# GIF buffering developer checks

Desktop long-GIF buffering is integrated automatically. These optional tools remain outside the installed application and compare the decoder with sequential Pillow composition. They never open USB, query sensors, or write application preferences. No test GIF or private raw report is stored in the repository.

## Reproduce offline checks

Run from the repository root with Pillow installed:

```bash
PYTHONPATH=src python experiments/gif_buffering.py generate /tmp/fx240-synthetic-360.gif --frames 360
PYTHONPATH=src python experiments/gif_buffering.py verify /tmp/fx240-synthetic-360.gif
PYTHONPATH=src python experiments/gif_buffering.py benchmark /tmp/fx240-synthetic-360.gif --mode eager --seconds 8
PYTHONPATH=src python experiments/gif_buffering.py benchmark /tmp/fx240-synthetic-360.gif --mode buffered --seconds 8 --buffer 12
```

Generation refuses to overwrite existing files. Verification compares complete loops, including transparency/disposal; the timed benchmark adds only a fixed overlay and JPEG encoding. Reports omit input paths and identifiers. Keep any private media and raw reports outside the checkout. The full regression suite separately covers session ownership, seek/rewind, renderer replacement, constructor failure, two assets, suspend/resume, metadata, and cleanup.

## Initial prototype results

One fresh process per mode/clip on Arch Linux; 240 × 240 synthetic GIFs, 8 seconds, 24 FPS host target, queue capacity 12:

| GIF frames | Eager peak RSS (MiB) | Buffered peak RSS (MiB) | Buffered render p95 (ms) |
| ---: | ---: | ---: | ---: |
| 120 | 55.44 | 32.92 | 1.602 |
| 360 | 110.54 | 35.20 | 1.589 |
| 720 | 193.78 | 38.29 | 1.517 |

Each clip matched the sequential reference across two complete loops. Those unpaced comparisons are separate from the eight-second runs, which did not span complete long-clip loops. Timed buffered runs recorded no underruns or render deadline misses. These minimal-renderer RSS values are not GUI application memory.

`runtime_smoke.py` exercises the actual backend renderer with synthetic telemetry and forbidden USB. Separate eight-second runs for Focus plus a 720-frame GIF and a scene with 720-/360-frame media layers observed 24 host FPS, p95 pipeline times of 7.971/6.572 ms, and peak RSS of 43.91/49.07 MiB, respectively. Neither included QML presentation or physical USB. No underruns or pipeline deadline misses were recorded in those runs.

For desktop/device observations, resource sampling, and measurement limits, see [performance](../docs/performance.md#long-gif-playback). Developer experiments and owner observations do not establish arbitrary-media performance, leak freedom, or optical FPS. Repeated lifecycle cycles and multi-hour runs remain pending.
