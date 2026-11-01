# Validation and further trials

## Software checks before hardware trials on October 28, 2026

- 19 local Python unit tests: header and known vector, report boundaries, JPEG markers, prefix and delays, partial writes without retries, identity and cleanup, invalid reports, orientation, transparency/aspect ratio, GIF timing, sysfs units/faults/missing values, overloaded scheduling, percentiles, and simulated CLI execution.
- External comparison against local scripts: identical packets for 240/240 frames from `animation_test.py`; identical encoder JPEG and reports for the square test image. Those source files and the image are excluded; script hashes are recorded in `provenance.json`.
- Offline inspection of a historical capture; partial result and discrepancies recorded in `verification.json`.

Live AMD CPU telemetry was read through k10temp/CPUFreq and AMD GPU telemetry through amdgpu. The dashboard preview was visually reviewed. Neither that preview nor its readings are stored in the repository. The CLI was run from source using `PYTHONPATH`; package installation and wheel building were not verified in this environment, which lacks setuptools.

At that stage, no new hardware transmissions had been performed and the modular version had not been physically validated. Subsequent physical trials are recorded separately in [hardware trials](hardware-trials.md). Identity and transport tests use mocks rather than a real hardware descriptor. The GitHub Actions workflow is prepared but has not run.

## Repeating checks without hardware

```bash
python -m unittest discover -s tests -v
fx240 sensors
fx240 dashboard --duration 2 --preview /tmp/fx240-dashboard.png
```

To test GIF playback, generate two original solid-color frames with different durations. Check aspect ratio, transparency background, and frame order. Compare sensor units, labels, and sources against driver tools; an individual reading does not represent the entire CPU or GPU.

## New hardware trial

Start with synthetic images. Record model/firmware where available, kernel, selected HID interface, quality, rotation, subsampling, delay, target FPS, and JPEG size. Verify identity and the complete descriptor. Change one parameter at a time.

Capture only the target device during the trial. Compare each payload against generated reports and document requested lengths, captured lengths, and USB completion status. Investigate the historical 1023-byte final payload before claiming exact bus-level reproduction. A capture without enumeration does not establish device identity by itself.

Measure writes, full transmission, scheduling, and encoding; keep host results separate from optical observations. If reports and delays exceed the frame budget, reduce FPS or image complexity before increasing USB throughput. The current 24 FPS cap is a policy based on the earlier trial, not a discovered panel limit.

For video, place an independent timing reference in the same shot and establish exposure and capture cadence. Do not automatically equate container FPS with physical exposures. Identify each displayed image with a unique pattern and look for a reproducible spatial boundary between states. Separate temporal blending, panel response, and rolling shutter by varying exposure and orientation. An unreadable number does not establish USB loss.

Before sharing a log, capture, or crop, review personal data, other devices, usernames, paths, serial numbers, UUIDs, and metadata. Publication approval will apply to a concrete set of reviewable files.

## Circular layout regression checks

After the first physical dashboard trial revealed clipping at the circular display edges, two tests were added for text bounding boxes within the circular inset and black outer corners. All 21 tests pass locally. This geometric check does not substitute for physical confirmation of the panel's exact visible area.

## Preparing a new USB capture

`examples/compare_usb_capture.py` compares output submission payloads with the exact reports generated from a selected image, quality, rotation, and expected frame count. It reports count, length, content differences, and packet truncation without exporting payload bytes. Synthetic comparator checks cover exact matching, a short report, missing reports, and changed content; these are separate from the 21-test application suite. USB completion statuses are reported separately and are not treated as optical evidence.

The preparation initially required administrator authentication to enable usbmon and a temporary read ACL. The subsequent controlled capture is complete and matched 24 reports exactly; see [hardware trials](hardware-trials.md). Keep captures in a private directory outside the repository. Recheck bus number and device address after any reconnection before capture or comparison.

After collecting a full-length capture of an isolated two-frame image trial:

```bash
PYTHONPATH=src python3 examples/compare_usb_capture.py /path/to/private/trial.pcapng /tmp/fx240-test/test-pattern.png --address DEVICE_ADDRESS --frames 2
```

Replace DEVICE_ADDRESS with the current decimal USB address. The tool filters output endpoints for that address, but assumes the capture contains only the intended trial on its bus. It does not establish device identity from the address alone or infer device initialization requirements.

## Image/GIF overlay checks

Five additional tests cover one-second sensor sampling independently of frame cadence, replacement of removed readings, preservation of source frames and central animation, circular text bounds and N/A for a missing selection, GIF CLI timing/content integration, and rejection of overlay use outside media modes. The full application suite now contains 26 passing tests. The synthetic preview uses invented readings, not captured personal data. The transport, JPEG profile, and report framing are unchanged.

## Focus animation and performance checks

Eight tests cover time-based arc motion and one-second sampling, continuity at reading changes, missing readings, metric selection and GHz conversion, configurable/clamped arc scales, font fallback and invalid explicit paths, circular text bounds, and conservative CLI simulation defaults. The complete suite now has 34 passing tests. Rendering, encoding, full per-frame pipeline time, and actual frame spacing have been added to diagnostics so simulation cannot be confused with USB throughput.

The local preferred font is discovered at runtime, not copied into the distribution. Synthetic preview assets use invented readings. The three new hardware trial records contain host timing summaries only; they do not contain live sensor values or screenshots.

## Font comparison and degree spacing

The suite now contains 36 tests. Added checks verify a close, consistent degree gap across one-, two-, three-digit and negative numbers, combined-group centering, weight application and optical-size clamping for variable fonts, and invalid weight rejection. Static fonts retain their native weight. Font candidate previews use synthetic data; physical legibility is not inferred from the previews.

## Moving-highlight regression checks

Two tests verify that highlight segments stay within the active arc at different temperatures, repeat on a three-second cycle, and animate even with constant readings while leaving the numeric region unchanged. Floating-point slivers at clipping boundaries are omitted. The complete suite has 38 passing tests.

## Exact highlight alignment

An additional pixel containment test verifies that the moving highlight cannot paint outside the active temperature arc at multiple phases. The full suite now has 39 passing tests. This complements physical feedback on apparent alignment and contrast; the pixel test does not establish visibility from a particular viewing distance.

## Desktop and temperature precision checks

The complete suite now contains 51 tests with PySide6 Essentials installed. New checks cover integer/decimal formatting, raw-value preservation, single-snapshot consistency, preview without HID access, output descriptor cleanup, failures, stopping/restart prevention, sensor removal, exact USB identity discovery, invalid settings, and UI error propagation. A separate offscreen QML smoke test verifies loading, preview data, output-control bounds, and orderly stopping without hardware. Optional Qt tests are skipped when the desktop dependency is absent.

A wheel was built without fetching further dependencies, installed into the isolated project environment, and checked for its QML asset. The user confirmed the real desktop window opened. Physical sensor/Start LCD comparison through the UI remains pending; this is not substituted by the existing CLI hardware trials. See `desktop.md`.

## Desktop hardware output and final-frame consistency

The full suite now has 52 passing tests with Qt installed. An additional desktop check verifies that stopping preserves the last completed JPEG and its exact sensor snapshot, including raw value, rounded target, and sample sequence, rather than leaving the UI one queued frame behind.

A controlled native QML trial entered output through `Bridge.start` and the shared Session/Hidraw transport. It completed 250 frames, sampled sensors 11 times, and reached Stopped without an error. The requested Qt stop timer was ten seconds; elapsed duration was not recorded, so the frame count is not claimed to represent exactly ten seconds. Recorded pipeline/transmission times are for the final frame only. Visual comparison remains pending. See `desktop-trial.json`.

## Bundled Outfit default

A font-resolution/package regression check brings the suite to 53 tests with Qt installed. It verifies that the default resolves to the approved Outfit asset, the adjacent OFL license is present, and the default weight is 350. The font file is unmodified; the chosen weight is applied at runtime. The physical Outfit trial and user approval are recorded separately in `outfit-trial.json`.

## Studio navigation and SVG assets

The current suite has 54 tests with Qt installed. The added asset check validates the selected Lucide SVGs with Qt's SVG renderer and verifies original hashes and complete upstream notices. The headless QML smoke test traverses Display, Sensors, Diagnostics, and Settings, checks a rendered preview and globally accessible Stop, and stops cleanly without HID access. Studio was rendered with synthetic values for visual inspection and opened on the user's desktop in preview-only mode. No new LCD protocol claim is made by this UI-only revision.

## Compact Studio output controls

The current 54 tests pass after compact layout integration. The QML smoke test traverses all active pages, verifies that contextual Stop stays visible, and confirms that start/preview actions return only after the session stops. Layout-only examples used synthetic readings and a simulated transport; the production compact window starts in preview-only mode. HID framing, sensor sampling, and the accepted LCD theme are unchanged.

## Continuous preview and standby lifecycle

The current suite has 60 passing tests with Qt installed. New coverage separates preview from physical output, validates the actual generated standby reports and transport reopen, checks suspend-worker release/resume, and exercises output-open and standby-write errors. Desktop startup selects exactly one discovered device automatically; ambiguous discovery remains preview-only. QML no longer presents preview start/stop actions. The firmware standby command and original vendor image have not been recovered. The reference is recreated in code; no personal photograph is distributed. A real system suspend test has not been performed.

## Direct numeric updates and live configuration

All 64 tests pass. New regression coverage requires the first changed CPU number to match the unblended new-value render, live edits to retain the active HID connection, invalid fonts to preserve the last working renderer, coalescing to select the latest edit, and device changes to be rejected while output is active. The QML smoke test changes the actual weight control and verifies that its debounce updates the worker without restarting it. The initial 120-second synthetic resource run completed without worker errors; scope and numerical results are documented in [performance.md](performance.md). This is not exhaustive endurance testing or physical ghosting validation.

## Rounded arc and comet caps

All 65 tests pass. A new geometry check verifies circular cap diameter, centers on the actual inward Pillow stroke, and empty-span behavior. Highlight containment now uses the shared rounded active-arc mask. Multiple synthetic positions were rendered for visual inspection. User validation on the LCD remains pending.

## Comet speed control

All 67 tests pass. Speed scaling and continuity at a live edit are covered independently of frame rate. Invalid speed multipliers are rejected. The QML smoke test moves the actual slider and verifies worker settings; the active-output configuration test includes a speed change without reopening USB. A synthetic offscreen render confirms the Appearance control fits the compact card.

## Palette, rainbow, and consolidated output status

All 69 tests pass. Color syntax and comet styles are validated before applying settings. Rendering tests check numeric-value stability across styles and containment of the rainbow trail within the rounded arc. The same-worker live configuration test now includes violet accent and rainbow style with an active simulated device. The QML smoke test applies accent/style/precision through the real controls and verifies their settings, as well as the single output status and hidden error line when there is no error. An offscreen synthetic render was visually reviewed at 960×650. No new physical or long-duration performance result is claimed.

## Application themes, consistent popups, and tray lifecycle

All 71 tests pass. New Qt checks cover theme changes without session creation, dark/light navigation and real dropdown operation, keyboard selection, output-row center alignment, and SVG validity for both palettes. A simulated system tray host drives a real QML window and worker to check hide/restore, frame continuity, availability loss recovery, no-host fallback, and graceful Quit. Native tray behavior remains to be checked on the user's desktop. Synthetic dark/light popup and Settings renders were inspected; the application theme does not change the physical LCD theme. No new USB, optical, long-run resource, or suspend result is claimed.

## General/advanced settings, bilingual UI, units, and private preferences

All 79 tests pass. New checks cover Celsius-to-Fahrenheit conversion before rounding, unchanged original samples and Celsius arc progress, Fahrenheit layout bounds, explicit target units, validated atomic preference storage with private permissions, invalid/corrupt file recovery, missing font fallback, and save failure without replacing the previous file.

A Qt integration test changes actual UI controls, verifies live unit conversion with a retained worker, checks help visibility by keyboard focus, switches language without resetting selections, saves settings, and creates a new engine with restored values. Tray labels are verified in Spanish. A separate GUI check verifies localized save-error reporting while retaining valid settings. Synthetic Spanish/light renders of Display, General settings, and expanded Advanced settings were reviewed. Real-device unit evaluation and native-desktop persistence/tray checks remain pending.

## Embedded color picker

All 80 tests pass. The custom picker uses a QML item popup rather than a native window. The added integration test checks identical top-level window counts before/after opening, anchor placement, both application palettes, real hex keyboard entry, preservation of the last valid color on partial input, HSV controls, Escape/outside dismissal, and live delivery to the existing worker. Synthetic screenshots of both themes were reviewed. Existing preference persistence and transport behavior are unchanged.

## Preference recovery diagnosis and timing-type regression

All 82 tests pass. Valid decimal representations of FPS and delay now round-trip using declared field types rather than integer default-value types. Regression tests verify 24.0/2.0 and 17.5/2.5 restore without spurious warnings. Invalid fields retain per-field reasons and fallback values. Qt checks verify the aligned wordmark, an informational recovery banner separate from runtime errors, localized details in an in-window dialog, successful saving after recovery, and detailed save failures followed by retry. Synthetic screenshots contain only invented settings and temporary test paths.

## Extended native and optical trials, 2026-11-01

The current desktop test suite has 86 passing checks. Added checks cover diagnostic Gray/inverse source words, statistics, injectable benchmark renderers without HID access, experimental settings without changing the production rate limit, and clean high-rate instrument shutdown using GUI-thread queued callbacks. The native 90 FPS instrument initially hung on shutdown and required terminating only the owned benchmark process. This failed run is retained in the evidence; a queued-callback instrument and precise deadline timer subsequently completed the bounded native check.

See the [extended performance report](benchmarks/2026-11-01/README.md) for full measurements and limits: 35,981 frames sent in a roughly ten-minute 60 FPS host run, stable descriptor/thread counts, no runaway RSS trend observed, the monitor-off/lock context for missing final Qt swaps, and three optical videos analyzed using declared 240 FPS capture with confidence sensitivity. The code-observability results are not physical full-frame certification. Application FPS defaults/cap and preference validation remain unchanged. Raw videos and camera extracts remain private, outside this repository.
