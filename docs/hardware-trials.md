# Hardware trials

## Initial modular client trials — October 28, 2026

USB identity was verified as bus 3, VID 0x2000, PID 0x3000 before writing. The device path was selected explicitly. No serial numbers, personal media, screenshots, or raw USB captures are included.

Both trials used JPEG quality 85, subsampling 0, 180-degree rotation, 1024-byte payloads with the hidraw 0x00 prefix, and a 10 ms pause between reports.

| Trial | Host result | Visual evidence |
|---|---|---|
| Synthetic pattern, 2 s, 1 FPS | 2 completed frames; 12 reports/frame; 112–113 ms transmission/frame; no incomplete writes | User confirmed correct orientation and red/green/blue blocks |
| CPU/GPU dashboard, 10 s, 1 FPS | 10 completed frames; 8 reports/frame; mean transmission 71.25 ms, maximum 71.58 ms; no frame budget overruns or incomplete writes | User confirmed readings updated correctly, but reported clipping at the circular display edges |

The dashboard reads current sensor data once per second. Successful writes establish host-side transmission, not physical refresh timing or proof of every optical state. No new USB capture was collected, so the historical short-payload discrepancy remains unresolved. The user confirmed GIF counter changes and marker movement. Cold-start behavior remains to be tested.

## Reproduce the synthetic pattern

From the repository root, with Pillow installed:

```bash
python3 examples/generate_test_media.py /tmp/fx240-test
PYTHONPATH=src python3 -m fx240 image /tmp/fx240-test/test-pattern.png --duration 2 --fps 1
```

After identifying the correct HID interface, add `--device /dev/hidrawN --send` for the physical trial. The generated pattern should have TOP / UP at the top, LEFT and RIGHT labels, and red, green, and blue blocks. The generator also produces an original 20-frame GIF with a counter and moving marker for the next playback trial. Generated files are excluded from this source distribution.

## Circular dashboard correction

The first dashboard used a rectangular text layout. Physical observation revealed that the round LCD hides its corners. The corrected renderer centers text within a conservative 104-pixel-radius inset and fits labels using measured text bounds. Missing values remain N/A. The 240×240 JPEG framing and HID protocol are unchanged. Two regression tests check text bounds, including long labels and missing sensors, and black square corners; the complete suite now has 21 passing tests. The ten-second physical retry completed 10 frames at 12 reports/frame, with mean transmission 112.10 ms, maximum 112.79 ms, no incomplete writes, and no frame budget overruns. The user confirmed that the title and all four readings are fully visible on the circular display.

## Synthetic GIF transmission

A ten-second trial at an explicit 5 FPS completed 50 frames with 11–12 reports/frame, mean transmission 110.05 ms, maximum 112.95 ms, no incomplete writes, and no frame budget overruns. Settings remained quality 85, subsampling 0, rotation 180 degrees, and a 10 ms inter-report delay. The generated rectangular diagnostic pattern was used to test counter changes and marker movement, not circular layout. The user confirmed that both the counter and marker animated correctly. This does not establish higher-rate capability, native GIF timing, or physical refresh rate.

## Controlled USB capture comparison

On October 28, 2026, the current sender transmitted the known synthetic image twice at 1 FPS while usbmon recorded the selected bus. The target USB bus/address and VID/PID were checked immediately before capture. The comparison found exactly 24 output submissions, all 1024 bytes, identical byte for byte to the expected reports. No packet truncation was reported. There were 24 output completions with status 0. See `usb-trial-verification.json` for the sanitized result and capture SHA-256. No raw capture is distributed.

This confirms that, in this trial, the userspace writes of 1025 bytes (0x00 prefix plus 1024-byte report) produced the expected 1024-byte USB payloads, including each frame's final report. The historical 1023-byte final payload did not recur.

A separate comparison of the historical capture against the saved local `reports.bin` found 3071 versus 3072 bytes. The captured concatenation exactly matches that saved buffer after removal of the byte at offset 2048, the start of the third report. This is a precise correspondence against the saved buffer, not proof of the original sender's input or an established cause. No contemporaneous sender log identifies why the byte was absent. The historical record is retained rather than silently corrected.

The current exact match does not certify other content, timing profiles, cold-start behavior, or physical refresh rate. Temporary usbmon access can be removed after capture; loading usbmon did not change the LCD protocol.

## GIF with telemetry overlay

A ten-second run of the original centered-motion demo with live CPU/GPU telemetry and an explicit 5 FPS completed 50 frames. Each frame used 10 reports; mean transmission was 91.60 ms and maximum 92.37 ms. No incomplete writes or frame budget overruns were reported. JPEG quality 85, subsampling 0, rotation 180, and the 10 ms inter-report delay were preserved. The user confirmed simultaneous animation, all four CPU/GPU readings updating, and a fully visible circular layout. No new USB capture was collected for this content.

## Focus theme and shorter inter-report delay

The user recalled reducing pauses to approximately 2 ms during the earlier Cyberpunk GIF trials. The recovered conversation does not include those settings/results. The saved GIF player uses quality 65 and a 7 ms default; a separate visual test uses a 0.5 ms default. These are code settings, not evidence of the best Cyberpunk result. The local 498×498, 40-frame animation was not redistributed or assumed to be the confirmed Cyberpunk reference.

The Focus implementation was therefore tested as a new profile with quality 65, subsampling 0, rotation 180 degrees, and an explicit 2 ms inter-report delay. Three eight-second runs completed 80 frames at target 10 FPS, 160 at target 20 FPS, and 192 at target 24 FPS. Mean transmission was approximately 10.9 ms/frame. The 24 FPS pipeline p95 was 14.97 ms; all trials recorded zero budget overruns and no incomplete writes. Measured host FPS includes HID open/close overhead; actual start intervals are recorded separately. See `focus-trials.json`.

The user confirmed complete visibility but reported that the font is too small or thin to read comfortably without moving closer. A physical reference photo was offered; legibility refinement and a separate smoothness assessment remain pending. No new USB capture or optical timing measurement was performed for Focus. The earlier quality-85, 10 ms captured profile remains unchanged. Cold boot/reconnection testing was explicitly deferred by the user.

## Focus legibility revision

A private user photograph showed the display at the normal viewing distance. The main value was distinguishable, but the small, light secondary readings had insufficient visual presence beside the illuminated physical ring. No photograph, crop, metadata, or personal identifying detail was copied into this repository.

The theme now discovers Noto Sans Regular instead of Light. CPU digits are 72 px (previously 57), CPU frequency 18 px (previously 14), GPU temperature 18 px (previously 12), and GPU frequency 14 px (previously 10), measured at native 240×240 design resolution. Secondary text is brighter and the circular text-bound tests still pass. The synthetic before/after preview uses invented values. The revised physical trial completed 240 frames at target 24 FPS, using quality 65 and a 2 ms delay. Mean transmission was 14.32 ms, full pipeline p95 was 19.25 ms, and maximum pipeline time was 33.14 ms, below the 41.67 ms frame budget. No incomplete writes or budget overruns were reported. The user confirmed substantially improved readability, but reported excessive spacing before the CPU degree symbol and requested a more delicate alternative font.

## Degree spacing and font candidates

CPU degree positioning now uses measured glyph bounds with a 3 px native gap and centers the number and unit as a group for one-, two-, and three-digit readings. Previous and current groups are drawn independently during crossfades. Two regression tests were added for adjacency across digit counts/negative values and variable-font axes; the complete suite has 36 passing tests.

Inter and Manrope variable fonts from the Google Fonts repository were downloaded into private scratch space for a synthetic 240×240 comparison at weight 350. They were not installed globally, added to the repository, or selected as the default. Candidate selection and physical validation remain pending. Noto Sans Regular remains the default; `--font` and `--font-weight` allow testing candidates without changing it.

Sources: [Inter](https://github.com/google/fonts/tree/main/ofl/inter), [Manrope](https://github.com/google/fonts/tree/main/ofl/manrope). The user's photograph remains excluded.

## Manrope weight 350 physical trial

At the user's request, Focus was rendered with the externally supplied Manrope variable font at weight 350, including measured 3 px degree spacing. The ten-second run completed 240 frames at target 24 FPS with quality 65, subsampling 0, rotation 180, and a 2 ms inter-report delay. Every frame used seven reports. Mean transmission was 13.00 ms, pipeline p95 was 17.13 ms, and maximum pipeline time was 28.83 ms. No incomplete writes or frame budget overruns were reported. User evaluation of readability, visual weight, and degree placement is pending. No raw capture or personal photo is included; the font remains outside the repository and is not yet the default.

## Moving arc highlight

After the user accepted Manrope but found the endpoint pulse too subtle, the pulse was replaced by a moving bright segment with a fading trail. The effect traverses the active temperature arc over a three-second cycle, clips to its start/end, and does not change its temperature-dependent length. It uses elapsed time independently of sensor updates; missing CPU data suppresses the active arc and highlight. The numeric readout remains unchanged by decorative movement.

The ten-second Manrope-350 trial at target 24 FPS completed 240 frames with quality 65 and a 2 ms delay, zero incomplete writes, and zero frame budget overruns. Mean transmission was 13.07 ms; pipeline p95 was 18.58 ms and maximum 27.84 ms. Visual evaluation is pending. A subsequent numerical epsilon guard suppresses effectively zero-length highlight segments at clipping boundaries; the code is covered by 38 passing tests. No physical refresh rate or tearing conclusion is derived from these host timings.

## Highlight alignment and visibility correction

The user reported subtle movement and an apparent offset below the main arc. The previous strokes were 3 px for the arc and 4 px for the highlight, which can produce an inward offset because the strokes share the outer bounds. Both now use the same 3 px geometry. Highlight compositing is clipped with the exact active-arc mask so no highlight pixels can lie outside the temperature stroke. A darker green base, longer fading tail, and white leading segment increase contrast without enlarging the stroke.

The revised ten-second Manrope-350 trial completed 240 frames at target 24 FPS, quality 65, and a 2 ms delay. Mean transmission was 12.93 ms; pipeline p95 was 18.60 ms and maximum 28.27 ms. No incomplete writes or budget overruns were reported. Visual confirmation of alignment and visibility is pending.

## Thicker shared arc stroke

The user accepted the corrected highlight alignment and visibility, then requested thicker lines. The background track, active temperature arc, and moving highlight now all use a shared 5 px stroke instead of 3 px. The exact clipping mask is preserved. The ten-second Manrope-350 trial completed 240 frames at target 24 FPS with quality 65 and a 2 ms pause. Mean transmission was 12.93 ms; pipeline p95 was 18.34 ms and maximum 28.32 ms. No incomplete writes or frame budget overruns occurred. All 39 tests pass. Physical preference for the new thickness is pending user confirmation.

## Output through the QML desktop controller

The native trial used the same QML Bridge/Session path as Start LCD, with Manrope weight 350, one temperature decimal, target 24 FPS, quality 65, rotation 180, and a 2 ms inter-report pause. It completed 250 frames and 11 sensor snapshots, then stopped without a reported error. The final frame had eight reports, approximately 14.98 ms transmission, and 19.82 ms render/encode/transmission pipeline time. These are final-frame timings, not averages or percentiles.

The trial requested stopping after ten seconds using a Qt timer; actual duration was not recorded, so no exact rate is calculated from the 250-frame count. On stopping, the interface retains the final completed JPEG and corresponding snapshot for comparison with the physical LCD. User confirmation of value agreement and decimal legibility is pending. The sanitized trial record contains no actual sensor readings or personal image.

## Focus spacing after decimal validation

The user confirmed that the four values in LCD TARGET matched the physical LCD. They requested reducing the CPU temperature readout slightly rather than shrinking secondary readings or reorganizing the layout. The CPU numeral maximum is now 64 px instead of 72 px; the measured 3 px degree gap, Manrope weight 350, one decimal, other text sizes/positions, and 5 px arc are unchanged. Decimal strings can still shrink to fit their circular width constraint.

A controlled QML trial completed 235 frames without an error and reached Stopped. The final frame elapsed timestamp was 9.7695 seconds. The requested Qt stop timer was ten seconds and is approximate. Final-frame pipeline time was 19.43 ms and transmission 15.04 ms, with eight reports; these are not aggregate performance statistics. All 52 tests pass. The user accepted the reduced CPU size and requested keeping this layout. See `focus-spacing-trial.json`.

## Outfit font adoption

The user compared Outfit at weight 350 with the accepted Manrope layout, keeping the 64 px CPU maximum, one decimal, 5 px shared arc/highlight stroke, target 24 FPS, quality 65, and 2 ms inter-report delay. The QML trial completed 242 frames without a reported error; the last frame elapsed timestamp was 10.0611 seconds. Its pipeline time was 19.42 ms and transmission 15.05 ms with eight reports. These describe the last frame, not aggregate timing.

The user preferred Outfit and confirmed readability at their normal viewing distance. Outfit weight 350 is now the default. The unmodified font is packaged with its upstream copyright notice, OFL 1.1 license, source URL, and SHA-256 provenance. Other downloaded candidates and user photos remain excluded. See `outfit-trial.json`.

## Continuous preview and recreated standby trial

The user confirmed that stopping the earlier sender leaves the last telemetry frame on the LCD. The new controlled host trial ran at target 24 FPS, quality 65, rotation 180, and 2 ms report delay: 72 live frames were sent, output was disabled, and 48 further preview frames rendered without USB streaming. The worker reported no output or render error and sent the software-created standby image before releasing the device. This validates the host path, not optical appearance. User confirmation of the recreated standby image is pending. No original vendor bitmap or firmware reset command was recovered; no reference photograph is distributed. Real suspend/resume has not been tested.

The user confirmed that the recreated standby artwork looks very good. Subsequent reports of ghost-like CPU transitions correspond to a known 250 ms software digit crossfade. That transition has now been removed and checked with a pixel regression test. Physical evaluation of the direct digit update and live configuration remains pending; no new hardware or suspend trial was performed for this revision.
