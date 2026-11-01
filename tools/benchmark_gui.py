# SPDX-License-Identifier: GPL-3.0-or-later
"""Measure production desktop or diagnostic preview with real Qt swap signals.

A frameSwapped signal counts a Qt buffer swap, not compositor/monitor/LCD proof.
Higher FPS are isolated benchmark settings, never saved or enabled in the app.
"""
import argparse
from dataclasses import dataclass,replace
from collections import deque
from datetime import datetime,timezone
import json,math,os,platform,signal,threading,time
from pathlib import Path
from PySide6.QtCore import QTimer,Qt
from PySide6.QtGui import QGuiApplication
from fx240.gui import create_engine,dispose_engine
from fx240.session import Settings,Session,find_devices
from fx240.focus import Focus
from benchmark_stream import diagnostic_frame,percentile


@dataclass(frozen=True)
class BenchmarkSettings(Settings):
    def validate(self):
        if not math.isfinite(self.fps) or not 1<=self.fps<=120:raise ValueError('Benchmark FPS: 1..120')
        Settings.validate(replace(self,fps=min(self.fps,24)))


class TimedFocus(Focus):
    def __init__(self,fps,**kwargs):
        super().__init__(min(fps,24),**kwargs)
        self.fps=fps


class CounterTheme:
    def __init__(self,fps,provider,**kwargs):
        self.fps=fps;self.provider=provider;self.sampled_at=None;self.number=0
        self.arc_from=self.arc_to=0
    def sample(self,elapsed):self.provider();self.sampled_at=elapsed
    def inherit_motion(self,other,elapsed):self.number=other.number
    def arc_value(self,elapsed):return 0
    def __call__(self,elapsed):
        if self.sampled_at is None or elapsed-self.sampled_at>=1:self.sample(elapsed)
        frame=diagnostic_frame(self.number,self.fps);self.number+=1
        return frame,1/self.fps


class Histogram:
    def __init__(self):self.bins={};self.count=0;self.total=0;self.maximum=0
    def add(self,value):
        bucket=min(100000,max(0,round(value*10)))
        self.bins[bucket]=self.bins.get(bucket,0)+1
        self.count+=1;self.total+=value;self.maximum=max(self.maximum,value)
    def summary(self):
        result={'count':self.count,'mean':self.total/self.count if self.count else None,'max':self.maximum}
        for p in (50,95,99):
            target=math.ceil(self.count*p/100);seen=0;value=None
            for bucket,count in sorted(self.bins.items()):
                seen+=count
                if seen>=target:value=bucket/10;break
            result['p'+str(p)]=value
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=float,default=600)
    parser.add_argument('--send',action='store_true')
    parser.add_argument('--device')
    parser.add_argument('--fps',type=float,default=24)
    parser.add_argument('--delay-ms',type=float,default=2)
    parser.add_argument('--counter',action='store_true')
    parser.add_argument('--experimental',action='store_true')
    parser.add_argument('--poll-ms',type=int,default=33)
    parser.add_argument('--exercise-options',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not 1<=args.seconds<=7200:parser.error('Duration: 1..7200 seconds')
    if args.fps>24 and not args.experimental:parser.error('Higher rates require --experimental')
    if not 1<=args.poll_ms<=100:parser.error('Poll interval: 1..100 ms')
    if args.send and not args.device:
        nodes=find_devices()
        if len(nodes)!=1:parser.error('Exactly one LCD or explicit device required')
        args.device=nodes[0]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    frame_log=args.output.with_suffix('.jsonl').open('w',buffering=65536)
    resource_path=args.output.with_suffix('.resources.jsonl')
    resource_log=resource_path.open('w')
    app=QGuiApplication([])
    config=BenchmarkSettings(fps=args.fps,delay_ms=args.delay_ms,device=args.device) if args.experimental else Settings(fps=args.fps,delay_ms=args.delay_ms,device=args.device)
    config.validate()
    theme=CounterTheme if args.counter else TimedFocus
    tx=Histogram();pipeline=Histogram();swap_intervals=Histogram();lock=threading.Lock()
    counts={'generated':0,'sent':0,'applied':0,'swaps':0,'unique_swaps':0,'output_error_frames':0,'config_error_frames':0}
    previous_swap=None;first_swap=None;last_presented=None;synced=None
    first_generated=None;last_generated=None;last_applied=None
    def factory(settings,**kwargs):
        session=Session(settings,theme_factory=theme,**kwargs)
        original=session.publish
        def publish(event):
            nonlocal first_generated,last_generated
            if event['kind']=='frame':
                timestamp=time.monotonic()
                if first_generated is None:first_generated=timestamp
                last_generated=timestamp
                counts['generated']+=1;counts['sent']+=int(event['sent'])
                counts['output_error_frames']+=bool(event.get('output_error'))
                counts['config_error_frames']+=bool(event.get('config_error'))
                tx.add(event['transmission_ms']);pipeline.add(event['pipeline_ms'])
                frame_log.write(json.dumps({'kind':'generated','frame':event['frames'],
                    'host_elapsed_s':event['elapsed'],'sent':event['sent'],
                    'pipeline_ms':event['pipeline_ms'],'transmission_ms':event['transmission_ms'],
                    'reports':event['reports']})+'\n')
            original(event)
        session.publish=publish
        return session
    engine,bridge=create_engine(app,config,session_factory=factory)
    bridge.timer.setInterval(args.poll_ms)
    window=engine.rootObjects()[0]
    if args.experimental:
        from PySide6.QtCore import QObject
        control=window.findChild(QObject,'fpsControl')
        control.setProperty('to',120);control.setProperty('value',int(args.fps))
    window.setTitle('FX240 benchmark / '+str(args.fps)+' FPS / '+('COUNTER' if args.counter else 'FOCUS'))
    serial_to_frame={};original_apply=bridge.apply_frame
    def apply(event):
        nonlocal last_applied
        original_apply(event)
        serial_to_frame[bridge._frame]=event['frames']
        if event['frames']!=last_applied:counts['applied']+=1
        last_applied=event['frames']
        # Keep instrumentation memory bounded regardless of duration.
        for key in list(serial_to_frame):
            if key<bridge._frame-8:serial_to_frame.pop(key)
    bridge.apply_frame=apply
    def swap():
        nonlocal last_presented,previous_swap,first_swap,synced
        synced=last_applied
        now=time.monotonic()
        with lock:
            counts['swaps']+=1
            if synced is not None and synced!=last_presented:
                if previous_swap is not None:swap_intervals.add((now-previous_swap)*1000)
                if first_swap is None:first_swap=now
                previous_swap=now;last_presented=synced;counts['unique_swaps']+=1
    # Never execute Python callbacks on the Qt render thread: GUI shutdown may
    # wait for that thread while it is waiting for the GIL. Association is now
    # deliberately reported as a queued proxy, not a direct render-thread ID.
    window.frameSwapped.connect(swap,Qt.ConnectionType.QueuedConnection)
    started_utc=datetime.now(timezone.utc).isoformat();start=time.monotonic();last_wall=start;last_cpu=time.process_time()
    resources=deque(maxlen=60);sample_count=0;stopping=False;exit_requested=False
    def stop():
        nonlocal stopping
        if not stopping:
            stopping=True;bridge.stop()
    def finish_if_stopped():
        nonlocal exit_requested
        if stopping and not bridge.running and not exit_requested:
            exit_requested=True
            window.frameSwapped.disconnect(swap)
            frame_log.flush();resource_log.flush()
            QTimer.singleShot(50,app.quit)
    def tick():
        nonlocal last_wall,last_cpu,sample_count
        now=time.monotonic();cpu=time.process_time();elapsed=now-start
        rss=int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')/1024**2
        resources.append({'seconds':elapsed,'rss_mib':rss,'cpu_one_core_percent':100*(cpu-last_cpu)/(now-last_wall),
                          'fds':len(list(Path('/proc/self/fd').iterdir())),
                          'threads':len(list(Path('/proc/self/task').iterdir())),
                          'window_visible':window.isVisible(),'window_exposed':window.isExposed(),
                          'window_active':window.isActive(),**counts})
        sample_count+=1
        resource_log.write(json.dumps(resources[-1])+'\n')
        last_wall,last_cpu=now,cpu
        if args.exercise_options and not args.counter and not stopping and sample_count%10==0:
            from PySide6.QtCore import QObject
            window.findChild(QObject,'weightControl').setProperty('value',350 if sample_count%20 else 500)
            window.findChild(QObject,'cometStyleControl').setProperty('currentIndex',0 if sample_count%20 else 1)
            window.setProperty('lcdAccent','#73dfc1' if sample_count%20 else '#ac8aff')
        if sample_count%30==0:
            print(json.dumps({'seconds':round(elapsed,1),'rss_mib':round(rss,2),**counts}),flush=True)
        if elapsed>=args.seconds or counts['output_error_frames'] or counts['config_error_frames']:stop()
        finish_if_stopped()
    timer=QTimer();timer.setInterval(1000);timer.timeout.connect(tick)
    signal.signal(signal.SIGTERM,lambda *unused:stop())
    signal.signal(signal.SIGINT,lambda *unused:stop())
    bridge.changed.connect(finish_if_stopped)
    bridge.start({'device':args.device or ''},args.send);timer.start()
    deadline_timer=QTimer(app);deadline_timer.setSingleShot(True)
    deadline_timer.setTimerType(Qt.TimerType.PreciseTimer)
    deadline_timer.timeout.connect(stop);deadline_timer.start(round(args.seconds*1000))
    app.exec()
    bridge.stop();bridge.session.thread.join(5);timer.stop();frame_log.close();resource_log.close()
    resources=[json.loads(line) for line in resource_path.read_text().splitlines()]
    end=time.monotonic();elapsed=end-start
    warm=[row for row in resources if row['seconds']>=min(30,args.seconds/4)]
    if not warm:warm=resources
    import statistics
    mean_cpu=statistics.mean(row['cpu_one_core_percent'] for row in warm) if warm else None
    slope=None
    if len(warm)>1:
        xm=statistics.mean(r['seconds'] for r in warm);ym=statistics.mean(r['rss_mib'] for r in warm)
        slope=sum((r['seconds']-xm)*(r['rss_mib']-ym) for r in warm)/sum((r['seconds']-xm)**2 for r in warm)*60
    screen=window.screen()
    result={'started_utc':started_utc,'python':platform.python_version(),'qt_platform':app.platformName(),
            'screen_reported_refresh_hz':screen.refreshRate() if screen else None,
            'scope':'Queued Qt swap-associated applied IDs are a proxy, not monitor/LCD optical proof',
            'qt_callback_method':'GUI-thread queued frameSwapped; latest applied ID at callback delivery',
            'experimental':args.experimental,'counter':args.counter,'target_fps':args.fps,
            'delay_ms':args.delay_ms,'quality':65,'poll_ms':args.poll_ms,'usb':args.send,
            'duration_s':elapsed,'requested_duration_s':args.seconds,
            'completed_requested_duration':elapsed>=args.seconds*.99,**counts,
            'host_fps':(counts['generated']-1)/(last_generated-first_generated) if counts['generated']>1 else None,
            'unique_qt_swap_fps':(counts['unique_swaps']-1)/(previous_swap-first_swap) if counts['unique_swaps']>1 else None,
            'qt_swap_coverage':counts['unique_swaps']/counts['generated'] if counts['generated'] else None,
            'unique_qt_swap_fps_over_generation_span':counts['unique_swaps']/(last_generated-first_generated) if counts['generated']>1 else None,
            'first_generated_s':first_generated-start if first_generated else None,
            'last_generated_s':last_generated-start if last_generated else None,
            'first_unique_swap_s':first_swap-start if first_swap else None,
            'last_unique_swap_s':previous_swap-start if previous_swap else None,
            'no_swap_tail_s':last_generated-previous_swap if previous_swap and last_generated else None,
            'transmission_ms':tx.summary(),'worker_pipeline_ms':pipeline.summary(),'unique_swap_interval_ms':swap_intervals.summary(),
            'steady_cpu_one_core_percent':mean_cpu,'steady_rss_slope_mib_per_min':slope,
            'rss_mib_range':[min(r['rss_mib'] for r in resources),max(r['rss_mib'] for r in resources)] if resources else [],
            'worker_error':bridge.session.error,'output_error':bridge.session.output_error,
            'config_error':bridge.session.config_error,'worker_stopped':not bridge.session.thread.is_alive(),
            'samples':resources}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='samples'},indent=2),flush=True)
    dispose_engine(engine)
    if result['worker_error'] or result['output_error'] or result['config_error'] or not result['worker_stopped']:raise SystemExit(1)


if __name__=='__main__':main()
