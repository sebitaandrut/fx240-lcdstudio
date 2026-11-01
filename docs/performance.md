# Performance and measurement limits

Measurements below were made on **one Arch Linux/Wayland system and one FX240**. The production application remains capped at **24 FPS**. Higher rates used isolated experimental instruments, not saved application presets. They do not establish a panel maximum, universal performance, or stable operation.

## Optical observations

A Gray-code row and its inverse identified successive source states. The owner selected 240 FPS camera capture; files reported approximately 29.985 FPS playback metadata. Capture cadence and independent exposures were not independently established. The analysis used a fixed crop; exposure, rolling shutter, JPEG artifacts, LCD response, and temporal blending affect readability.

| Target | IDs sent | Observed IDs, ≥1 sample | IDs with ≥2 samples |
| --- | ---: | ---: | ---: |
| 24 FPS | 240 | 240 | 240 |
| 30 FPS | 300 | 300 | 294 |
| 40 FPS | 400 | 382 | 361 |
| 48 FPS | 480 | 440 | 411 |
| 60 FPS | 600 | 533 | 492 |
| 90 FPS | 900 | 542 | 433 |

These counts use permissive decoding with an inverse-row check. Observed IDs were chronological; stricter confidence thresholds reduce coverage, especially at higher rates. The full confidence sensitivity and aggregate methods are retained in [evidence.json](evidence.json), not just the most favorable counts.

These are **diagnostic-region state observations**, not certified complete-frame FPS. Missing IDs alone do not prove LCD drops, and the approximately 53–54 observed states/s at higher targets does not identify a hardware ceiling. The initial binary-code attempt was inconclusive. Retaining 24 FPS is conservative; 30 FPS remains a candidate for later application validation.

## Host and preview throughput

With JPEG quality 65 and content-specific report sizes, short instruments reached approximately 60 host FPS at 1 ms inter-report delay and 90 at 0.5 ms. The production 33 ms preview queue poll limited a 60 FPS instrument to approximately 31 unique swap-associated IDs/s; a 4 ms experimental poll removed that bottleneck.

Host FPS counts completed processing/writes, not LCD presentation. Qt swap-associated IDs are a GUI-delivery proxy, not exact GPU texture or optical presentation IDs. An early direct-callback instrument hung during 90 FPS shutdown; it failed and was replaced with GUI-thread queued notifications. A corrected short trial completed normally, without establishing long-term stability. Complex GIFs can produce larger JPEGs and lower throughput than Focus.

## Ten-minute native USB trial

| Measurement | Experimental result |
| --- | --- |
| Settings | Target 60 FPS, quality 65, delay 1 ms, preview poll 4 ms |
| Completed/sent/applied frames | 35,981; approximately 59.997 host FPS |
| Reported output/configuration errors | 0; worker stopped normally |
| RSS range | 270.25–274.17 MiB |
| Post-warmup fitted RSS slope | Approximately +0.058 MiB/min |
| Mean CPU | Approximately 27.49% of one core |
| Descriptors / OS threads | 28 / 25 throughout the measured samples |
| Distinct Qt swap-associated IDs | 31,001; 86.16% coverage |

The monitor powered off or the screen locked in the final segment: USB continued but Qt swaps stopped. This is not uninterrupted ten-minute preview presentation. The workload exercised live UI settings and partly overlapped local video analysis. It predates the independent standby helper and later visual changes; these resource numbers are not a profile of the current packaged 8 px build. A small RSS slope neither identifies nor excludes a leak. Multi-hour native validation remains pending.

The earlier two-minute synthetic/offscreen run is omitted here because it is a different workload and less representative. Aggregate native run context and statistics remain in [evidence.json](evidence.json); per-second traces and private recordings are excluded.

## Repeating measurements

`tools/benchmark_stream.py` and `tools/benchmark_gui.py` measure host/USB and native Qt activity. Both require explicit `--send` for USB and use verified identity/locking. Close other senders first; higher-rate experiments require their explicit experimental option where applicable. Use an external timeout for native instrument trials and retain failures.

For a no-USB resource exercise:

```bash
PYTHONPATH=src .venv/bin/python tools/profile_desktop.py \
  --duration 3600 --warmup 60 --output /tmp/fx240-profile.json
```

This offscreen synthetic tool is not a native LCD endurance test. `tools/analyze_counter_video.py` optionally decodes private diagnostic footage using the matching host trial boundaries and a calibrated crop; install `.[analysis]` only for analysis. Preserve confidence sensitivity and visibility context. Review every output before sharing, and do not equate video container FPS with physical exposures.
