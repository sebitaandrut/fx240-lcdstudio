"""Decode the private optical counter video; NumPy/OpenCV are analysis-only extras.

Rates are conditional on the user-declared capture FPS, not playback metadata.
Unobserved IDs do not, by themselves, prove dropped LCD frames.
"""
import argparse,json,math,statistics
from collections import defaultdict
from pathlib import Path
import cv2
import numpy as np


def sample_word(gray,pattern="binary"):
    samples=[]
    count=16 if pattern=='binary' else 24
    for bit in range(count):
        x=round(70.5+(bit%8)*14) if pattern=='binary' else 59+(bit%12)*11
        y=round(156.5+(bit//8)*18) if pattern=='binary' else 156+(bit//12)*18
        radius=2 if pattern=='binary' else 1
        samples.append(float(np.median(gray[y-radius:y+radius+1,x-radius:x+radius+1])))
    low,high=min(samples),max(samples)
    if high-low<100:return None,False,0
    normalized=[(value-low)/(high-low) for value in samples]
    strength=min(abs(value-.5)*2 for value in normalized)
    word=0
    for value in normalized:word=(word<<1)|int(value>.5)
    if pattern=='binary':
        number=word>>4
        check=(word&15)==((number^(number>>4)^(number>>8)^0xA)&15)
    else:
        encoded=word>>12;inverse=word&4095
        check=inverse==(encoded^4095)
        number=encoded
        shifted=encoded>>1
        while shifted:
            number^=shifted;shifted>>=1
    return number,check,strength


def decode_word(gray,confidence=.5,pattern="binary"):
    number,check,strength=sample_word(gray,pattern)
    if number is None:return None,'low_contrast',0
    if strength<confidence:return None,'ambiguous',strength
    if not check:return None,'check_failed',strength
    return number,'valid',strength


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video',type=Path)
    parser.add_argument('--pattern',choices=('binary','gray'),default='binary')
    parser.add_argument('--trial-json',type=Path,help='Matching benchmark_stream result, for exact profile/ID ranges')
    parser.add_argument('--crop',type=int,nargs=4,required=True,metavar=('X','Y','W','H'))
    parser.add_argument('--capture-fps',type=float,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not math.isfinite(args.capture_fps) or args.capture_fps<=0:parser.error('Positive capture FPS required')
    profiles_spec=[(0,359,24),(360,1259,60)]
    if args.trial_json:
        trial=json.loads(args.trial_json.read_text())
        profiles_spec=[];offset=0
        for profile in trial['profiles']:
            profiles_spec.append((offset,offset+profile['frames']-1,profile['target_fps']))
            offset+=profile['frames']
        if offset>4096:parser.error('Counter wrap requires a separate unwrapping analysis')
    max_id=max(last for first,last,target in profiles_spec)
    cv2.setNumThreads(1)
    options=[cv2.CAP_PROP_N_THREADS,1] if hasattr(cv2,'CAP_PROP_N_THREADS') else []
    cap=cv2.VideoCapture(str(args.video),cv2.CAP_FFMPEG,options)
    if not cap.isOpened():raise SystemExit('Video could not be opened')
    playback=cap.get(cv2.CAP_PROP_FPS)
    seen=defaultdict(list);statuses=defaultdict(int);index=0;details=[]
    thresholds={str(level):defaultdict(list) for level in (0.0,0.2,0.35,0.5)}
    exact_duplicates=0;previous=None
    x,y,w,h=args.crop
    with args.output.with_suffix('.jsonl').open('w') as log:
        while True:
            okay,frame=cap.read()
            if not okay:break
            crop=frame[y:y+h,x:x+w]
            if crop.size==0:raise SystemExit('Crop is outside the rotated image')
            gray=cv2.cvtColor(cv2.resize(crop,(240,240),interpolation=cv2.INTER_AREA),cv2.COLOR_BGR2GRAY)
            if previous is not None and np.array_equal(gray,previous):exact_duplicates+=1
            previous=gray
            candidate,check,confidence=sample_word(gray,args.pattern)
            if candidate is not None and check and candidate<=max_id:
                for level,states in thresholds.items():
                    if confidence>=float(level):states[candidate].append(index)
            number,status,confidence=decode_word(gray,pattern=args.pattern)
            if number is not None and number>max_id:number,status=None,'outside_transmitted_range'
            statuses[status]+=1
            if number is not None:seen[number].append(index)
            log.write(json.dumps({'video_frame':index,'counter':number,'status':status,'confidence':round(confidence,4),'candidate':candidate,'check_valid':check})+'\n')
            index+=1
            if index%1500==0:print('Decoded',index,'video frames',flush=True)
    cap.release()
    profiles=[]
    for first,last,target in profiles_spec:
        numbers=sorted(n for n in seen if first<=n<=last)
        confirmed=[n for n in numbers if len(seen[n])>=2 and max(seen[n])-min(seen[n])<=24]
        item={'target_fps':target,'any_checked_ids':len(numbers),'confirmed_ids_two_samples':len(confirmed)}
        if len(confirmed)>1:
            mids=[statistics.median(seen[n]) for n in confirmed]
            ordered=all(a<b for a,b in zip(mids,mids[1:]))
            span=(mids[-1]-mids[0])/args.capture_fps
            item.update({'first_id':confirmed[0],'last_id':confirmed[-1],
                'time_span_s_at_declared_capture_rate':span,
                'confirmed_readable_state_rate_hz':(len(confirmed)-1)/span,
                'unique_id_coverage_in_observed_range':len(confirmed)/(confirmed[-1]-confirmed[0]+1),
                'chronological_order_valid':ordered,
                'camera_samples_per_confirmed_id_median':statistics.median(len(seen[n]) for n in confirmed),
                'first_last_camera_frame':[mids[0],mids[-1]]})
        profiles.append(item)
    sensitivity={}
    for level,states in thresholds.items():
        rows=[]
        for first,last,target in profiles_spec:
            numbers=sorted(n for n in states if first<=n<=last)
            confirmed=[n for n in numbers if len(states[n])>=2 and max(states[n])-min(states[n])<=24]
            mids=[statistics.median(states[n]) for n in confirmed]
            rows.append({'target':target,'checked_ids':len(numbers),'confirmed_ids':len(confirmed),
                'first_id':confirmed[0] if confirmed else None,'last_id':confirmed[-1] if confirmed else None,
                'rate_hz':(len(confirmed)-1)*args.capture_fps/(mids[-1]-mids[0]) if len(confirmed)>1 else None,
                'order_valid':all(a<b for a,b in zip(mids,mids[1:])),
                'coverage':len(confirmed)/(confirmed[-1]-confirmed[0]+1) if confirmed else None})
        sensitivity[level]=rows
    result={'pattern':args.pattern,'opencv_version':cv2.__version__,'numpy_version':np.__version__,'method':'Fixed crop, center-patch median, contrast >=100, per-bit confidence >=0.5; '+('folded 4-bit check' if args.pattern=='binary' else 'Gray plus inverse-row check'),
            'video_frames_decoded':index,'playback_fps_metadata':playback,
            'capture_fps_user_declared':args.capture_fps,'capture_rate_independently_verified':False,
            'estimated_capture_duration_s':index/args.capture_fps,'crop_after_rotation':args.crop,
            'classification':dict(statuses),'profiles':profiles,'confidence_sensitivity':sensitivity,
            'exact_duplicate_normalized_images':exact_duplicates,
            'limits':['Rates depend on capture FPS declaration and independent camera exposures.',
                      'A readable barcode state does not establish a complete tear-free LCD frame.',
                      'Unobserved states may reflect exposure, rolling shutter, LCD response, or decoding rejection.',
                      'This analysis matches only the supplied transmitted profile and ID ranges.']}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
