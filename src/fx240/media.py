# SPDX-License-Identifier: GPL-3.0-or-later
"""Image/GIF composition and JPEG encoding, independent of transport."""
import io
import math
import struct
from PIL import Image, ImageOps
from .localfiles import read_regular


MAX_SOURCE_PIXELS = 16_000_000
MAX_FILE_BYTES = 64 * 1024 * 1024


def check_size(image):
    if image.width * image.height > MAX_SOURCE_PIXELS:
        raise ValueError('Source image exceeds the 16 megapixel limit')


def canvas(image):
    check_size(image)
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
    try:
        payload=read_regular(path,MAX_FILE_BYTES)
    except ValueError as error:
        raise ValueError('Media input must be a regular file of at most 64 MiB') from error
    frames = []
    try:
        with Image.open(io.BytesIO(payload)) as source:
            check_size(source)
            if getattr(source, "n_frames", 1) > max_frames:
                raise ValueError("Too many frames; limit is 1000")
            for i in range(getattr(source, "n_frames", 1)):
                source.seek(i)  # Pillow applies GIF disposal/composition.
                check_size(source)
                duration = source.info.get("duration", 100)
                if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
                    duration = 100
                frames.append((canvas(source.copy()), duration / 1000))
    except (IndexError, EOFError, struct.error, Image.DecompressionBombError) as error:
        raise ValueError('Invalid, truncated, or oversized image/GIF data') from error
    return frames
