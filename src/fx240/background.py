# SPDX-License-Identifier: GPL-3.0-or-later
"""Local-only, bounded image/GIF backdrops. Never exports paths or source metadata."""
from bisect import bisect_right
from functools import lru_cache
import math
from pathlib import Path
from PIL import Image, ImageEnhance
from .media import load


@lru_cache(maxsize=2)
def cached_frames(path, modified, size):
    # At most two assets cached; each 120-frame RGB set uses about 20 MiB of pixels.
    return load(path,max_frames=120)


class Background:
    def __init__(self,path=None,dim=.65):
        if not isinstance(dim,(float,int)) or not math.isfinite(dim) or not 0 <= dim <= .9:
            raise ValueError('Background dimming must be between 0 and 0.9')
        self.enabled = bool(path)
        self.dim = dim
        self._stream=None
        self.frames = []
        self.ends = []
        self.duration = 0
        if not path:cached_frames.cache_clear()
        if path:
            try:
                from .gifstream import acquire
                self._stream=acquire(path)
                if self._stream:
                    self.duration=self._stream.duration
                    return
                stat=Path(path).stat()
                self.frames=cached_frames(str(path),stat.st_mtime_ns,stat.st_size)
                for _,delay in self.frames:
                    self.duration += max(.04,min(float(delay),60))
                    self.ends.append(self.duration)
            except (OSError,ValueError,SyntaxError) as error:
                self.close()
                message='Background could not be loaded; choose a valid local image or GIF within the decoding limits'
                raise ValueError(message) from error
            if not self.frames or not math.isfinite(self.duration):
                raise ValueError('Background has no valid frames')

    def frame(self,elapsed):
        if not self.enabled:
            return Image.new('RGB',(240,240),'black')
        if self._stream:return ImageEnhance.Brightness(self._stream.frame(elapsed)).enhance(1-self.dim)
        index=min(bisect_right(self.ends,max(0,elapsed)%self.duration),len(self.frames)-1)
        return ImageEnhance.Brightness(self.frames[index][0]).enhance(1-self.dim)

    def close(self):
        if self._stream:self._stream.close();self._stream=None
        self.frames=[]
