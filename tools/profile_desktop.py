"""Bounded desktop soak measurement using synthetic sensors and no USB access.

Run from the repository with PYTHONPATH=src .venv/bin/python tools/profile_desktop.py.
CPU percent is relative to one core; RSS includes Qt/Pillow/native allocations.
This is a measurement tool, not a proof of leak freedom or physical USB performance.
"""
import argparse
import json
import os
from pathlib import Path
import statistics
import time

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from fx240.gui import create_engine,dispose_engine
from fx240.session import Settings
from fx240.telemetry import Metric


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration',type=int,default=300)
    parser.add_argument('--warmup',type=int,default=30)
    parser.add_argument('--output',type=Path,default=Path('desktop-profile.json'))
    args=parser.parse_args()
    if args.warmup<0 or args.duration<args.warmup+10:
        parser.error('Duration must exceed warmup by at least ten seconds')
    app=QGuiApplication([])
    began=time.monotonic()
    def sensors():
        return [Metric('ct','CPU synthetic',40+(int(time.monotonic()-began)%20)/10,'C','synthetic'),
                Metric('cf','CPU synthetic',4200,'MHz','synthetic'),
                Metric('gt','GPU synthetic',38,'C','synthetic'),
                Metric('gf','GPU synthetic',1800,'MHz','synthetic')]
    engine,bridge=create_engine(app,Settings(),provider=sensors)
    bridge.start({},False)
    rows=[]
    previous_wall=began
    previous_cpu=time.process_time()
    midpoint=args.warmup+(args.duration-args.warmup)/2
    def tick():
        nonlocal previous_cpu,previous_wall
        now=time.monotonic()
        elapsed=now-began
        cpu=time.process_time()
        fields=Path('/proc/self/statm').read_text().split()
        phase='warmup' if elapsed<args.warmup else 'steady' if elapsed<midpoint else 'live_edits'
        rows.append({'seconds':round(elapsed,3),'phase':phase,
                     'rss_mib':int(fields[1])*os.sysconf('SC_PAGE_SIZE')/1024**2,
                     'cpu_one_core_percent':100*(cpu-previous_cpu)/(now-previous_wall),
                     'fds':len(list(Path('/proc/self/fd').iterdir())),
                     'threads':len(list(Path('/proc/self/task').iterdir())),
                     'frames':bridge.session.frames,'revision':bridge.session.config_revision})
        previous_cpu,previous_wall=cpu,now
        engine.rootObjects()[0].setProperty('page',(len(rows)//5)%4)
        if phase=='live_edits':
            bridge.applySettings({'weight':350 if len(rows)%2 else 500,
                                  'decimals':bool(len(rows)%2),'quality':65 if len(rows)%2 else 75})
        if elapsed>=args.duration:
            timer.stop()
            bridge.stop()
            app.quit()
    timer=QTimer();timer.setInterval(1000);timer.timeout.connect(tick);timer.start()
    app.exec()
    bridge.session.thread.join(5)
    summaries={}
    for phase in ('steady','live_edits'):
        subset=[r for r in rows if r['phase']==phase]
        if not subset:continue
        x=[r['seconds'] for r in subset];y=[r['rss_mib'] for r in subset]
        xm,ym=statistics.mean(x),statistics.mean(y)
        slope=sum((a-xm)*(b-ym) for a,b in zip(x,y))/sum((a-xm)**2 for a in x)*60
        edge=max(1,min(10,len(y)//3))
        summaries[phase]={'samples':len(y),'rss_min_mib':min(y),'rss_max_mib':max(y),
            'rss_start_median_mib':statistics.median(y[:edge]),
            'rss_end_median_mib':statistics.median(y[-edge:]),'rss_slope_mib_per_min':slope,
            'cpu_mean_one_core_percent':statistics.mean(r['cpu_one_core_percent'] for r in subset),
            'fds_range':[min(r['fds'] for r in subset),max(r['fds'] for r in subset)],
            'threads_range':[min(r['threads'] for r in subset),max(r['threads'] for r in subset)]}
    result={'scope':'Qt software/offscreen + Pillow + synthetic sensors; no USB',
            'duration_seconds':rows[-1]['seconds'],'target_fps':24,
            'frames':bridge.session.frames,'config_revisions':bridge.session.config_revision,
            'worker_error':bridge.session.error,'config_error':bridge.session.config_error,
            'worker_stopped':not bridge.session.thread.is_alive(),'summary':summaries,'samples':rows}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='samples'},indent=2))
    dispose_engine(engine)
    if result['worker_error'] or result['config_error'] or not result['worker_stopped']:
        raise SystemExit(1)


if __name__=='__main__':main()
