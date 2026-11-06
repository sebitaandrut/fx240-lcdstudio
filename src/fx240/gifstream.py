# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded GIF playback with bounded queues and renderer-owned leases."""
from bisect import bisect_right
from collections import OrderedDict
import io
import math
from pathlib import Path
import queue
import struct
import threading
from PIL import Image
from .localfiles import read_regular,regular_identity
from .media import canvas,MAX_FILE_BYTES

MAX_FRAMES=2000
MAX_PIXELS=4_000_000
MAX_WORK=300_000_000
BUFFER_FRAMES=12
_pool={}
_small_assets=OrderedDict()
MAX_INSPECTION_CACHE=8
_pool_lock=threading.RLock()


def inspect_gif(payload):
    ends=[];duration=0;work=0
    with Image.open(io.BytesIO(payload)) as source:
        if source.format!='GIF':return None
        for index in range(MAX_FRAMES+1):
            try:source.seek(index)
            except EOFError:break
            pixels=source.width*source.height;work+=pixels
            if index>=MAX_FRAMES or pixels>MAX_PIXELS or work>MAX_WORK:
                raise ValueError('GIF exceeds the frame or decoding budget')
            delay=source.info.get('duration',100)
            if not isinstance(delay,(float,int)) or not math.isfinite(delay) or delay<=0:delay=100
            duration+=max(.04,min(delay/1000,60));ends.append(duration)
    if not ends:raise ValueError('GIF contains no frames')
    return ends


class Decoder:
    def __init__(self,payload,ends):
        self.ends=ends;self.duration=ends[-1];self.count=len(ends)
        self.queue=queue.Queue(maxsize=BUFFER_FRAMES)
        self.stop=threading.Event();self.ready=threading.Event();self.lock=threading.Lock()
        self.generation=0;self.restart_at=0;self.anchor=0
        self.last=None;self.index=-1;self.error=False;self.underruns=0;self.peak_queue=0
        self.refs=0;self.cleanup_timeout=False
        self.thread=threading.Thread(target=self._run,args=(payload,),daemon=True,name='fx240-gif-stream')
        self.thread.start()
        if not self.ready.wait(3) or self.error:
            self.close();raise ValueError('GIF decoder could not start')

    def _run(self,payload):
        generation=-1;index=0
        try:
            with Image.open(io.BytesIO(payload)) as source:
                while not self.stop.is_set():
                    with self.lock:
                        current=self.generation
                        if generation!=current:generation=current;index=self.restart_at
                    source.seek(index%self.count);frame=canvas(source.copy())
                    while not self.stop.is_set():
                        with self.lock:
                            if generation!=self.generation:break
                        try:self.queue.put((generation,index,frame),timeout=.025);break
                        except queue.Full:continue
                    self.peak_queue=max(self.peak_queue,self.queue.qsize())
                    self.ready.set();index+=1
        except (OSError,ValueError,EOFError,IndexError,struct.error,Image.DecompressionBombError):
            self.error=True;self.ready.set()

    def _restart(self,index):
        with self.lock:self.generation+=1;self.restart_at=index;self.anchor=index
        while True:
            try:self.queue.get_nowait()
            except queue.Empty:break
        self.index=-1

    def frame(self,elapsed):
        elapsed=max(0,elapsed)
        wanted=int(elapsed/self.duration)*self.count+min(bisect_right(self.ends,elapsed%self.duration),self.count-1)
        # Drain ready frames first. A stale worker generation can never replace
        # a current frame after a seek, rewind, or suspend/resume gap.
        while self.index<wanted:
            try:generation,index,frame=self.queue.get_nowait()
            except queue.Empty:break
            if generation==self.generation:self.index=index;self.last=frame
        if wanted<self.index or wanted<self.anchor or wanted>max(self.index,self.anchor)+BUFFER_FRAMES*2:
            self._restart(wanted)
        if self.last is None:
            try:
                generation,index,frame=self.queue.get(timeout=3)
                if generation==self.generation:self.index=index;self.last=frame
            except queue.Empty:pass
        if self.last is None or self.error:raise ValueError('GIF decoder failed')
        if self.index!=wanted:self.underruns+=1
        return self.last

    def close(self):
        self.stop.set();self.thread.join(timeout=2)
        self.cleanup_timeout=self.thread.is_alive()
        while True:
            try:self.queue.get_nowait()
            except queue.Empty:break
        self.last=None


class Lease:
    def __init__(self,key,decoder):self.key=key;self.decoder=decoder;self.closed=False
    @property
    def duration(self):return self.decoder.duration
    @property
    def ends(self):return tuple(self.decoder.ends)
    def frame(self,elapsed):return self.decoder.frame(elapsed)
    def close(self):
        if self.closed:return
        self.closed=True;closing=None
        with _pool_lock:
            self.decoder.refs-=1
            if self.decoder.refs==0:
                _pool.pop(self.key,None);self.decoder.stop.set();closing=self.decoder
        if closing:closing.close()


def acquire(path,clock=None):
    path=Path(path);identity=regular_identity(path)
    # Geometry edits must not re-read/index the entire GIF. Long-lived streams
    # share leases; a bounded metadata-only cache remembers eager assets.
    asset=(str(path),identity,MAX_FRAMES,MAX_PIXELS,MAX_WORK)
    key=(threading.current_thread(),*asset,clock)
    with _pool_lock:
        decoder=_pool.get(key)
        if decoder is not None:
            decoder.refs+=1
            return Lease(key,decoder)
        if asset in _small_assets:
            _small_assets.move_to_end(asset)
            return None
    # File decoding and worker startup never hold the registry lock, allowing
    # independent preview/output sessions to continue while an asset loads.
    payload=read_regular(path,MAX_FILE_BYTES);ends=inspect_gif(payload)
    if ends is None or len(ends)<=120:
        if regular_identity(path)==identity:
            with _pool_lock:
                _small_assets[asset]=True;_small_assets.move_to_end(asset)
                while len(_small_assets)>MAX_INSPECTION_CACHE:_small_assets.popitem(last=False)
        return None
    decoder=Decoder(payload,ends)
    with _pool_lock:
        decoder.refs=1;_pool[key]=decoder
    return Lease(key,decoder)


def statistics(owner=None):
    owner=owner or threading.current_thread()
    if not _pool_lock.acquire(blocking=False):return {'preparing':True}
    try:
        values=[value for key,value in _pool.items() if key[0] is owner]
        return {'streams':len(values),'queued_frames':sum(value.queue.qsize() for value in values),
                'underruns':sum(value.underruns for value in values)}
    finally:_pool_lock.release()
