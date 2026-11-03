# SPDX-License-Identifier: GPL-3.0-or-later
import argparse
from bisect import bisect_right
import json
import math
from pathlib import Path
import sys
import time
from .dashboard import render
from .media import load
from .player import play, summary
from .telemetry import collect
from .transport import Hidraw
from .overlay import TelemetryOverlay
from .focus import Focus


def main(argv=None):
    parser = argparse.ArgumentParser(description="FX240 LCD STUDIO; experimental native Linux client. CLI simulation by default, GUI auto-starts LCD output")
    parser.add_argument("mode", choices=("image", "gif", "dashboard", "sensors", "focus", "gui", "self-test"))
    parser.add_argument("--start-minimized", action="store_true", help="GUI: start in the tray, or minimize normally when no tray is available")
    # Accept old trial/autostart commands; buffering is now automatic.
    parser.add_argument("--experimental-gif-buffering",action="store_true",help=argparse.SUPPRESS)
    parser.add_argument("--config-home", type=Path, help="GUI-only configuration root for Studio; leaves system XDG folders and theme settings unchanged")
    parser.add_argument("file", nargs="?", type=Path)
    parser.add_argument("--temperature-unit", choices=("C","F"), default="C", help="Displayed temperature unit; raw sensors remain Celsius")
    parser.add_argument("--temperature-decimals", type=int, choices=(0,1), default=None, help="Focus temperature decimal places")
    parser.add_argument("--accent", default="#73dfc1", help="LCD accent as #RRGGBB")
    parser.add_argument("--comet-style", choices=("accent","rainbow"), default="accent")
    parser.add_argument("--comet-speed", type=float, default=1.0, help="Comet speed multiplier, 0.25..3 (default 1)")
    parser.add_argument("--font-weight", type=int, default=350, help="Focus variable font weight, 100..900; static fonts keep their native weight")
    parser.add_argument("--font", type=Path, help="Focus TrueType font; default: bundled Outfit, then installed Noto Sans Regular or Pillow fallback")
    parser.add_argument("--arc-min", type=float, default=0, help="Focus arc scale minimum in C (visual scale, not an alarm)")
    parser.add_argument("--arc-max", type=float, default=100, help="Focus arc scale maximum in C (visual scale, not an alarm)")
    parser.add_argument("--overlay", action="store_true", help="Overlay CPU/GPU telemetry on an image or GIF")
    parser.add_argument("--device", help="Explicit /dev/hidrawN path for transmission")
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--duration", type=float, default=10)
    parser.add_argument("--fps", type=float, default=None, help="Maximum 24 FPS; preserve GIF timing unless overridden")
    parser.add_argument("--delay-ms", type=float, default=10)
    parser.add_argument("--quality", type=int, default=85)
    parser.add_argument("--rotation", type=int, choices=(0,90,180,270), default=180)
    parser.add_argument("--metric", action="append", help="Key from sensors; repeat up to four times")
    parser.add_argument("--preview", type=Path, help="Save the first frame as PNG before rotation")
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(raw_argv)
    args.explicit_options = {token.split('=',1)[0] for token in raw_argv if token.startswith('--')}
    if not math.isfinite(args.comet_speed) or not .25 <= args.comet_speed <= 3:
        parser.error("Comet speed: 0.25..3")
    if not 0 < args.duration <= 3600 or not math.isfinite(args.duration):
        parser.error("Duration: 0 < seconds <= 3600")
    if args.fps is not None and not 0 < args.fps <= 24:
        parser.error("FPS: 0 < FPS <= 24")
    if not 0 <= args.delay_ms <= 100 or not 1 <= args.quality <= 95:
        parser.error("Delay: 0..100 ms; quality: 1..95")
    if len(args.metric or []) > 4:
        parser.error("At most four metrics are supported")
    if args.overlay and args.mode not in ("image", "gif"):
        parser.error("--overlay requires image or gif mode")
    if args.start_minimized and args.mode != 'gui':
        parser.error('--start-minimized requires gui mode')
    if args.experimental_gif_buffering and args.mode not in ('gui','self-test'):parser.error('--experimental-gif-buffering requires gui or self-test mode')
    if args.config_home is not None:
        if args.mode!='gui':parser.error('--config-home requires gui mode')
        if not args.config_home.is_absolute() or len(str(args.config_home))>4096 or any(ord(c)<32 for c in str(args.config_home)):
            parser.error('--config-home must be an absolute path without control characters')
    if args.mode == 'self-test':
        if args.send:parser.error('self-test never transmits')
        from .selftest import run
        return run()
    if args.mode == "gui":
        from .guard import StandbyGuard
        from .lifecycle import LifecycleTrace
        trace=LifecycleTrace();trace.emit('session-start')
        guard=None
        try:
            try:guard=StandbyGuard(trace=trace).start()
            except (OSError,RuntimeError):trace.emit('guard-start-failed')
            from .gui import launch
            trace.emit('gui-start')
            return launch(args,standby_guard=guard,trace=trace)
        except (ImportError, OSError, RuntimeError) as error:
            parser.exit(1, f"GUI could not start: {error}\nInstall the optional desktop dependencies with: python -m pip install '.[desktop]'\n")
        finally:
            if guard:guard.close()
    if args.mode == "sensors":
        if args.send:
            parser.error("sensors does not transmit")
        print(json.dumps([m.record() for m in collect()], ensure_ascii=False, indent=2))
        return
    if args.send and not args.device:
        parser.error("--send requires --device /dev/hidrawN")
    try:
        if args.mode in ("image", "gif"):
            if args.file is None:
                parser.error("An input file is required")
            if args.mode == "gif":
                from PIL import Image
                with Image.open(args.file) as check:
                    if check.format != "GIF":
                        parser.error("gif mode requires a GIF file")
            frames = load(args.file)
            if args.mode == "image":
                frames = frames[:1]
            intervals = [1/args.fps if args.fps else max(d,1/24) for _,d in frames]
            ends = []
            for d in intervals:
                ends.append((ends[-1] if ends else 0)+d)
            def frame_at(elapsed):
                i = min(bisect_right(ends, elapsed % ends[-1]), len(frames)-1)
                return frames[i][0], intervals[i]
        elif args.mode == "focus":
            frame_at = Focus(args.fps or 5, args.metric, args.font, arc_range=(args.arc_min,args.arc_max), font_weight=args.font_weight,comet_speed=args.comet_speed,accent=args.accent,comet_style=args.comet_style, temperature_decimals=args.temperature_decimals or 0, temperature_unit=args.temperature_unit)
        else:
            cache = {"at": -1, "image": None}
            def frame_at(elapsed):
                if cache["image"] is None or elapsed-cache["at"] >= 1:
                    cache.update(at=elapsed, image=render(collect(), args.metric))
                return cache["image"], 1/(args.fps or 1)
        if args.overlay:
            frame_at = TelemetryOverlay(frame_at, args.metric)
        if args.preview:
            frame_at(0)[0].save(args.preview, format="PNG")
        playback_start = time.monotonic()
        if args.send:
            with Hidraw(args.device) as device:
                samples = play(frame_at, args.duration, device, args.delay_ms, args.quality, args.rotation)
        else:
            samples = play(frame_at, args.duration, None, args.delay_ms, args.quality, args.rotation)
        elapsed = time.monotonic()-playback_start
        print(json.dumps({"elapsed_seconds": elapsed, "host_fps": len(samples)/elapsed if elapsed else 0,
                          "mode": "send" if args.send else "simulation",
                          "note": "Host metrics do not measure the physical LCD refresh rate",
                          "profile": {"fps": args.fps or (5 if args.mode == "focus" else None),
                                      "quality": args.quality, "delay_ms": args.delay_ms,
                                      "rotation": args.rotation},
                          **summary(samples)}, ensure_ascii=False, indent=2))
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")
    except KeyboardInterrupt:
        parser.exit(130, "Interrupted\n")
