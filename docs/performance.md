# Resource profiling

No exhaustive memory/CPU endurance validation has been completed. Unit tests do not establish stable long-term resource consumption. The first instrumented desktop run is recorded in [desktop-profile.json](desktop-profile.json); all readings and sources in the run are synthetic, with no personal sensor paths or photos.

## Initial measurement

The run used Qt Quick offscreen with software rendering, the full QML interface, Pillow rendering/JPEG encode/decode, synthetic 1 Hz sensors, and no USB device. It ran for 120.234 seconds at target 24 FPS and rendered 2,885 host preview frames. After a 10-second warmup, it measured a steady phase and a live-edit phase; the latter committed 55 renderer changes while periodically navigating all four pages. There were no worker/configuration errors, and shutdown joined the worker successfully.

| Measurement | Steady phase | Repeated live edits |
| --- | --- | --- |
| Mean process CPU, percent of one core | 11.43% | 11.53% |
| RSS range | 109.11–112.16 MiB | 109.69–112.86 MiB |
| Initial/final RSS medians | 111.33 / 111.50 MiB | 112.34 / 112.14 MiB |
| Fitted RSS slope | +0.67 MiB/min | −0.002 MiB/min |
| Open descriptors | 12 throughout | 12 throughout |
| OS threads | 9 throughout | 9 throughout |

CPU includes the worker, QML, and measurement process threads; 100% means one fully occupied core, not the whole machine. RSS includes native Qt/Pillow/font allocations as well as Python objects. Short-term RSS fluctuations and a fitted slope do not identify or exclude a leak. The initial steady phase has a positive fitted slope even though its endpoint medians differ by only 0.17 MiB; longer measurements are necessary before drawing conclusions. These figures are host-specific and do not predict native GPU/compositor or real USB behavior.

## Repeatable longer run

From the repository root, with desktop dependencies installed:

```bash
PYTHONPATH=src .venv/bin/python tools/profile_desktop.py \
  --duration 3600 --warmup 60 --output /tmp/fx240-desktop-profile.json
```

The tool never opens USB. It samples RSS, process CPU, descriptors, threads, frame count, and renderer revisions once per second. It navigates pages and exercises live settings in the second half. JSON contains full samples and phase summaries. This is a profiling tool, not a pass/fail leak detector. A multi-hour native-window run with actual sysfs telemetry and physical USB output, repeated start/stop, different fonts, and suspend/resume remains future validation. Run the native application separately for those observations; do not mistake this offscreen command for a physical LCD trial.

## Native USB and optical extension

The [2026-11-01 extended report](benchmarks/2026-11-01/README.md) supersedes the initial two-minute synthetic run as the most substantial resource measurement. It documents ten minutes of native Wayland/real-sensor/USB activity, the queue-polling preview bottleneck, isolated 60/90 FPS instruments, an instrument shutdown failure and correction, and three private optical recordings summarized numerically. It does not claim physical maximum FPS or exhaustive leak freedom.
