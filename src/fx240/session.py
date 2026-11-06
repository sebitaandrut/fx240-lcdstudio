# SPDX-License-Identifier: GPL-3.0-or-later
"""Desktop session worker: one sensor snapshot feeds rendering and diagnostics."""
from dataclasses import dataclass
from datetime import datetime, timezone
import io
import math
from pathlib import Path
import queue
import threading
import time
from PIL import Image
from .focus import Focus, readings, accent_rgb
from .media import encode
from .protocol import build_reports
from .telemetry import collect
from .transport import Hidraw
from .idle import render_idle
from .timing import DEFAULT_FPS,MAX_FPS
from .presets import DEFAULT_GPU_ACCENT, DESIGNS, PRESET_ACCENTS, PresetRenderer


@dataclass(frozen=True)
class Settings:
    fps: float = DEFAULT_FPS
    quality: int = 65
    delay_ms: float = 2
    rotation: int = 180
    font_path: str | None = None
    font_weight: int = 350
    comet_speed: float = 1.0
    accent: str = "#73dfc1"
    comet_style: str = "accent"
    animation: str = "comet"
    dual_accent: str = PRESET_ACCENTS['dual']
    dual_gpu_accent: str = DEFAULT_GPU_ACCENT
    dual_gpu_effect_style: str = 'accent'
    trace_accent: str = PRESET_ACCENTS['trace']
    halo_accent: str = PRESET_ACCENTS['halo']
    preset_animation: str = 'signature'
    background_path: str | None = None
    background_dim: float = .65
    temperature_decimals: int = 1
    temperature_unit: str = "C"
    layout_mode: str = "focus"
    scene_json: str = ""
    profile_id: str = ""
    draft_scene_json: str = ""
    draft_profile_id: str = ""
    draft_name: str = ""
    device: str | None = None

    def validate(self):
        if not isinstance(self.layout_mode, str) or (self.layout_mode not in DESIGNS and self.layout_mode != 'editor'):
            raise ValueError("Unknown layout mode")
        from .scene import parse_scene
        parse_scene(self.scene_json)
        parse_scene(self.draft_scene_json)
        from .scene import plain
        if not plain(self.draft_name,32):raise ValueError('Invalid draft name')
        import re
        for identifier in (self.profile_id,self.draft_profile_id):
            if not isinstance(identifier,str) or (identifier and re.fullmatch(r'profile-[1-9][0-9]{0,6}',identifier) is None):raise ValueError('Invalid profile identifier')
        if type(self.fps) not in (int,float) or not math.isfinite(self.fps) or not 0 < self.fps <= MAX_FPS:
            raise ValueError('FPS must be greater than zero and at most 60')
        if not 1 <= self.quality <= 95 or not 0 <= self.delay_ms <= 100:
            raise ValueError('Invalid JPEG quality or report delay')
        if not math.isfinite(self.comet_speed) or not .25 <= self.comet_speed <= 3:
            raise ValueError('Comet speed must be between 0.25 and 3')
        if self.temperature_unit not in ('C','F'):
            raise ValueError('Temperature unit must be C or F')
        accent_rgb(self.accent)
        accent_rgb(self.dual_gpu_accent)
        for design in PRESET_ACCENTS:
            accent_rgb(getattr(self, design + '_accent'))
        if self.comet_style not in ('accent','rainbow') or self.dual_gpu_effect_style not in ('accent','rainbow'):
            raise ValueError('Unknown comet style')
        if self.animation not in ('comet','orbit','pulse','none') or self.preset_animation not in ('signature','none'):
            raise ValueError('Unknown animation')
        if not math.isfinite(self.background_dim) or not 0 <= self.background_dim <= .9:
            raise ValueError('Background dimming must be between 0 and 0.9')
        if self.background_path is not None and not isinstance(self.background_path,str):
            raise ValueError('Background must be a local file')
        if self.rotation not in (0,90,180,270):
            raise ValueError('Invalid rotation')
        if not 100 <= self.font_weight <= 900 or self.temperature_decimals not in (0,1):
            raise ValueError('Invalid font weight or decimal places')


class Snapshot:
    def __init__(self, provider=None):
        self.provider = provider if provider is not None else collect
        self.sequence = 0
        self.metrics = []
        self.timestamp = ''

    def sample(self):
        self.metrics = self.provider()
        self.sequence += 1
        self.timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        return self.metrics


def find_devices(root=Path('/sys/class/hidraw')):
    matches = []
    for node in sorted(Path(root).glob('hidraw*')):
        try:
            identity = (node/'device/uevent').read_text().upper()
        except OSError:
            continue
        if 'HID_ID=0003:00002000:00003000' in identity.splitlines():
            matches.append('/dev/'+node.name)
    return matches


class Session:
    def __init__(self, settings, send=False, provider=None, transport_factory=Hidraw, theme_factory=Focus, standby_guard=None, jpeg_subsampling=0):
        settings.validate()
        if type(jpeg_subsampling) is not int or jpeg_subsampling not in (0,2):
            raise ValueError('Invalid experimental JPEG subsampling')
        # Session-only experiment: never part of saved preferences or profiles.
        self.jpeg_subsampling=jpeg_subsampling
        if send and not settings.device:
            raise ValueError('Select a device before starting LCD output')
        self.settings = settings
        self.standby_guard = standby_guard
        self.send = send
        self.output_requested = send
        self.output_error = None
        self.suspended = threading.Event()
        self.output_released = threading.Event()
        self.output_released.set()
        self.snapshot = Snapshot(provider)
        self.transport_factory = transport_factory
        self.theme_factory = theme_factory
        self.events = queue.Queue(maxsize=1)
        self.stop_event = threading.Event()
        self.thread = None
        self.error = None
        self.frames = 0
        self.last_frame = None
        self.config_error = None
        self._request_sequence = 0
        self.config_revision = 0
        self._update_lock = threading.Lock()
        self._suspend_reasons = set()
        self._pending_config = None

    def publish(self, event):
        if event['kind'] == 'frame':
            self.last_frame = event
        try:
            self.events.put_nowait(event)
        except queue.Full:
            try:
                self.events.get_nowait()
            except queue.Empty:
                pass
            self.events.put_nowait(event)

    def start(self):
        if self.thread is not None:
            raise RuntimeError('A session cannot be started twice')
        self.thread = threading.Thread(target=self.run, name='fx240-display', daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def set_output(self, enabled):
        if enabled and not self.settings.device:
            raise ValueError('Select a device before starting LCD output')
        self.output_requested = enabled

    def configure(self, settings, send=None):
        """Coalesce edits; commit a complete configuration at a frame boundary."""
        settings.validate()
        if send and not settings.device:
            raise ValueError('Select a device before starting LCD output')
        with self._update_lock:
            self._request_sequence += 1
            self._pending_config = (settings,send,self._request_sequence)
            return self._request_sequence

    def suspend(self, sleeping, reason='sleep'):
        # Independent notifications must not resume each other's paused output.
        with self._update_lock:
            if sleeping:self._suspend_reasons.add(reason)
            else:self._suspend_reasons.discard(reason)
            if self._suspend_reasons:
                if not self.suspended.is_set():self.output_released.clear()
                self.suspended.set()
            else:self.suspended.clear()

    def make_theme(self,config):
        factory=self.theme_factory
        options={}
        accent = config.accent
        animation = config.animation
        if config.layout_mode=='editor':
            from .scene import SceneRenderer
            factory=SceneRenderer;options['scene_json']=config.scene_json
        elif config.layout_mode != 'focus':
            factory = PresetRenderer
            options['design'] = config.layout_mode
            options['gpu_accent'] = config.dual_gpu_accent
            options['gpu_effect_style'] = config.dual_gpu_effect_style
            accent = getattr(config, config.layout_mode + '_accent')
            animation = config.preset_animation
        return factory(config.fps,font_path=config.font_path,font_weight=config.font_weight,
                       temperature_decimals=config.temperature_decimals,temperature_unit=config.temperature_unit,
                       comet_speed=config.comet_speed,accent=accent,comet_style=config.comet_style,
                       animation=animation,background_path=config.background_path,background_dim=config.background_dim,
                       provider=self.snapshot.sample,**options)

    def run(self):
        config = self.settings
        manager = device = None
        theme=None

        def dispose(renderer):
            close=getattr(renderer,"close",None)
            if close:close()

        def release():
            nonlocal manager, device
            if device is not None:
                try:
                    jpeg = encode(render_idle(),config.quality,config.rotation,subsampling=self.jpeg_subsampling)
                    device.send(build_reports(jpeg),config.delay_ms)
                    if self.standby_guard:self.standby_guard.disarm()
                except Exception as error:
                    self.output_error = 'Standby frame failed: '+str(error)
                    if self.standby_guard:self.standby_guard.disarm()
                finally:
                    manager.__exit__(None,None,None)
                    manager = device = None
            self.send = False
            self.output_released.set()

        try:
            theme = self.make_theme(config)
            start = time.monotonic()
            target = start
            target_offset = 0.0
            request_id = 0
            while not self.stop_event.is_set():
                if self.suspended.is_set():
                    release()
                    self.stop_event.wait(.05)
                    target = time.monotonic()
                    target_offset = target-start
                    continue
                began = time.monotonic()
                prepared_frame = None
                with self._update_lock:
                    pending = self._pending_config
                    self._pending_config = None
                if pending is not None:
                    candidate,send,request_id = pending
                    replacement=None
                    try:
                        if device is not None and candidate.device != config.device:
                            raise ValueError('Pause LCD output before changing its device')
                        replacement = self.make_theme(candidate)
                        # Preserve the decorative arc position and animation clock.
                        elapsed = max(target_offset,time.monotonic()-start)
                        replacement.inherit_motion(theme,elapsed)
                        replacement.sample(elapsed)
                        prepared_frame,_ = replacement(elapsed) # Validate once and send this same frame.
                        previous=theme;theme=replacement;replacement=None
                        dispose(previous)
                        config = self.settings = candidate
                        if send is not None:
                            self.output_requested = send
                        if device is not None and self.standby_guard:self.standby_guard.arm(config)
                        self.config_error = None
                        self.config_revision += 1
                    except Exception as error:
                        prepared_frame=None
                        if replacement is not None:dispose(replacement)
                        self.config_error = str(error)
                if prepared_frame is None:
                    frame,_ = theme(max(target_offset,time.monotonic()-start))
                else:frame=prepared_frame
                jpeg = encode(frame,config.quality,config.rotation,subsampling=self.jpeg_subsampling)
                reports = build_reports(jpeg)
                # Prepare before the delivery deadline: sensor/render/encode
                # work must not shift every USB burst after its scheduled time.
                waiting_at=time.monotonic()
                if self.stop_event.wait(max(0,target-waiting_at)):
                    break
                waited=time.monotonic()-waiting_at
                if self.suspended.is_set():
                    continue
                if not self.output_requested:
                    release()
                elif device is None:
                    try:
                        manager = self.transport_factory(config.device)
                        device = manager.__enter__()
                        self.send = True
                        self.output_error = None
                        self.output_released.clear()
                        if self.standby_guard:self.standby_guard.arm(config)
                    except Exception as error:
                        manager = device = None
                        self.output_requested = self.send = False
                        self.output_error = str(error)
                        self.output_released.set()
                tx = 0
                sent = False
                if device is not None:
                    try:
                        tx,_ = device.send(reports,config.delay_ms)
                        sent = True
                    except Exception as error:
                        # Do not attempt more reports after a partial/failed write.
                        if self.standby_guard:self.standby_guard.disarm()
                        manager.__exit__(None,None,None)
                        manager = device = None
                        self.output_requested = self.send = False
                        self.output_error = str(error)
                        self.output_released.set()
                finished = time.monotonic()
                with Image.open(io.BytesIO(jpeg)) as decoded:
                    preview = decoded.convert('RGB').rotate(-config.rotation)
                self.frames += 1
                self.publish({'kind':'frame','image':preview,'metrics':self.snapshot.metrics,
                              'sequence':self.snapshot.sequence,'timestamp':self.snapshot.timestamp,
                              'display_values':readings(self.snapshot.metrics),
                              'temperature_decimals':getattr(theme,'temperature_decimals',config.temperature_decimals),
                              'temperature_unit':getattr(theme,'temperature_unit',config.temperature_unit),
                              'frames':self.frames,'transmission_ms':tx,'reports':len(reports),
                              'pipeline_ms':max(0,(finished-began-waited)*1000),
                              'sent':sent,'output_error':self.output_error,'config_error':self.config_error,
                              'config_revision':self.config_revision,'configuration':config,'config_request_id':request_id,'elapsed':finished-start})
                # Accumulate the small relative clock, not large absolute
                # monotonic timestamps, to keep GIF boundary sampling stable.
                target_offset = max(target_offset+1/config.fps,time.monotonic()-start)
                target = start+target_offset
        except Exception as error:
            self.error = str(error)
        finally:
            try:release()
            except Exception as error:self.error=self.error or str(error)
            try:dispose(theme)
            except Exception as error:self.error=self.error or str(error)
            self.publish({'kind':'stopped','error':self.error or self.output_error,
                          'frames':self.frames,'last_frame':self.last_frame})
