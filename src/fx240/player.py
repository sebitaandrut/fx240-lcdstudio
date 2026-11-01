"""Bounded wall-clock playback; rebase late deadlines instead of catch-up bursts."""
import time
from .protocol import build_reports
from .media import encode


def play(frame_at, duration, transport=None, delay_ms=10, quality=85, rotation=180,
         clock=time.monotonic, sleep=time.sleep):
    samples = []
    start = clock()
    target = start
    while clock() - start < duration:
        sleep(max(0, min(target, start+duration)-clock()))
        if clock() - start >= duration:
            break
        actual = clock()
        image, interval = frame_at(actual-start)
        rendered = clock()
        jpeg = encode(image, quality, rotation)
        encoded = clock()
        reports = build_reports(jpeg)
        tx, writes = transport.send(reports, delay_ms) if transport else (0, [])
        end = clock()
        samples.append({"jpeg_bytes": len(jpeg), "reports": len(reports),
                        "render_ms": (rendered-actual)*1000, "encode_ms": (encoded-rendered)*1000,
                        "pipeline_ms": (end-actual)*1000, "start_offset_ms": (actual-start)*1000,
                        "transmission_ms": tx, "write_ms": writes,
                        "lateness_ms": max(0, (actual-target)*1000),
                        "overrun_ms": max(0, (end-target-interval)*1000)})
        target = max(target+interval, end)
    return samples


def summary(samples):
    result = {"frames": len(samples)}
    for field in ("jpeg_bytes", "reports", "transmission_ms", "lateness_ms", "overrun_ms", "write_ms", "render_ms", "encode_ms", "pipeline_ms"):
        values = ([x for row in samples for x in row[field]] if field == "write_ms"
                  else [row[field] for row in samples if field in row])
        values.sort()
        if not values:
            continue
        def percentile(p):
            index = (len(values)-1)*p
            low = int(index)
            high = min(low+1, len(values)-1)
            return values[low]+(values[high]-values[low])*(index-low)
        result[field] = {"min": values[0], "mean": sum(values)/len(values),
                         **{f"p{p}": percentile(p/100) for p in (50,90,95,99)}, "max": values[-1]}
    starts = [row["start_offset_ms"] for row in samples if "start_offset_ms" in row]
    if len(starts) > 1:
        gaps = [b-a for a,b in zip(starts,starts[1:])]
        result["frame_spacing_ms"] = {"min": min(gaps), "mean": sum(gaps)/len(gaps), "max": max(gaps)}
    return result
