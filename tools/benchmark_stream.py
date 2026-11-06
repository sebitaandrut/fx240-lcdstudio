# SPDX-License-Identifier: GPL-3.0-or-later
"""Experimental host-throughput sweep and optical-counter generator.

Uses a separate benchmark rate limit. Requires explicit --send for USB.
Host write completion is not evidence of physical LCD presentation.
"""
import argparse
from datetime import datetime,timezone
import io,json,math,os,signal,statistics,time
from pathlib import Path
from PIL import Image,ImageDraw
from fx240.focus import Focus,font,resolve_font
from fx240.idle import render_idle
from fx240.media import encode
from fx240.protocol import build_reports
from fx240.session import find_devices
from fx240.transport import Hidraw


def percentile(values,p):
    if not values:return None
    ordered=sorted(values)
    return ordered[min(len(ordered)-1,math.ceil(len(ordered)*p)-1)]


def diagnostic_frame(number,fps,pattern="binary"):
    image=Image.new('RGB',(240,240),'#080b0e');draw=ImageDraw.Draw(image)
    face=font(resolve_font(),24,500) # cached face is 48 px at the supersampling scale
    small=font(resolve_font(),7,450)
    draw.ellipse((4,4,236,236),outline='#73dfc1',width=3)
    draw.text((120,42),f'{fps:g} FPS TARGET',font=small,anchor='mm',fill='white')
    draw.text((120,100),f'{number%10000:04d}',font=face,anchor='mm',fill='white')
    # 12-bit frame ID plus a four-bit folded check nibble, MSB first.
    n=number%4096;check=(n^(n>>4)^(n>>8)^0xA)&15
    word=(n<<4)|check
    for bit in range(16) if pattern=="binary" else []:
        x=65+(bit%8)*14;y=150+(bit//8)*18
        draw.rectangle((x,y,x+11,y+13),fill='white' if word&(1<<(15-bit)) else '#202830')
    if pattern=='gray':
        gray=n^(n>>1)
        for bit in range(12):
            state=bool(gray&(1<<(11-bit)))
            x=55+bit*11
            for y,on in ((151,state),(169,not state)):
                draw.rectangle((x,y,x+8,y+10),fill='white' if on else '#202830')
        draw.text((120,128),'GRAY / INVERSE',font=small,anchor='mm',fill='#73dfc1')
    angle=number*math.tau/120
    orbit=104 if pattern=='gray' else 84
    x=120+orbit*math.cos(angle);y=120+orbit*math.sin(angle)
    draw.ellipse((x-5,y-5,x+5,y+5),fill='#73dfc1')
    return image


def run_profile(device,fps,delay,seconds,content,log,sequence,pattern="binary"):
    theme=Focus(24,temperature_decimals=1)
    tx=[];pipeline=[];starts=[];sizes=[];reports_count=[]
    began=time.monotonic();cpu=time.process_time();target=began
    deadline=began+seconds
    while time.monotonic()<deadline:
        time.sleep(max(0,target-time.monotonic()))
        if time.monotonic()>=deadline:break
        start=time.monotonic();elapsed=start-began
        frame=theme(elapsed)[0] if content=='focus' else diagnostic_frame(sequence,fps,pattern)
        jpeg=encode(frame,65,180);reports=build_reports(jpeg)
        duration,_=device.send(reports,delay) if device else (0,[])
        # Include exact-JPEG preview decode costs, as in the desktop worker.
        with Image.open(io.BytesIO(jpeg)) as decoded:decoded.convert('RGB').rotate(-180)
        done=time.monotonic()
        tx.append(duration);pipeline.append((done-start)*1000);starts.append(start)
        sizes.append(len(jpeg));reports_count.append(len(reports))
        log.write(json.dumps({'frame':sequence,'target_fps':fps,'delay_ms':delay,'content':content,
                              'start_monotonic':start,'pipeline_done_monotonic':done,
                              'jpeg_bytes':len(jpeg),'reports':len(reports)})+'\n')
        sequence+=1
        target=max(target+1/fps,time.monotonic())
    finished=time.monotonic();intervals=[(b-a)*1000 for a,b in zip(starts,starts[1:])]
    result={'content':content,'pattern':pattern,'target_fps':fps,'delay_ms':delay,'quality':65,'rotation':180,
            'frames':len(starts),'duration_s':finished-began,
            'host_completion_fps':len(starts)/(finished-began),
            'start_interval_fps':(len(starts)-1)/(starts[-1]-starts[0]) if len(starts)>1 else None,
            'interval_ms_p95':percentile(intervals,.95),'pipeline_ms_mean':statistics.mean(pipeline),
            'pipeline_ms_p95':percentile(pipeline,.95),'pipeline_ms_p99':percentile(pipeline,.99),
            'transmission_ms_mean':statistics.mean(tx),'transmission_ms_p95':percentile(tx,.95),
            'over_budget_frames':sum(x>1000/fps for x in pipeline),
            'jpeg_bytes_range':[min(sizes),max(sizes)],'reports_range':[min(reports_count),max(reports_count)],
            'cpu_one_core_percent':100*(time.process_time()-cpu)/(finished-began)}
    return result,sequence


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--send',action='store_true')
    parser.add_argument('--device')
    parser.add_argument('--mode',choices=('sweep','optical'),default='sweep')
    parser.add_argument('--pattern',choices=('binary','gray'),default='binary')
    parser.add_argument('--seconds',type=float,default=8)
    parser.add_argument('--fps',type=float,nargs='+',default=[24,30,40,48,60])
    parser.add_argument('--delays',type=float,nargs='+',default=[2,1,.5])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not 0<args.seconds<=3600 or any(not 0<f<=120 for f in args.fps) or any(not 0<=d<=10 for d in args.delays):parser.error('Invalid benchmark bounds')
    if args.send and not args.device:
        devices=find_devices()
        if len(devices)!=1:parser.error('Exactly one LCD or explicit device is required')
        args.device=devices[0]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    records=[];sequence=0;device=None;error=None
    started=datetime.now(timezone.utc).isoformat()
    def interrupt(signum,frame):raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,interrupt)
    try:
        if args.send:device=Hidraw(args.device).__enter__()
        with args.output.with_suffix('.jsonl').open('w') as log:
            for delay in args.delays:
                for fps in args.fps:
                    record,sequence=run_profile(device,fps,delay,args.seconds,'focus' if args.mode=='sweep' else 'diagnostic',log,sequence,args.pattern)
                    records.append(record);log.flush()
                    args.output.write_text(json.dumps({'started_utc':started,'scope':'host loop; not optical refresh','usb':args.send,'profiles':records},indent=2)+'\n')
                    print(json.dumps(record),flush=True)
                    if args.mode=='sweep' and (record['host_completion_fps']<fps*.95 or record['pipeline_ms_p95']>1000/fps):
                        print('Higher targets skipped for this delay: host timing budget exceeded',flush=True)
                        break
    except KeyboardInterrupt:error='Interrupted'
    except Exception as exc:error=str(exc)
    finally:
        if device:
            try:device.send(build_reports(encode(render_idle(),65,180)),2)
            except Exception as exc:error=(error+'; ' if error else '')+'Standby failed: '+str(exc)
            device.__exit__(None,None,None)
        args.output.write_text(json.dumps({'started_utc':started,'scope':'host loop; not optical refresh','usb':args.send,'error':error,'profiles':records},indent=2)+'\n')
    if error:raise SystemExit(error)


if __name__=='__main__':main()
