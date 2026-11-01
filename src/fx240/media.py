# SPDX-License-Identifier: GPL-3.0-or-later
"""Image/GIF composition and JPEG encoding, independent of transport."""
import io
from PIL import Image, ImageOps


def canvas(image):
    image = image.convert("RGBA")
    image = ImageOps.contain(image, (240, 240), Image.Resampling.LANCZOS)
    result = Image.new("RGBA", (240, 240), (0, 0, 0, 255))
    result.alpha_composite(image, ((240-image.width)//2, (240-image.height)//2))
    return result.convert("RGB")


def encode(image, quality=85, rotation=180):
    if not 1 <= quality <= 95 or rotation not in (0, 90, 180, 270):
        raise ValueError("Invalid quality or rotation")
    output = io.BytesIO()
    canvas(image).rotate(rotation).save(output, "JPEG", quality=quality, subsampling=0)
    return output.getvalue()


def load(path, max_frames=1000):
    frames = []
    with Image.open(path) as source:
        if getattr(source, "n_frames", 1) > max_frames:
            raise ValueError("Too many frames; limit is 1000")
        for i in range(getattr(source, "n_frames", 1)):
            source.seek(i)  # Pillow applies GIF disposal/composition.
            duration = source.info.get("duration", 100)
            if not isinstance(duration, (int, float)) or duration <= 0:
                duration = 100
            frames.append((canvas(source.copy()), duration / 1000))
    return frames
