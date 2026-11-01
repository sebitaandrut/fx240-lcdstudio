# SPDX-License-Identifier: GPL-3.0-or-later
"""Circular telemetry overlay with independent one-second sensor sampling."""
from PIL import Image, ImageDraw
from .dashboard import centered_text, default_metrics
from .media import canvas
from .telemetry import collect


def render(background, metrics, keys=None):
    image = canvas(background).convert('RGBA')
    shade = Image.new('RGBA', image.size)
    draw = ImageDraw.Draw(shade)
    draw.rectangle((0, 30, 239, 86), fill=(0, 0, 0, 205))
    draw.rectangle((0, 156, 239, 210), fill=(0, 0, 0, 205))
    image = Image.alpha_composite(image, shade)
    draw = ImageDraw.Draw(image)
    if keys:
        lookup = {metric.key: metric for metric in metrics}
        selected = [(key, lookup.get(key)) for key in keys[:4]]
    else:
        selected = [(metric.key, metric) for metric in default_metrics(metrics)]
    if not selected:
        centered_text(draw, 'No supported sensors', 48, 12, 'white')
    for (key, metric), top in zip(selected, (40, 65, 164, 189)):
        label = metric.label.split()[0] if metric else 'Sensor'
        value = 'N/A' if metric is None or metric.value is None else f'{metric.value:.1f} {metric.unit}'
        centered_text(draw, f'{label} {value}', top, 14, 'white')
    mask = Image.new('L', image.size)
    ImageDraw.Draw(mask).ellipse((3, 3, 236, 236), fill=255)
    result = Image.new('RGB', image.size, 'black')
    result.paste(image.convert('RGB'), (0, 0), mask)
    return result


class TelemetryOverlay:
    def __init__(self, frame_at, keys=None, provider=None):
        self.frame_at = frame_at
        self.keys = keys
        self.provider = provider if provider is not None else collect
        self.sampled_at = None
        self.metrics = []

    def __call__(self, elapsed):
        if self.sampled_at is None or elapsed < self.sampled_at or elapsed-self.sampled_at >= 1:
            # Replace the whole snapshot so failed or removed sensors cannot stay stale.
            self.metrics = self.provider()
            self.sampled_at = elapsed
        image, interval = self.frame_at(elapsed)
        return render(image, self.metrics, self.keys), interval
