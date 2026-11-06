# SPDX-License-Identifier: GPL-3.0-or-later
"""Local-only, bounded image/GIF backdrops. Never exports paths or source metadata."""
from bisect import bisect_right
from functools import lru_cache
import math
from pathlib import Path
from PIL import Image, ImageEnhance
from .media import load
from .localfiles import regular_identity
from .timing import MAX_FPS


@lru_cache(maxsize=2)
def cached_frames(path, identity):
    # At most two assets cached; each 120-frame RGB set uses about 20 MiB of pixels.
    return load(path,max_frames=120,validate_gif=True)


class Background:
    def __init__(self,path=None,dim=.65,pacing_fps=None):
        if not isinstance(dim,(float,int)) or not math.isfinite(dim) or not 0 <= dim <= .9:
            raise ValueError('Background dimming must be between 0 and 0.9')
        if pacing_fps is not None and (type(pacing_fps) not in (float,int) or not math.isfinite(pacing_fps) or not 0<pacing_fps<=MAX_FPS):
            raise ValueError('FPS must be greater than zero and at most 60')
        self.pacing_fps=pacing_fps
        self.enabled = bool(path)
        self.dim = dim
        self._stream=None
        self.frames = []
        self.ends = []
        self.duration = 0
        self._pacing=None
        if not path:cached_frames.cache_clear()
        if path:
            try:
                from .gifstream import acquire
                self._stream=acquire(path,clock=pacing_fps)
                if self._stream:
                    self.duration=self._stream.duration
                    self.ends=list(self._stream.ends)
                    return
                self.frames=cached_frames(str(path),regular_identity(path))
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
        fps=self.pacing_fps
        if not self.enabled:
            return Image.new('RGB',(240,240),'black')
        elapsed=max(0,elapsed)
        if fps is not None and len(self.ends)>1:
            if self._pacing is None or self._pacing[0]!=fps:
                adapted=[];previous=0;total=0
                for end in self.ends:
                    total+=max(end-previous,1/fps);adapted.append(total);previous=end
                self._pacing=(fps,adapted)
            adapted=self._pacing[1]
            loops=int(elapsed/adapted[-1])
            phase=elapsed%adapted[-1]
            # Output ticks can land a few floating-point units below a GIF
            # boundary. A microsecond tolerance prevents duplicate/skip pairs.
            phase+=min(.000001,(1/fps)*.0001)
            if phase>=adapted[-1]:loops+=1;index=0
            else:index=min(bisect_right(adapted,phase),len(adapted)-1)
            start=0 if index==0 else self.ends[index-1]
            # Select the middle of the original source frame to avoid rounding
            # errors at a GIF boundary. Source pixels and file stay untouched.
            elapsed=loops*self.duration+(start+self.ends[index])/2
        if self._stream:frame=self._stream.frame(elapsed)
        else:
            index=min(bisect_right(self.ends,elapsed%self.duration),len(self.frames)-1)
            frame=self.frames[index][0]
        # Callers treat source snapshots as immutable and transform fresh images.
        return frame if self.dim==0 else ImageEnhance.Brightness(frame).enhance(1-self.dim)

    def close(self):
        if self._stream:self._stream.close();self._stream=None
        self.frames=[]
