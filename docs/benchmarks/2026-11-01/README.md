# Extended performance and optical trials — 2026-11-01

These are development measurements on one FX240 and one Linux/Wayland desktop. They do not establish a universal hardware maximum or production stability. The application remains capped at 24 FPS; higher rates were isolated benchmark settings and were never saved as user preferences. No GitHub publication or first commit was performed by these trials.

## Conclusions for the initial experimental repository

- Retain 24 FPS as the conservative application default. The Gray trial recovered every transmitted ID in its 24 FPS phase using inverse validation and at least two samples per state.
- 30 FPS is the next practical candidate to integrate and validate in the application: 300/300 IDs were observed in order, with 294/300 supported by at least two samples under permissive decoding. It is not yet an application preset.
- Do not advertise 60 or 90 physical, complete, tear-free FPS. Host transmission and Qt update throughput reach these rates, but the optical evidence contains mixed transitions and incomplete state observability.
- The current 33 ms preview queue poll imposes a roughly 31 FPS bottleneck if higher production rates are introduced. A separate benchmark using 4 ms polling removed this bottleneck. The production polling/default/cap were not silently changed.
- The 10-minute real-USB run showed sustained host throughput with no reported transmission/configuration errors and no runaway RSS increase. This does not exclude a slow leak, driver failure, or behavior on other hardware.

## What each metric means

**Host FPS** counts completed render/encode/write/decode work, not LCD presentation. The stream instrument includes preview JPEG decode in its full-loop timings. The session's own `pipeline_ms` ends before preview JPEG decoding; its statistics must not be directly equated to full-loop latency.

**Qt swaps** refer to buffer swaps in the native QML window. The initial instrument sampled an applied-ID tag at render synchronization using direct Python callbacks. It later hung during one 90 FPS shutdown; that attempt is failed. The corrected instrument queues `frameSwapped` callbacks to the GUI thread and associates the latest applied source ID at callback delivery. This association is a proxy, not an exact GPU texture presentation ID or proof of physical monitor refresh. Extra repaints and callback scheduling are material limitations.

**Optical states** are IDs read from a small diagnostic region in camera frames. A readable code does not prove that all LCD pixels simultaneously displayed a complete source frame. Camera exposure, rolling shutter, LCD response, JPEG artifacts, fixed-crop alignment, and state blending can affect decoding. Unobserved IDs do not alone prove LCD drops.

## Host and native Qt measurements

All profiles used JPEG quality 65, rotation 180, and the verified Hidraw transport. Focus typically used 7–8 reports/frame; the optical Gray pattern used about 11. These results are content-specific: a complex GIF can produce larger JPEGs and lower throughput. No new prolonged GIF run was performed. The initial Focus stream sweep tested 24, 30, 40, 48, and 60 FPS with report delays of 2, 1, and 0.5 ms. These eight-second runs are screening measurements, not endurance validation.

| Test | Generated/sent | Preview result | Qualification |
| --- | ---: | --- | --- |
| Stream, 48 FPS / 2 ms | 384 / about 8 s | Not measured | About 48 host FPS; one full-loop over-budget frame |
| Stream, 60 FPS / 2 ms | 429 / about 8 s | Not measured | About 53.54 host FPS; target not sustained |
| Stream, 60 FPS / 1 ms | 480 / about 8 s | Not measured | About 60 host FPS; no full-loop overruns |
| Native 60 FPS / 1 ms, 33 ms poll | 1,192 / about 19.94 s | 620 unique swap-associated IDs, about 31.26/s | Queue polling bottleneck; 52.01% coverage |
| Native 60 FPS / 1 ms, 4 ms poll | 1,774 / about 29.64 s | 1,774 unique swap-associated IDs, about 60.02/s | Short trial using the original direct instrumentation |
| Native 90 FPS / 0.5 ms, direct instrumentation | No complete result | Window stopped responding during shutdown | **Failed**, forcibly terminated; not evidence of stability |
| Native 90 FPS / 0.5 ms, queued/precise instrumentation | 2,695 / about 30.06 s | 2,695 swap-associated IDs, about 90.01/s | Closed normally, no output/configuration error; presentation association remains a proxy |

The native screen reported about 144 Hz. The 90 FPS queued trial had worker pipeline p99 about 9.3 ms, maximum about 19.34 ms, and mean process CPU about 39.2% of one core. This is not hard real-time operation: the maximum exceeds its nominal 11.11 ms frame budget.

See [host sweep](host-sweep.json), [33 ms preview](preview-poll33.json), [4 ms preview](preview-poll4.json), [failed 90 FPS attempt](failed-90-direct-instrument.json), and [corrected 90 FPS attempt](preview-90-queued-precise.json).

## Ten-minute native USB run

At target 60 FPS, quality 65, 1 ms report delay, and 4 ms queue polling:

- 35,981 generated, sent, and GUI-applied frames; approximately 59.997 host FPS.
- No reported output or live-configuration errors; the worker stopped normally.
- Live weight, color, and comet-style changes were applied through the actual QML controls every ten seconds.
- RSS range: 270.25–274.17 MiB. Median RSS from seconds 30–90 was 272.74 MiB; the last-minute median was 272.83 MiB. Fitted post-warmup slope was about +0.058 MiB/min, not proof of a leak or leak freedom.
- Mean process CPU: about 27.49% of one core. File descriptors stayed at 28 and OS thread count at 25.
- Qt recorded 31,001 distinct swap-associated IDs, 86.16% of all generated IDs. Swaps ceased in the final segment while USB continued. The user confirmed that the monitor powered off or the screen locked. The active swap interval rate was about 59.997/s; it must not be presented as uninterrupted ten-minute preview presentation.

Part of this run overlapped single-thread local optical video decoding. The machine was not exclusively reserved for the benchmark. Native and old offscreen software-rendered RSS numbers are different workloads and are not directly comparable. Per-frame timing is streamed to disk and in-run resource storage is bounded; summary loading happens after the measured run.

See [soak record with context](soak-60-10min.json). The original run did not record window exposure/visibility flags; those fields were added for subsequent runs rather than inferred retroactively.

## Optical evidence

Three private camera videos were analyzed. The user selected 240 FPS capture. Files contain about 29.985 FPS playback metadata, consistent with slow-motion storage. Capture FPS and independent exposures were not independently established. All optical rates below are conditional on that declared capture rate. No exact duplicate normalized images were found; this does not prove independent camera exposures or exclude interpolation.

The first binary/folded-check trial was inconclusive at 60 FPS because of mixed states, weak check-bit protection, and confidence sensitivity. It was followed by Gray/inverse trials: only one Gray bit changes per consecutive source ID, and the second row must be the inverse of the first. Sample thresholds and multiple-sample support are retained in each JSON summary instead of selecting a favorable confidence level.

| Gray target | IDs sent | IDs observed with inverse check, at least one sample, permissive threshold | IDs supported by at least two samples, permissive threshold |
| --- | ---: | ---: | ---: |
| 24 FPS | 240 | 240 | 240 |
| 30 FPS | 300 | 300 | 294 |
| 40 FPS | 400 | 382 | 361 |
| 48 FPS | 480 | 440 | 411 |
| 60 FPS | 600 | 533 | 492 |
| 90 FPS | 900 | 542 | 433 |

Observed IDs were chronological in these Gray phases. Permissive one-sample state rates were about 24.02, 30.06, 38.21, 44.01, 53.32, and 54.20 states/s respectively. These are **code-observability measurements**, not certified complete-frame or panel-refresh FPS. Stricter contrast-margin requirements reduce higher-rate coverage sharply; full sensitivity tables are included. The plateau around 53–54 observed states/s at 60/90 target does not establish an exact panel ceiling or identify the cause of blending.

See [binary summary](optical-binary-summary.json), [Gray high-rate summary](optical-gray-high-summary.json), [Gray intermediate summary](optical-gray-intermediate-summary.json), and corresponding [high-rate host log summary](optical-gray-host.json) / [intermediate host log summary](optical-intermediate-host.json). Public source files contain aggregate numeric summaries only. Videos, extracted camera images, per-frame private traces, and personal captures remain outside the repository.

## Reproduction

Install the desktop extra for native measurements and the optional analysis extra only if decoding a video:

```bash
python -m pip install '.[desktop]'
# Optional, analysis tools only; not required to run the application:
python -m pip install '.[analysis]'
```

Close other transmitters before a USB run. Each benchmark requires `--send` to open USB, verifies identity and exclusive locking through Hidraw, and attempts to leave the recreated standby frame on exit. The tools do not write application preferences. Use an external timeout when testing native Qt instruments so an instrumentation failure cannot leave an unbounded process:

```bash
PYTHONPATH=src .venv/bin/python tools/benchmark_stream.py \
  --send --seconds 8 --output /tmp/fx240-stream.json

timeout --signal=TERM --kill-after=3s 630s env PYTHONPATH=src \
  .venv/bin/python tools/benchmark_gui.py --send --experimental \
  --fps 60 --delay-ms 1 --poll-ms 4 --seconds 600 --exercise-options \
  --output /tmp/fx240-native.json
```

A forced timeout invalidates the run's successful-completion claim. If the display powers off or the window is hidden, interpret Qt swaps with recorded visibility/exposure context; do not stop counting transmitted frames as though rendering and USB were the same metric.

Optical recording uses an explicit experimental counter and its matching host result for exact phase/ID boundaries. Keep the camera steady, the whole code visible, and preserve the original file:

```bash
PYTHONPATH=src .venv/bin/python tools/benchmark_stream.py --send \
  --mode optical --pattern gray --seconds 10 --fps 30 40 48 --delays 1 \
  --output /tmp/fx240-optical-host.json

PYTHONPATH=src .venv/bin/python tools/analyze_counter_video.py /path/to/private-video.mp4 \
  --pattern gray --trial-json /tmp/fx240-optical-host.json \
  --crop X Y W H --capture-fps 240 --output /tmp/fx240-optical-analysis.json
```

Crop coordinates refer to the decoded image after rotation. A new recording requires its own calibration. The recorded regions for these trials were fixed crops; no claim of camera-motion-independent tracking is made.

## Remaining work before calling a release stable

One-hour/multi-hour resource runs, suspend/resume, cold boot, reconnection, clean-machine installation, more hardware/firmware, and GitHub CI remain separate validation gates. The original-code license and final publication audit also remain owner decisions. These results support an honestly documented experimental initial repository, not a blanket compatibility, maximum-FPS, or stability certification.
