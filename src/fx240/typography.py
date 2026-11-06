# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded font loading, per-thread faces, and truthful weight capabilities."""
from functools import lru_cache
import io
from pathlib import Path
import threading
from PIL import ImageFont
from .localfiles import read_regular,regular_identity

SCALE=2
MAX_FONT_BYTES = 16 * 1024 * 1024


def load_font(path, size):
    # A saved/custom font is local input too: never hand a FIFO to FreeType.
    return ImageFont.truetype(io.BytesIO(read_regular(path,MAX_FONT_BYTES)),size)


@lru_cache(maxsize=32)
def _validate_font(path,identity):
    # Validation is immutable per file version; native faces remain per-thread.
    load_font(path,12)


def resolve_font(path=None):
    if path is not None:
        # Validate explicit choices instead of silently substituting another font.
        _validate_font(str(path),regular_identity(path))
        return str(path)
    for candidate in (str(Path(__file__).parent/'assets/fonts/Outfit.ttf'),
                      '/usr/share/fonts/noto/NotoSans-Regular.ttf',
                      '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf'):
        if Path(candidate).is_file():
            return candidate
    return None


@lru_cache(maxsize=32)
def _font(path, size, weight, owner, identity):
    face = load_font(path, size*SCALE) if path else ImageFont.load_default(size=size*SCALE)
    try:
        axes = face.get_variation_axes()
    except (OSError, AttributeError):
        return face
    values = []
    for axis in axes:
        name = axis['name']
        value = weight if name == b'Weight' else size if name == b'Optical size' else axis['default']
        values.append(max(axis['minimum'], min(axis['maximum'], value)))
    face.set_variation_by_axes(values)
    return face


def font(path,size,weight=400):
    # FreeType faces are not shared between the LCD and draft-preview threads.
    return _font(path,size,weight,threading.current_thread(),regular_identity(path) if path else None)


font.cache_clear = _font.cache_clear



@lru_cache(maxsize=32)
def _capabilities(path,modified,size,identity=None):
    face=load_font(path,12)
    family,style=face.getname()
    try:axes=face.get_variation_axes()
    except (OSError,AttributeError):axes=[]
    axis=next((axis for axis in axes if axis['name']==b'Weight'),None)
    return {'variable':axis is not None,'family':family,'style':style,
            'minimum':max(100,int(axis['minimum'])) if axis else 100,
            'maximum':min(900,int(axis['maximum'])) if axis else 900}


def capabilities(path=None):
    source=resolve_font(path)
    if source is None:return {'variable':False,'family':'Default','style':'Regular','minimum':100,'maximum':900}
    metadata=Path(source).stat()
    return dict(_capabilities(source,metadata.st_mtime_ns,metadata.st_size,regular_identity(source)))
