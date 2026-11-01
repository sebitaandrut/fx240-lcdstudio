# Development notes and detailed observations

This document preserves the detailed implementation and trial notes previously in the main README. For current installation and project status, start with the [main README](../README.md), [build guide](building.md), and [roadmap](roadmap.md). Historical steps describe the stage at which they were recorded. The current original-code license is [GPLv3 or later](../LICENSE); older licensing-status statements below describe the earlier preparation stage.

Experimental native Linux client for the **ID-COOLING FX240 LCD**. This first modular version supports images, GIF playback, and a dashboard of CPU/GPU temperatures and frequencies exposed through sysfs. It does not control the pump, fans, or RGB. This is unofficial software with no affiliation with ID-COOLING.

**Status: 0.1.0, experimental; image/GIF output and the Focus/QML workflow have been tested on one FX240. Cold-boot and reconnection tests remain pending.** The protocol comes from a local HID prototype that displayed images and animations in user-reported trials. Packet construction equivalence has been checked; this does not establish compatibility with other models, firmware versions, or interfaces sharing the same VID/PID.

## Validated platform

All hardware, desktop, performance, and optical trials recorded so far were performed on **Arch Linux only**. No other Linux distribution has been tested. General Linux requirements and bundled executables are not evidence of compatibility with other distributions; those remain unverified.

## Extended performance measurements

[Native USB, Qt preview, resource, and optical trial report](benchmarks/2026-11-01/README.md) records the development tests on one FX240. The host and an experimental Qt instrument reached 90 updates/s in short runs, but this is not evidence of 90 complete physical LCD frames/s. The Gray/inverse videos recovered all 24/30 target IDs under permissive decoding; higher rates had incomplete or mixed-state observability. A ten-minute 60 FPS host run sent 35,981 frames without reported output errors, with approximately 270–274 MiB RSS. The monitor powered off/locked in the final segment, so preview swaps were not uninterrupted for all ten minutes.

The application remains at its conservative 24 FPS default/cap. Higher rates, alternate queue polling, and optical patterns are isolated experimental instruments; 30 FPS is a practical next candidate rather than an enabled application preset. The report includes a failed instrument shutdown, its corrected queued-callback checks, camera/exposure limitations, aggregate evidence, and reproducible commands. Private videos and extracted images are not distributed.

## Build an executable locally

Follow the [build guide](building.md) for Arch Linux dependencies, a pinned isolated build environment, the one-file or directory build, and a safe packaged-runtime check. Users can generate their own executable without keeping a Python environment active at runtime. Only Arch Linux x86_64 has been checked; other distributions and clean-machine installation remain unverified.

## Quick start

Requirements: Linux, Python 3.11 or later, and Pillow. From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
fx240 sensors
fx240 dashboard --duration 2 --preview /tmp/fx240-preview.png
fx240 image /path/to/image.png --duration 2
fx240 gif /path/to/animation.gif --duration 10
```

To run directly from source with Pillow already installed:

```bash
PYTHONPATH=src python3 -m fx240 dashboard --duration 2
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

These commands only read sensors or simulate playback; they do not open the LCD. The PNG preview shows content before physical orientation compensation.

To transmit, identify the correct `/dev/hidrawN` interface and grant access through your local permissions configuration. The number may change after reconnecting. This project does not modify udev; simulated tests require no administrator privileges.

```bash
fx240 image /path/to/image.png --device /dev/hidrawN --duration 2 --send
fx240 gif /path/to/animation.gif --device /dev/hidrawN --duration 10 --send
fx240 dashboard --device /dev/hidrawN --duration 10 --send
```

`--send` explicitly enables writes without a second confirmation prompt. The transport verifies USB bus and VID/PID `2000:3000`, rejects regular files and symbolic links, and obtains a cooperative lock. These checks do not distinguish all matching interfaces or block applications that ignore the lock. Select the node explicitly; no automatic device selection is performed.

## Desktop interface (PySide6 + QML)

```bash
python -m pip install '.[desktop]'
fx240 gui --fps 24 --quality 65 --delay-ms 2
```

The Studio window starts its live preview and automatically transmits when exactly one FX240 is discovered, or when `--device` specifies the device. With no device or ambiguous discovery, the preview remains available. **Stop display** sends a recreated standby frame and closes USB output while the preview continues. **Start display** resumes physical output. There are no preview start/stop controls. Font, weight, LCD accent, comet style/speed, decimal precision, FPS, quality, and delay edits apply live after a 200 ms debounce at a frame boundary, with no worker or USB restart. Only switching the device requires pausing output. Invalid renderer edits retain the last working configuration and show an error. Closing the window also attempts standby before releasing the device. On Linux/logind, a delay inhibitor coordinates standby before suspend; output resumes after wake only if previously enabled. See Diagnostics for suspend integration availability. Hardware errors are displayed without stopping the preview.

Studio uses Outfit and local Lucide SVGs, with their upstream licenses bundled. Display, Sensors, Diagnostics, and Settings are implemented; Media and Dual are omitted until available. Desktop temperatures default to one decimal. Appearance switches between Celsius and Fahrenheit live; the preview, LCD, and target table agree while raw sysfs samples and arc scaling remain Celsius. The standby artwork is generated in code from a visual reference: it is not the original vendor bitmap or a firmware reset. No personal photo is bundled. The user confirmed the recreated standby artwork looks good. Physical suspend/resume validation remains pending. See [desktop usage and verification](desktop.md) and [resource profiling with evidence limits](performance.md).

Studio uses the approved compact 1000×650 layout: a 300×300 preview in a 344 px wide card, approximately 22 px of horizontal clearance, compact CPU/GPU cards, and a persistent output bar. Appearance groups the palette, comet style/speed, temperature precision, and typeface summary. Transmission state appears once in the output bar; a separate line appears only for errors. Secondary pages scroll when needed without hiding output actions. The header offers Dark/Light application themes, including matching dropdowns and icon colors; changing the application theme leaves LCD colors unchanged. Minimizing hides the window in the system tray when a tray host is available, and Hide to tray does the same explicitly. The tray menu provides Show studio and Quit. Its original LCD icon (selected concept B) uses a rounded cooler outline with a circular display and adapts to the desktop color scheme independently of the application theme. Without a tray host, normal window minimization remains available. Closing the window or choosing Quit exits with the existing standby sequence; hiding does not stop LCD output. Language (Spanish/English), application theme, LCD accent/style/speed, font, units, and validated transmission settings are saved automatically in `$XDG_CONFIG_HOME/fx240-linux/settings.json` (default `~/.config/fx240-linux/settings.json`). Settings separates General from collapsed Advanced controls with brief hover/focus help. First launch uses Spanish and the Smooth desktop defaults. Explicit CLI flags override saved values; use `fx240 gui` to restore the complete saved configuration. Device paths are rediscovered; output state is not persisted. The physical LCD renderer is unchanged by this desktop layout refinement.

## Focus animated theme

Focus uses a large CPU temperature, a secondary CPU frequency, and compact GPU temperature/frequency readings. An accent-colored arc (mint by default) eases toward each new CPU reading over 600 ms. A white segment with a fading trail traverses the active arc every three seconds at 1×, without an endpoint pulse. Appearance includes a live Comet speed slider from 0.25× (12-second cycle) to 3× (one-second cycle). Changes preserve the current sweep position and do not alter FPS or USB timing. CLI Focus and GUI also accept `--comet-speed` (default 1). LCD accent offers six swatches and an in-window custom picker with saturation/value, hue, and validated hex input. The picker follows the application theme, applies changes live, and opens below Custom without a separate native window. The Accent comet has a white highlight over an accent-tinted tail; Rainbow uses a moving multicolor tail while retaining the selected accent for the base arc, CPU frequency, and degree symbol. Desktop navigation colors remain unchanged. CLI Focus and GUI also accept `--accent "#ac8aff" --comet-style rainbow`. The background track, active arc, and highlight share a 5 px stroke with round caps. The comet head is a circular cap on the same inward stroke centerline, and a shared rounded mask keeps it aligned with the temperature arc. CPU digits switch directly on the first frame using the new sample; there is no blend with the previous value. Values are actual sampled readings, not invented intermediate temperatures. GPU data is displayed on two lower rows for circular readability. Sensors refresh once per second independently of animation cadence. The time-based animation uses cached static artwork and fonts, drawing at 480×480 before downsampling to 240×240.

```bash
fx240 focus --duration 2 --preview /tmp/fx240-focus.png
fx240 focus --fps 24 --quality 65 --delay-ms 2 --temperature-decimals 1 --duration 10
```

The first command keeps the conservative transport defaults and uses 5 FPS. The second explicitly selects the new measured fast profile; add `--device /dev/hidrawN --send` for hardware output. No existing profile defaults are silently changed. Focus can display zero or one temperature decimal with `--temperature-decimals`. Decimal glyphs are fitted to the circular area. The default arc scale is 0–100 C and can be changed with `--arc-min` and `--arc-max`; this is a visual mapping, not a thermal safety threshold. Missing readings display N/A and remove the active arc. Selected `--metric` keys are matched by CPU/GPU group and temperature/frequency unit.

After physical viewing-distance feedback, the CPU digits were initially increased from 57 to 72 px and later reduced to a 64 px maximum after the user requested more breathing room, CPU frequency from 14 to 18 px, GPU temperature from 12 to 18 px, and GPU frequency from 10 to 14 px. Secondary text contrast was increased. These sizes refer to the native 240×240 design before supersampling.

The degree symbol is positioned from the measured number bounds with a 3 px gap and the combined number/unit group is centered. The degree symbol moves with the current number group. Variable fonts can be adjusted with `--font-weight 350` (100..900); static fonts retain their native weight. Supported optical-size axes follow the native text size within the font's bounds.

The selected default font is **Outfit at weight 350**. Its unmodified variable font is bundled with its copyright notice and SIL Open Font License 1.1 in `src/fx240/assets/fonts/`. No global font installation is needed. `--font /path/to/font.ttf` remains available for alternatives. If the bundled asset is unavailable, the renderer falls back to an installed Noto Sans Regular and then Pillow's default; an invalid explicit font path is an error. Earlier Manrope trials are retained in the evidence records.

Three physical trials at 10, 20, and 24 FPS, each eight seconds with quality 65 and a 2 ms inter-report delay, completed 80, 160, and 192 frames. All had zero frame budget overruns and no incomplete writes. At 24 FPS the pipeline p95 was 14.97 ms, below the 41.67 ms frame budget, with mean transmission 10.89 ms. These are host measurements; optical confirmation is recorded separately in [Focus trial results](focus-trials.json). The remembered Cyberpunk trial suggested investigating shorter pauses, but its exact best historical settings were not recovered.

## Telemetry over images and GIFs

```bash
fx240 image /path/to/image.png --overlay --duration 2
fx240 gif /path/to/animation.gif --overlay --fps 5 --duration 10
```

Add `--device /dev/hidrawN --send` only after identifying the correct interface. Use repeated `--metric` options to select up to four readings. A ten-second physical test of the synthetic GIF with live telemetry completed 50 frames at 5 FPS without incomplete writes or frame budget overruns; the user confirmed animation, updating readings, and complete visibility. Image overlay composition is covered by software tests; no separate physical image-overlay trial has been recorded. The overlay is optional and only valid for image/GIF modes; it preserves frame selection and timing. Missing selected sensors display N/A, and each new sensor snapshot replaces the old one. Arbitrary backgrounds may have important content covered by the bands; a dedicated circular layout or crop control is not yet provided. Higher JPEG complexity can increase transmission time, so start at 5 FPS with the existing 10 ms inter-report delay.

Original synthetic demonstration assets can be generated with:

```bash
python3 examples/generate_overlay_demo.py /tmp/fx240-overlay
fx240 gif /tmp/fx240-overlay/overlay-motion.gif --overlay --fps 5 --duration 10
```

## Features and limitations

- Images and GIF: transparency composed over black, aspect ratio preserved, and content centered on a 240×240 canvas. The default 180-degree orientation compensation is configurable with `--rotation`.
- JPEG quality 85, subsampling 0, and a 10 ms delay between reports. `--quality` and `--delay-ms` allow explicit experiments. No delay is added after the final report.
- GIF: original frame durations capped at 24 frames/s; `--fps 24` overrides them with a fixed cadence. Playback repeats for `--duration`, ignoring the file's loop count. Up to 1000 frames are preloaded; large files may consume substantial memory.
- Telemetry: temperatures from `coretemp`, `k10temp`, `zenpower`, `amdgpu`, `radeon`, and `nouveau`; hwmon frequencies where exposed by the driver; and CPUFreq `scaling_cur_freq`. There is no proprietary NVIDIA/NVML provider yet, or guaranteed support for every Intel GPU. Missing, unreadable, or faulted sensors display `N/A`, never a substituted zero.
- The dashboard places all text within a conservative 104-pixel-radius circular area, centered on the 240×240 canvas, with measured text fitting and black outer corners. It displays up to four readings. `fx240 sensors` lists keys, labels, units, and sources. Select readings with `--metric hwmon0/temp1 --metric cpu/policy0`. Hwmon indices may change after reboot; verify labels again. Default selection chooses one temperature and one frequency for each of CPU and GPU where available; these are not system-wide averages.
- Dashboard sensors update once per second. Images and GIFs support `--overlay` to compose CPU/GPU readings over the media. Sensor snapshots refresh once per second independently of GIF cadence. Semi-transparent dark bands improve contrast; the center remains available for animation. Overlay text stays within the circular inset; outer corners are black. Overlays use compact CPU/GPU labels and units; use `sensors` and `--metric` to inspect and choose the full sensor identities.
- Playback uses a monotonic clock and does not queue every overdue frame for catch-up. GIF frames are selected by elapsed time, so states may be skipped under load. The schedule is rebased when transmission exceeds its budget. The final transmission may finish after the requested duration; blocking writes depend on the driver and have no application-level timeout.
- Final diagnostics summarize JPEG size, report count, transmission time, `os.write` duration, scheduling lateness, and budget overrun with p50/p90/p95/p99 percentiles. Simulation does not model USB latency: zero transmission time and absent write samples are not hardware measurements.

CPUFreq readings may reflect a driver-requested state rather than instantaneous effective clock measurements. Temperature labels such as Tctl, Tdie, edge, and junction are preserved and are not interchangeable. The basic sysfs reader does not apply libsensors configuration corrections. References: [HIDRAW](https://docs.kernel.org/hid/hidraw.html), [hwmon](https://docs.kernel.org/hwmon/sysfs-interface.html), [CPUFreq](https://docs.kernel.org/admin-guide/pm/cpufreq.html).

## Reverse engineering and evidence

This project continues exclusively from the HID scripts in `fx240-controlcenter`. The abandoned AIO Control Center project is outside its scope; its code, interface, and tests are not used. The encoder, transmitter, GIF player, FPS tests, and inspection scripts were reviewed. [Provenance](provenance.json) records their SHA-256 hashes; originals are not distributed here. The recovered messages do not provide a complete historical account of every protocol deduction, so no missing steps or firmware conclusions are invented.

The current verifiable path is: inspect prototype framing → compare with a local USB capture → separate JPEG, DRA header, and padding → preserve the hidraw write convention → compare 240 frames and run simulated transport tests. [Protocol notes](protocol.md) document bytes, assumptions, and open questions.

| Evidence | Result | Scope |
|---|---|---|
| User trial at 20 FPS | 200 sent / 9.983 s = 20.03 FPS; perceived smoothness | Host rate reported in conversation; no raw log attached |
| User trial at 24 FPS | 240 sent / 9.991 s = 24.02 FPS; perceived smoothness | Does not certify physical refresh rate or absence of tearing |
| GIF prototype | Code uses quality 65 and 7 ms delay | Separate configuration; do not combine with the quality-85, 10 ms trial |
| 60 FPS visual test | Code uses quality 65 and 0.5 ms delay | Experimental target, not a physical guarantee or the new default profile |
| Local USB capture reviewed here | DRA header and 240×240 JPEG; payload lengths 1024/1024/1023 bytes | Length and JPEG discrepancies against the local file; not proof of full equivalence |
| New implementation vs. prototype | All 240 frames produce identical packets; encoder matches on a square test image | Local software verification without LCD transmission |
| This version's test suite | 86 passing tests with desktop dependencies | Protocol, simulated transport, images/GIF, simulated sensors, scheduling, and CLI |

The reviewed capture contains 3071 payload bytes and declares a 2532-byte message; its final payload is short. The JPEG segment selected by the declared length neither ends exactly at EOI nor matches the local JPEG. No cause is assigned to firmware, prefix handling, capture, or script without a new controlled comparison. The [historical verification record](verification.json) retains those original discrepancies. A [new controlled trial](usb-trial-verification.json) matched all 24 current reports exactly. Comparing the old capture with the saved local report buffer is consistent with one missing byte at offset 2048, at the third report boundary; this does not establish the original sender input or cause. These records contain numeric results and hashes only, with no capture or image.

### Video analysis: explicit evidence limits

An earlier analysis reviewed 28 frames of the a private optical recording, using zero-based indices: ranges 676–686, 708–715, and 800–808. It reported overlapping digits without a sufficiently clear spatial boundary to establish tearing. Values 11, 19, and 42 were not distinguishable as separate complete states; **this does not prove the device omitted or failed to receive them**.

The earlier estimate of 52–54 readable states/s assumed capture at 240 FPS and playback at about 29.985 FPS. Metadata and readable states do not establish independent exposures or an exact physical refresh rate. Exposure time, rolling shutter, camera processing, and LCD response can blend states. The evidence cannot attribute ghosting solely to the panel, establish 60 physical FPS, or set a physical ceiling of 53 FPS.

This work recovered the previous report; **it did not reprocess the original video**. No video frames, crops, or footage are included. See the [validation plan](validation.md).

## Architecture

```text
media (image/GIF) ────┐
                     ├─ player → JPEG → protocol → transport → hidraw
telemetry → dashboard ┘
```

The desktop `gui` bridge connects QML to a worker `session`, which shares one sensor snapshot between Focus and diagnostics and previews the same encoded JPEG used by output. CLI playback remains available independently. `protocol` performs no device I/O. `transport` verifies identity, writes complete reports, and closes the descriptor on errors; partial writes are not retried because retries could create another malformed report. `telemetry` only reads sensors, `dashboard` composes standalone panels, `overlay` combines media with cached telemetry, `player` schedules and measures playback, and `cli` selects the execution mode. Tests use the standard library; imaging uses Pillow.

## Repository conventions

All repository content is maintained in English: README, documentation, comments, identifiers, CLI messages, tests, commit messages, pull request titles/descriptions, and release notes. Sensor labels supplied by drivers retain their original meaning. Conversation with the maintainer may remain in Spanish.

The [development and commit workflow](../CONTRIBUTING.md) defines English commit messages, coherent change boundaries, appropriate checks, documentation updates, and staged-file review. The first commit should honestly snapshot the implementation developed so far; historical trials are evidence records, not reconstructed Git commits.

## GitHub preparation

This is an independent local Git repository with no remote or publication. It contains no USB captures, personal GIFs, videos, user images, or copies of the abandoned project. Ignore patterns help exclude files but do not replace privacy review: inspect `git status`, diffs, and the complete file list before adding content.

CI workflows for Python 3.11/3.13 core tests and an optional desktop/QML test job are included but have not run on GitHub. No license has been selected for the original application code; the bundled Outfit font retains its own OFL license, and the Lucide SVG assets retain their upstream ISC/MIT notices. Ownership and application licensing should be decided before presenting the project as open source or redistributing it. This revision prepares the technical structure; publication, licensing, and evidence media remain the owner's decisions.

## Initial hardware trials

The modular client transmitted a synthetic pattern successfully; the user confirmed correct orientation and colors. A ten-second CPU/GPU dashboard trial completed 10 frames without incomplete writes or frame budget overruns; the user confirmed readable, updating values but reported clipping on the circular display. The corrected circular dashboard was then tested for ten seconds; the user confirmed the title and all four readings are fully visible. These visual trials do not establish physical refresh rate. A subsequent controlled USB capture matched all 24 expected 1024-byte reports exactly, with 24 successful output completions; the historical short payload did not recur. Its original cause remains unknown. A ten-second synthetic GIF trial at an explicit 5 FPS also completed 50 frames without incomplete writes or frame budget overruns; the user confirmed counter changes and marker movement. The user also confirmed agreement of all four QML LCD targets with the physical display, accepted the smaller CPU readout, and selected Outfit after a physical readability trial. See [hardware trial results](hardware-trials.md), [QML comparison](desktop-trial.json), [spacing approval](focus-spacing-trial.json), and [Outfit approval](outfit-trial.json).

## Next validation steps

1. Extend the successful 24-report USB comparison to other content and timing profiles. The historical short payload did not recur; its original cause remains undetermined.
2. Extend animation trials to additional content and timing profiles, changing one parameter at a time. Initial synthetic image, circular dashboard, and fixed-rate 5 FPS GIF trials are complete.
3. Test cold boot and reconnection: whether prior initialization by the official software is required remains unknown.
4. Measure optical behavior with an independent timing reference and controlled exposure before changing FPS limits or claiming tearing.
5. Add Dual, desktop image/GIF controls, NVML, persistent sensor selection, and an optional service. Physical QML output and agreement of all four LCD targets have been confirmed; the accepted design uses bundled Outfit 350, a 64 px CPU numeral maximum, one decimal, and a 5 px aligned arc/highlight. Image/GIF telemetry overlays remain available in the CLI.
