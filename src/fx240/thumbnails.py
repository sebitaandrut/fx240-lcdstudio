# SPDX-License-Identifier: GPL-3.0-or-later
"""On-demand gallery snapshots using sample readings and the existing renderer."""
import queue
import threading

from PIL import Image
from PySide6.QtCore import QObject, Property, Signal

from .preview import ThumbnailProvider, circular_image
from .presets import EDITOR_EFFECTS
from .scene import effect_layer, scene_json
from .session import Session, Settings
from .telemetry import Metric


def sample_metrics():
    return [
        Metric('ct', 'CPU sample', 46.5, 'C', 'sample'),
        Metric('cf', 'CPU sample', 4280, 'MHz', 'sample'),
        Metric('gt', 'GPU sample', 39.0, 'C', 'sample'),
        Metric('gf', 'GPU sample', 1850, 'MHz', 'sample'),
    ]


def render_thumbnail(settings):
    session = Session(settings, provider=sample_metrics)
    theme = session.make_theme(settings)
    try:
        if settings.layout_mode == 'trace' or getattr(theme, 'has_trace', False):
            # A representative history gives the static Trace card a visible plot.
            for index in range(38):
                value = 44 + (index % 9) / 2 + (index % 3) / 3
                theme.history.append((index - 38, value))
        frame, _ = theme(.5)
        return frame.resize((192, 192), Image.Resampling.LANCZOS)
    finally:
        theme.close()


class EffectThumbnails(ThumbnailProvider):
    def requestImage(self, identifier, size, requested_size):
        if identifier in EDITOR_EFFECTS and identifier not in self.images:
            scene = scene_json({'version': 1, 'layers': [effect_layer('sample', identifier)]})
            config = Settings(layout_mode='editor', scene_json=scene)
            self.images[identifier] = circular_image(render_thumbnail(config))
        return super().requestImage(identifier, size, requested_size)


class GalleryThumbnails(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.provider = ThumbnailProvider()
        self.targets = ()
        self.cache = {}
        self.results = queue.SimpleQueue()
        self.worker = None
        self.cancel = threading.Event()
        self.visible = False
        self.serial = 0

    @Property('QStringList', notify=changed)
    def urls(self):
        return [f'image://thumbnails/{self.cache[config]}' if self.cache.get(config) else ''
                for config in self.targets]

    def show(self, configs):
        self.visible = True
        targets = tuple(configs)
        if targets != self.targets:
            self.cancel.set()
            self.targets = targets
            self.cache = {config: key for config, key in self.cache.items() if config in targets}
            images = self.provider.images
            self.provider.images = {key: images[key] for key in self.cache.values() if key}
            self.changed.emit()
        self.ensure_worker()

    def hide(self):
        self.visible = False
        self.cancel.set()
        # Allow a missing or repaired asset to be retried on the next visit.
        self.cache = {config: key for config, key in self.cache.items() if key}

    def ensure_worker(self):
        if not self.visible or self.worker is not None:
            return
        pending = tuple(config for config in dict.fromkeys(self.targets) if config not in self.cache)
        if pending:
            self.cancel = threading.Event()
            self.worker = threading.Thread(target=self.render, args=(pending, self.cancel),
                                           name='fx240-thumbnails', daemon=True)
            self.worker.start()

    def render(self, pending, cancel):
        for config in pending:
            if cancel.is_set():
                break
            try:
                image = render_thumbnail(config)
            except Exception:
                # A preview failure should leave a placeholder and let other cards load.
                image = None
            if not cancel.is_set():
                self.results.put((config, image))

    def poll(self):
        if self.worker and not self.worker.is_alive():
            self.worker = None
        updated = False
        while True:
            try:
                config, image = self.results.get_nowait()
            except queue.Empty:
                break
            if config not in self.targets or config in self.cache:
                continue
            key = ''
            if image is not None:
                self.serial += 1
                key = str(self.serial)
                self.provider.images[key] = circular_image(image)
            self.cache[config] = key
            updated = True
        if updated:
            self.changed.emit()
        self.ensure_worker()

    def close(self):
        self.hide()
        if self.worker:
            self.worker.join(timeout=2)
