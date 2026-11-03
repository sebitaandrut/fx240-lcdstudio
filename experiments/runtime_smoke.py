# SPDX-License-Identifier: GPL-3.0-or-later
"""Full-renderer host timing with synthetic telemetry and a forbidden USB transport."""
import argparse
from dataclasses import replace
import json
import math
import queue
import resource
import threading
import time
from pathlib import Path
from fx240 import gifstream
from fx240.scene import default_scene,layer,scene_json
from fx240.session import Session,Settings
from fx240.telemetry import Metric


def run(first,second=None,seconds=8):
    first=Path(first).absolute();second=Path(second).absolute() if second else None
    config=Settings(background_path=str(first))
    if second:
        scene=default_scene();scene['layers']=[layer('layer-6','media',path=str(first)),layer('layer-7','media',path=str(second),opacity=.5)]+scene['layers']
        config=replace(config,layout_mode='editor',scene_json=scene_json(scene))
    metrics=[Metric('ct','CPU synthetic',45.1,'C','synthetic'),Metric('cf','CPU synthetic',4200,'MHz','synthetic'),Metric('gt','GPU synthetic',38,'C','synthetic'),Metric('gf','GPU synthetic',1800,'MHz','synthetic')]
    def forbid(path):raise AssertionError('Runtime smoke tests cannot access USB')
    session=Session(config,provider=lambda:metrics,transport_factory=forbid)
    samples=[];maximum_queue=0;underruns=0
    session.start();started=None;cpu=0
    deadline=time.monotonic()+10
    try:
        while True:
            try:event=session.events.get(timeout=.2)
            except queue.Empty:
                if time.monotonic()>deadline:raise RuntimeError('Runtime smoke test timed out')
                continue
            if event['kind']=='stopped' or event.get('config_error'):raise RuntimeError('Runtime smoke test could not render the clip')
            if started is None:started=time.monotonic();cpu=time.process_time();deadline=started+seconds+2
            samples.append(event['pipeline_ms'])
            stats=gifstream.statistics(session.thread)
            maximum_queue=max(maximum_queue,stats.get('queued_frames',0));underruns=max(underruns,stats.get('underruns',0))
            if time.monotonic()-started>=seconds:break
        elapsed=time.monotonic()-started;cpu=time.process_time()-cpu
    finally:session.stop();session.thread.join(5)
    if session.thread.is_alive() or gifstream.statistics(session.thread).get('streams') or any(worker.name=='fx240-gif-stream' and worker.is_alive() for worker in threading.enumerate()):
        raise RuntimeError('Runtime smoke resources did not close')
    ordered=sorted(samples)
    return {'renderer':'two media layers plus telemetry' if second else 'Focus plus GIF',
            'target_fps':24,'frames':len(samples),'observed_host_fps':round((len(samples)-1)/elapsed,2),
            'pipeline_p95_ms':round(ordered[int((len(ordered)-1)*.95)],3),'pipeline_max_ms':round(max(samples),3),
            'pipeline_deadline_misses':sum(value>1000/24 for value in samples),
            'underruns':underruns,'max_queued_frames':maximum_queue,'peak_rss_mib':round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2),
            'cpu_seconds':round(cpu,3),'playback_seconds':round(elapsed,3),'resources_closed':True,
            'scope':'Host backend only; synthetic telemetry; no QML presentation, USB, or physical LCD measurement'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file',type=Path);parser.add_argument('--second',type=Path)
    parser.add_argument('--seconds',type=float,default=8);args=parser.parse_args()
    if not math.isfinite(args.seconds) or not 1<=args.seconds<=60:parser.error('Seconds must be 1..60')
    print(json.dumps(run(args.file,args.second,args.seconds)))


if __name__=='__main__':main()
