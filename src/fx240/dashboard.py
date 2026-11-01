# SPDX-License-Identifier: GPL-3.0-or-later
"""Dashboard layout for the circular visible area of the 240x240 LCD."""
import math
from PIL import Image, ImageDraw, ImageFont

CENTER = 119.5
TEXT_RADIUS = 104


def default_metrics(metrics):
    selected = []
    for group, unit in (("CPU", "C"), ("CPU", "MHz"), ("GPU", "C"), ("GPU", "MHz")):
        candidate = next((m for m in metrics if m.label.startswith(group+" ") and m.unit == unit), None)
        if candidate:
            selected.append(candidate)
    return selected


def centered_text(draw, text, top, size, fill):
    """Fit the whole text bounding box inside a conservative circular inset."""
    font = ImageFont.load_default(size=size)
    box = draw.textbbox((0, 0), text, font=font)
    height = box[3]-box[1]
    distance = max(abs(top-CENTER), abs(top+height-CENTER))
    width_limit = 2*math.sqrt(max(0, TEXT_RADIUS**2-distance**2)) - 4
    fitted = text
    while fitted and draw.textbbox((0, 0), fitted, font=font)[2] - draw.textbbox((0, 0), fitted, font=font)[0] > width_limit:
        text = text[:-1]
        fitted = text + "..." if text else ""
    box = draw.textbbox((0, 0), fitted, font=font)
    width = box[2]-box[0]
    draw.text((CENTER-width/2-box[0], top-box[1]), fitted, font=font, fill=fill)


def render(metrics, keys=None):
    image = Image.new("RGB", (240, 240), "black")
    draw = ImageDraw.Draw(image)
    draw.ellipse((3, 3, 236, 236), fill=(12, 18, 28))
    centered_text(draw, "FX240 LINUX", 30, 13, (80, 220, 205))
    if keys:
        lookup = {m.key: m for m in metrics}
        selected = [(k, lookup.get(k)) for k in keys]
    else:
        selected = [(m.key, m) for m in default_metrics(metrics)]
    if not selected:
        centered_text(draw, "No supported sensors", 111, 13, "white")
    for i, (key, metric) in enumerate(selected[:4]):
        top = 49 + i*40
        label = metric.label if metric else key
        centered_text(draw, label, top, 12, (160, 175, 190))
        text = "N/A" if metric is None or metric.value is None else f"{metric.value:.1f} {metric.unit}"
        centered_text(draw, text, top+15, 19, "white")
    return image
