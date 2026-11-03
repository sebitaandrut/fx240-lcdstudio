# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline GIF buffering experiment: no HID, telemetry, GUI, or preference access."""
import argparse
from bisect import bisect_right
import io
import json
import math
from pathlib import Path
import queue
import resource
import struct
import threading
import time
from PIL import Image,ImageDraw,ImageFont
from fx240.localfiles import read_regular
from fx240.media import canvas,encode,MAX_FILE_BYTES

MAX_FRAMES=2000
MAX_PIXELS=4_000_000
MAX_DECODE_WORK=300_000_000


def inspect(payload):
    durations=[]
    with Image.open(io.BytesIO(payload)) as source:
        if source.format!='GIF':raise ValueError('Experimental input must be GIF')
        size=source.size;work=0
        for index in range(MAX_FRAMES+1):
            try:source.seek(index)
            except EOFError:break
            pixels=source.width*source.height;work+=pixels
            if index>=MAX_FRAMES or pixels>MAX_PIXELS or work>MAX_DECODE_WORK:
                raise ValueError('Experimental GIF input exceeds the decoding budget')
            value=source.info.get('duration',100)
            if not isinstance(value,(float,int)) or not math.isfinite(value) or value<=0:value=100
            durations.append(max(.04,min(value/1000,60)))
    return size,durations


class Eager:
    def __init__(self,payload,count):
        if not 1<=count<=MAX_FRAMES or count*240*240*4>256*1024*1024:
            raise ValueError('Experimental eager pixel storage exceeds 256 MiB')
        self.frames=[]
        with Image.open(io.BytesIO(payload)) as source:
            for index in range(count):
                source.seek(index);self.frames.append(canvas(source.copy()))
        self.underruns=0;self.peak_queue=len(self.frames)

    def frame(self,index):return self.frames[index%len(self.frames)],index
    def close(self):self.frames.clear()


class Buffered:
    """Sequential GIF disposal stays on one decoder thread; the queue is bounded."""
    def __init__(self,payload,count,capacity=12):
        if not 1<=count<=MAX_FRAMES:raise ValueError('Experimental frame count is invalid')
        if not 1<=capacity<=24:raise ValueError('Experimental buffer capacity must be 1..24')
        self.queue=queue.Queue(maxsize=capacity);self.stop=threading.Event()
        self.ready=threading.Event();self.error=False;self.last=None;self.index=-1
        self.underruns=0;self.peak_queue=0
        self.thread=threading.Thread(target=self._run,args=(payload,count),daemon=True,name='fx240-gif-experiment')
        self.thread.start()
        if not self.ready.wait(3) or self.error:
            self.close();raise ValueError('Experimental decoder could not prepare a frame')

    def _run(self,payload,count):
        try:
            with Image.open(io.BytesIO(payload)) as source:
                index=0
                while not self.stop.is_set():
                    source.seek(index%count);frame=canvas(source.copy())
                    while not self.stop.is_set():
                        try:self.queue.put((index,frame),timeout=.05);break
                        except queue.Full:continue
                    self.peak_queue=max(self.peak_queue,self.queue.qsize())
                    self.ready.set();index+=1
        except (OSError,ValueError,EOFError,IndexError,struct.error,Image.DecompressionBombError):
            self.error=True;self.ready.set()

    def next(self,wait=False):
        try:return self.queue.get(timeout=3) if wait else self.queue.get_nowait()
        except queue.Empty:
            if self.error:raise ValueError('Experimental GIF decoding failed')
            if wait:raise ValueError('Experimental GIF decoder timed out')
            return None

    def frame(self,index):
        while self.index<index:
            item=self.next(wait=self.last is None)
            if item is None:self.underruns+=1;break
            self.index,self.last=item
        return self.last,self.index

    def close(self):
        self.stop.set();self.thread.join(timeout=3)
        if self.thread.is_alive():raise RuntimeError('Experimental decoder did not stop')
        while not self.queue.empty():self.queue.get_nowait()
        self.last=None


def verify(payload,count):
    decoder=Buffered(payload,count,capacity=3)
    checked=0
    try:
        with Image.open(io.BytesIO(payload)) as source:
            for cycle in range(2):
                for index in range(count):
                    source.seek(index);reference=canvas(source.copy())
                    ordinal,frame=decoder.next(wait=True)
                    if ordinal!=cycle*count+index or frame.tobytes()!=reference.tobytes():
                        raise ValueError('Experimental frames differ from sequential Pillow composition')
                    checked+=1
        return {'frames_checked':checked,'loops_checked':2,'reference_matches':True}
    finally:decoder.close()


def percentile(values,fraction):return sorted(values)[min(len(values)-1,int((len(values)-1)*fraction))]


def benchmark(payload,mode,seconds,fps,capacity):
    startup=time.perf_counter();size,durations=inspect(payload)
    player=Eager(payload,len(durations)) if mode=='eager' else Buffered(payload,len(durations),capacity)
    ends=[];total=0
    for duration in durations:total+=duration;ends.append(total)
    font=ImageFont.truetype(str(Path(__file__).resolve().parents[1]/'src/fx240/assets/fonts/Outfit.ttf'),36)
    startup_ms=(time.perf_counter()-startup)*1000
    costs=[];repeats=0;last=-1;deadline_misses=0;late_ticks=0
    began=time.perf_counter();cpu=time.process_time()
    try:
        for tick in range(math.ceil(seconds*fps)):
            due=began+tick/fps
            time.sleep(max(0,due-time.perf_counter()))
            start=time.perf_counter()
            if start-due>.005:late_ticks+=1
            elapsed=start-began
            wanted=int(elapsed/total)*len(durations)+min(bisect_right(ends,elapsed%total),len(durations)-1)
            frame,ordinal=player.frame(wanted)
            if ordinal==last:repeats+=1
            last=ordinal
            composed=frame.copy();draw=ImageDraw.Draw(composed)
            draw.text((120,110),'45.0 C',font=font,anchor='mm',fill='white')
            draw.arc((8,8,232,232),tick*4%360,tick*4%360+55,fill='#73dfc1',width=8)
            encode(composed,quality=65,rotation=180)
            cost=(time.perf_counter()-start)*1000;costs.append(cost)
            if cost>1000/fps:deadline_misses+=1
        wall=time.perf_counter()-began;cpu=time.process_time()-cpu
        return {'mode':mode,'source_frames':len(durations),'source_size':list(size),'source_bytes':len(payload),
                'target_fps':fps,'ticks':len(costs),'startup_ms':round(startup_ms,2),
                'render_ms':{key:round(percentile(costs,value),3) for key,value in [('p50',.5),('p95',.95),('p99',.99),('max',1)]},
                'render_deadline_misses':deadline_misses,'scheduler_late_ticks':late_ticks,
                'buffer_underruns':player.underruns,'repeated_source_frames':repeats,
                'peak_decoded_queue_frames':player.peak_queue,'peak_rss_mib':round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2),
                'playback_cpu_seconds':round(cpu,3),'playback_wall_seconds':round(wall,3),
                'limits':'Offline composition/JPEG timing on Linux; no USB or physical LCD FPS measurement. Queue pixels exclude source bytes, Pillow state, and transient images.'}
    finally:player.close()


def generate(path,count):
    if not 1<=count<=720:raise ValueError('Synthetic generation supports 1..720 frames')
    frames=[]
    for index in range(count):
        frame=Image.new('RGB',(240,240),'#0e1216');draw=ImageDraw.Draw(frame)
        for stripe in range(0,240,12):draw.line((stripe,0,(stripe+index)%240,239),fill=((stripe+index)%256,(index*3)%256,120),width=5)
        x=index%200;draw.ellipse((x,90,x+30,120),fill='#73dfc1')
        draw.text((12,12),str(index),fill='white');frames.append(frame)
    with path.open('xb') as destination:
        frames[0].save(destination,format='GIF',save_all=True,append_images=frames[1:],duration=40,loop=0,disposal=2,optimize=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('generate','benchmark','verify'))
    parser.add_argument('file',type=Path)
    parser.add_argument('--frames',type=int,default=360)
    parser.add_argument('--mode',choices=('eager','buffered'),default='buffered')
    parser.add_argument('--seconds',type=float,default=8)
    parser.add_argument('--fps',type=int,default=24)
    parser.add_argument('--buffer',type=int,default=12)
    args=parser.parse_args()
    if not math.isfinite(args.seconds) or not 1<=args.seconds<=60 or not 1<=args.fps<=24 or not 1<=args.buffer<=24:
        parser.error('Use seconds 1..60, FPS 1..24, and buffer 1..24')
    if args.action=='generate':generate(args.file,args.frames);return
    payload=read_regular(args.file,MAX_FILE_BYTES)
    if args.action=='verify':
        _,durations=inspect(payload);result=verify(payload,len(durations))
    else:result=benchmark(payload,args.mode,args.seconds,args.fps,args.buffer)
    print(json.dumps(result))


if __name__=='__main__':main()
