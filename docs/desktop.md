# Qt Quick desktop interface

The desktop application is implemented from scratch with **PySide6 + QML**. It uses the existing FX240 protocol, Pillow Focus renderer, telemetry provider, and verified hidraw transport. No code, UI, or tests were imported from the abandoned AIO Control Center project. Tkinter and PyQt6 are not dependencies.

## Install and launch

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install '.[desktop]'
fx240 gui
```

Qt is optional; CLI image/GIF/Focus use does not require it. The desktop extra installs PySide6 Essentials, including Qt Quick/QML, in the selected Python environment. Normal platform libraries for Qt may still be required by the Linux distribution.

To use the tested fast profile with the bundled Outfit font:

```bash
fx240 gui --fps 24 --quality 65 --delay-ms 2
```

Outfit is bundled with its copyright notice and OFL license, and is used at weight 350 by default. No global font installation is performed. Alternative fonts remain selectable with the font picker or `--font`. The GUI first version supports **Focus only**; image/GIF modes and telemetry overlays remain available through the CLI. Dual, sensor-selection controls, named profiles, and packaging as a system application are future work.

## Application appearance and tray

The header theme selector switches between Dark and Light without changing LCD colors, restarting the worker, or opening USB. Dropdown panels, selected/hover rows, controls, labels, borders, and local SVG variants follow the application theme. Output status and actions share a vertical center in a 64 px bar with 12 px padding and 40 px buttons. All active dropdowns use the shared rounded popup, including the device and profile selectors in Settings.

When a system tray host is available, minimizing the window hides it to the tray. **Hide to tray** is also available in the header. Clicking the icon or choosing **Show studio** restores and activates the window. Hiding keeps the same worker and output state; preview/telemetry continue. **Quit** from the tray or closing the main window performs the existing orderly shutdown and standby attempt. Close is not redefined as hide. This does not install an autostart entry or background service.

Without a supported tray host, the header hide action is unavailable and the normal window minimization remains intact. Availability is rechecked before hiding and every two seconds. If the tray disappears while the window was hidden, the window is restored to avoid leaving an inaccessible process. Theme and other validated preferences are now restored from the private configuration file described below. The UI remains Qt Quick; Qt Widgets supplies only the system tray icon and its platform menu through the same PySide6 Essentials dependency.

## Language, settings groups, units, and persistence

The current desktop uses a 1000×650 logical-pixel window to fit translated labels. General settings includes interface language (English / Español), transmission preset, font file, and font weight. Advanced controls are collapsed initially and contain device selection, FPS, JPEG quality, and inter-report delay. Each setting has an information button with a wrapped tooltip after 400 ms of hover, also available by keyboard focus. The Sensors page retains its source labels/paths and live readings.

Language changes apply live to application labels, help, menus, status, and tray actions. English remains the source language for code, documentation, and commit messages; Spanish translations live in `i18n.py`. Linux sensor identities, source paths, timestamps, and underlying OS/driver error details are retained rather than rewritten. First launch defaults to Spanish; subsequent starts restore the chosen language. Platform-owned native dialogs may follow desktop/Qt translation availability.

Appearance includes a °C / °F selector. Fahrenheit is derived as `C * 9 / 5 + 32` from each original sample, before display rounding. The LCD, decoded preview, summary cards, Sensors targets, and diagnostic LCD target use the same selected unit with an explicit suffix. Raw diagnostic values remain Celsius; the decorative arc always uses the original Celsius reading and range. Unit changes go through the existing live worker configuration and do not reopen USB. Missing sensors remain N/A.

Desktop preferences are stored as version 1 JSON at `$XDG_CONFIG_HOME/fx240-linux/settings.json`, falling back to `~/.config/fx240-linux/settings.json`. Render preferences include FPS, quality, delay, rotation, font path/weight, accent, comet style/speed, decimal precision, and unit. Application preferences include language and dark/light appearance. The current device path and paused/sending state are deliberately excluded: device discovery and automatic startup remain unchanged. No sensor samples or raw source paths are stored. A selected local font path remains private in this local configuration file.

Writes are debounced by 600 ms, replace the file atomically, and use a private temporary file (0600). Confirmed render settings are saved; invalid live edits retain the last accepted configuration. Preference-write errors remain visible without stopping rendering. An unavailable saved font resets to bundled Outfit with a notice. Corrupt/unsupported data uses defaults, and invalid individual fields are ignored while keeping valid fields. Preferences are also flushed during orderly shutdown. Named profiles are not implemented.

Start with `fx240 gui` to restore all saved values. Explicit CLI arguments take priority over the corresponding saved fields, so repeating the old `--fps 24 --quality 65 --delay-ms 2` command overrides those three preferences. CLI Focus accepts `--temperature-unit F`; other CLI render modes retain their existing behavior. The standalone CLI defaults remain independent of desktop preferences.

## Controls

Opening the window starts the preview and physical transmission automatically when exactly one matching LCD is found, or uses the explicit `--device` path. Zero or multiple matches without an explicit path leave the preview active without USB output. Identity verification and exclusive locking still occur when the device opens. No automatic retry loop follows an output error.

- **Stop display** completes the current frame, sends the recreated standby image once, and releases the descriptor. Preview animation and sensor sampling continue.
- **Start display** applies the current settings and resumes USB output on the same preview worker.
- Font, font weight, unit, decimal precision, accent, comet style/speed, FPS, quality, and delay edits apply automatically after 200 ms, between complete frames. The preview worker and active USB connection remain open. Only a device change requires pausing physical output first. Invalid font/render edits keep the last working configuration and show an error.
- Closing the window waits for orderly worker shutdown, including a standby attempt if output is active.
- A logind `PrepareForSleep` listener and `sleep` delay inhibitor coordinate standby before suspension. The worker pauses while sleeping and resumes physical output after wake only if output was enabled before sleep. A manually paused LCD stays paused.

The software-created standby frame uses the slogan and rounded outline visible in the user's reference. It is an approximation drawn with the bundled font, not a recovered vendor image, firmware command, or exact pixel reproduction. The reference photograph is not included in the repository. The user confirmed that simply stopping the old sender retains the last telemetry frame, so an explicit final frame is needed.

Diagnostics reports whether suspend integration is available. Without logind or permission to inhibit, suspend handling is unavailable or best effort. The system can enforce its delay limit; a blocked driver write, unplugged device, forced process termination, or power loss can prevent the final frame. Standby failures are reported. The program never claims a successful hardware reset. Real suspend/resume validation remains pending. Preferences and automatic reconnection after USB errors are not implemented.

## Comparing temperature values

A single sensor snapshot feeds Focus and the diagnostic table. There is no independent UI sensor polling loop. Every frame event carries its snapshot, sequence number, and UTC sampling timestamp. While physical output is paused, preview readings continue updating and no longer describe the static standby image on the LCD.

- **RAW SAMPLE**: the selected provider reading formatted to three decimal places with its source unit. This is diagnostic display precision, not a claim about sensor accuracy or physical resolution. Temperatures already have their hwmon unit conversion applied.
- **LCD TARGET**: the same reading after Focus formatting, such as 45.125 C → 45.1°, or 3940 MHz → 3.94 GHz.
- **Preview**: the encoded JPEG itself, decoded and returned to upright orientation. In output mode, it is published only after that frame's writes complete. The physical panel may still have display latency.
- **Sensor/source**: the provider label and sysfs path, preserving distinctions such as Tctl, edge, and individual CPUFreq policies.

Sensors are sampled once per second; UI preview/animation cadence can be 24 FPS. A CPU reading may remain unchanged because it is stable, the sensor updates at its own cadence, or integer formatting hides small changes. A raw transition from 44.6 to 45.3 appears as 45 in integer mode. Enable one decimal to expose that difference. CPU digits switch directly to the current sampled value. Only the decorative arc interpolates; no previous numeric glyphs are blended into the new frame.

Missing sensors are shown as N/A, without retaining an old reading. Frequencies and temperatures are selected with the same default CPU/GPU grouping used by Focus. No motherboard or coolant temperature is substituted for CPU/GPU temperature.

## Threading and verification

The Python worker performs sensor reads, rendering, encoding, and optional transmission. QML runs on the GUI thread. A bounded latest-frame queue avoids accumulating an obsolete preview backlog. Font changes, precision, FPS, quality, and report delay are applied when starting a new session. The preview and raw table are updated together from that session's event.

Local checks on October 28, 2026:

- 54 tests pass with the desktop dependencies installed. This includes new precision, sensor snapshot, worker lifecycle, mock transmission, error propagation, device discovery, diagnostic formatting, and headless QML smoke tests.
- The QML window was rendered offscreen with synthetic sensor values and visually inspected. Its output controls were checked to remain within their card.
- A wheel was built, installed in the project environment, and checked for the bundled `qml/Main.qml` asset.
- The user confirmed that the native window opened in preview mode. A controlled hardware trial through the same QML controller completed 250 frames and stopped cleanly. The user confirmed agreement of all four values with the physical LCD and requested a smaller CPU readout; see `desktop-trial.json`.

The source archive excludes `.venv`, build products, raw captures, downloaded font candidates, and user photographs. The public UI preview uses synthetic data. Existing hardware trial records remain separate from the new GUI checks.

## Current Focus spacing

After confirming that all four LCD targets matched the physical screen, the user requested a little more room around the CPU value. The current maximum CPU numeral size is 64 native pixels (previously 72); secondary readings, measured degree spacing, decimal selection, and the selected font weight are retained. This is a visual change, not a telemetry or protocol change.

The user approved this 64 px Focus layout after the physical trial. A subsequent font comparison led the user to select Outfit weight 350 as the new default, retaining one decimal and the 5 px aligned highlight arc. Outfit is included in the source archive and wheel with its separate license.

## Historical Studio layout and local SVG icons

The production interface now follows the approved Studio direction, implemented with Qt Quick/QML and local Lucide SVG assets. Display contains the circular JPEG viewport, compact CPU/GPU values, appearance summary, and start/preview actions. Sensors exposes the current labels, source paths, and values. Diagnostics contains raw vs target comparison, sample identity, and host timing. Settings contains device, profile, font, and transmission controls. Stop is visible globally while the session is active.

The underlying renderer, sensor snapshot sharing, and HID protocol are unchanged. The circular desktop viewport clips only the physically invisible corners of the decoded JPEG; it does not alter the image sent to the LCD. The interface uses Outfit at normal UI weight for legibility; the LCD theme retains its separately selected weight 350.

Media and Dual placeholders were removed after review; they are not shown until implemented. Color and Comet motion are descriptive in this revision. The current implementation is dark-only, requires stopping before changes, and does not persist preferences. Smooth and Conservative presets populate the existing FPS/quality/delay controls. The same explicit start action is required for LCD output.

The icon files are bundled with the complete Lucide ISC and Feather-derived MIT notices, source URLs, and original file hashes. Theme variants change only the stroke color. No online icon service or additional UI framework is used. The optional Qt checks now verify SVG validity, source hashes, license notices, and all four active navigation pages. There are 54 passing tests with desktop dependencies installed. The real Studio window has been opened for user review; approval for the first commit is pending.

## Historical compact Studio refinement

The user approved the compact proportions after reviewing the native Qt example. Production now opens at 960×690 logical pixels with a 300×300 circular JPEG viewport in a 344×384 preview card. CPU/GPU summaries are compact. The tall secondary pages can scroll while the output bar remains fixed below them.

No coming-soon controls are displayed. All output actions are grouped with the session state in the bottom bar. During LCD output it shows Stop display; during local preview it shows Stop preview; after stopping it shows Start display and Preview only. The bar remains accessible across all active navigation pages. This preserves the existing stop-before-edit lifecycle without presenting inactive start buttons during output.

The 54-test suite includes all navigation pages and verifies contextual Stop text, visibility during the active session, and reappearance of start actions after stopping. A synthetic offscreen render was visually checked, then the actual compact application was opened in preview-only mode. No LCD protocol change or additional optical performance claim is made by this UI revision. The first Git commit remains pending an explicit instruction to create it.

## Secondary text readability

Secondary captions, navigation details, status text, and footer labels now use a minimum explicit size of 14 logical pixels and a lighter muted color (#abb8c0). The compact window gained 20 logical pixels in height to accommodate the larger text. The LCD renderer and its selected typography are unchanged. All 54 tests pass, and a synthetic offscreen render was checked for clipping.

## Continuous preview lifecycle validation

The current 64-test suite covers independent output stop/resume, final standby report content, descriptor release, suspend-worker acknowledgement and resume, output-open failure without a retry loop, standby-write failure, automatic single-device startup, and ambiguous discovery. The QML smoke check verifies navigation and the absence of preview controls without touching hardware. Historical notes above describe earlier UI behavior and are superseded by the Controls section. Physical suspend/resume remains unverified.

## Live rendering updates and consumption measurements

The user reported ghost-like CPU digits. The renderer explicitly blended old and new numbers for 250 ms; that software transition is removed. A pixel regression test compares the very first changed number against a fresh render of the new value. This does not establish the absence of physical LCD persistence, which requires observation.

Live edits are coalesced and processed by the worker at a frame boundary. A replacement renderer is validated before committing it, preserving the arc position and animation clock. An active HID descriptor is retained. Tests cover live format/weight updates during transmission, malformed font rollback, coalescing, and rejecting device changes during output. Sensor sampling is normally 1 Hz; applying a new renderer takes a fresh snapshot for internally consistent diagnostics.

See [resource profiling](performance.md) for scope, measurements, and a repeatable long-run command.

## Rounded comet refinement

The user confirmed correct direct numeric updates and working live settings. The comet and both arc endpoints now have circular caps using the existing 5 px diameter. Cap centers follow Pillow's inward stroke centerline, rather than the outer arc box, avoiding the earlier visible alignment offset. The active arc and comet share the same rounded mask. The existing three-second sweep and fading trail are retained. The 65-test suite passes, including cap geometry and highlight containment. Synthetic frames were visually checked at several positions; physical evaluation of the rounded appearance remains pending. No USB protocol or suspension behavior changed.

## Live comet speed

Appearance exposes a Comet speed slider from 0.25× to 3× in 0.25 increments. Default 1× retains the three-second sweep; 0.25× takes 12 seconds and 3× takes one second. The existing 200 ms settings debounce applies live to preview and physical output. A renderer update carries forward the current comet phase, so speed changes do not jump to another point in the sweep. Frame rate, sensor polling, report delay, and digit updates remain independent. The setting is not persisted yet. CLI Focus and GUI accept `--comet-speed 2` as an optional initial value.

All 67 tests pass, including period scaling, phase continuity through live speed changes, range validation, live session configuration with USB retained, and an actual QML slider edit reaching the worker. A synthetic Studio render was checked for layout clipping. Physical speed evaluation remains pending.

## LCD palette, rainbow comet, and simplified Studio controls

The current window is 960×650 logical pixels, retaining the approved 300×300 preview and 344×384 card. Appearance now contains six accent swatches (mint, blue, violet, pink, amber, and ice), a Custom color dialog, a compact Accent/Rainbow comet selector, a small speed slider, a temperature precision selector (Whole degrees / 1 decimal), and the typeface summary. The former oversized checkbox and descriptive-only animation rows are removed. The single available Focus theme is shown as a label, not a selectable button.

LCD accent changes the active arc base, CPU frequency, degree symbol, and tail tint. The Accent mode preserves the white head; Rainbow assigns smoothly varying HSV colors to the fading tail. Both can be combined with any selected LCD accent. Rounded caps, the shared containment mask, three-second base cycle, and speed multiplier remain in effect. The desktop navigation accent is deliberately unchanged. Palette/style updates use the same live frame-boundary configuration and preserve motion phase; no USB restart occurs. Preferences are still not persisted. CLI Focus and GUI support `--accent "#ac8aff" --comet-style rainbow`.

Transmission state now appears once, alongside the output action. The top badge, repeated output subtitle, preview JPEG caption, and normal-state footer are removed. Errors retain their own visible line. Controls remain available across navigation pages.

All 69 tests pass. Added checks cover color parsing/rejection, unchanged numeric values across styles, visible rainbow rendering, and mask containment for multiple arc lengths. The active-output update test includes accent and style changes while retaining the USB descriptor. The QML smoke test changes the actual palette property, style selector, and precision selector and verifies worker configuration. A synthetic violet/rainbow Studio render was checked for clipping. Physical color/style evaluation remains pending; no additional resource, USB, or suspend trial was performed.

## Theme, popup, alignment, and tray validation

All 71 tests pass. A QML test opens the real popup, verifies keyboard selection, visits all four pages in each theme, checks that theme changes alone do not start a session, and compares the vertical centers of output text and action. Both icon variant sets pass Qt SVG validation. Dark/light popup screenshots and the Light Settings page were inspected using synthetic telemetry.

A headless tray integration test uses a simulated tray host with a real QApplication, QML window, menu, and preview worker. It verifies automatic hide on minimize, continued frame production on the same worker while hidden, restoration by icon activation, restoration if the host disappears, fallback when no host exists, and orderly shutdown through Quit. This does not establish actual KDE/GNOME/panel tray behavior. Native tray validation on the user's desktop remains pending. No new physical LCD or suspension trial was performed.

## Preferences and bilingual units validation

All 79 tests pass. Coverage includes numeric Celsius/Fahrenheit conversion and missing values, Celsius arc invariance, explicit raw-C/target-F formatting, Fahrenheit text bounds, unit changes on the same active USB worker, complete preference round-trip, 0600 file permissions, exclusion of device/output state, corrupt/invalid field recovery, missing font fallback, and preservation of the previous file when atomic replacement fails.

Qt integration changes real language/theme/unit/style/speed/weight controls, checks keyboard-focus help visibility, verifies selected values survive language changes, saves preferences, and creates a fresh engine to confirm restored controls. A write failure is surfaced in both languages. Tray actions are also checked in Spanish. Spanish/light General, expanded Advanced, and Fahrenheit preview renders were inspected using synthetic readings. These tests do not validate physical Fahrenheit output, real desktop preference restoration, native tray behavior, or system suspend. No private preference file or personal image was added to the repository.

## In-window custom accent picker

Custom now opens a Qt Quick `Popup.Item` anchored below its button and constrained to the main window. The native ColorDialog is removed. The popover follows Dark/Light and the selected UI language, with a saturation/value field, hue slider, current-color swatch, validated `#RRGGBB` text field, and Done action. Partial/invalid hex input leaves the last valid accent unchanged. Visual selection and accepted hex edits use the existing live/debounced render update and preference storage. Done, Escape, or an outside click dismiss the picker; dismissal keeps the already applied color. Keyboard users can choose a precise color with the hex field and adjust hue with the slider.

All 80 tests pass. A new Qt test verifies the top-level window count remains unchanged, alignment under the Custom button, real keyboard hex editing, rejection of a partial color, HSV mouse controls, theme switching, Escape/outside dismissal, and delivery of the color to the same running worker. Both theme renders were visually reviewed using synthetic readings. No additional physical USB or suspend trial was performed.

## Selected LCD tray icon

The user selected concept B (LCD) from the original icon study. The generic monitor tray icon is replaced by original project artwork in `assets/branding`: a rounded cooler outline surrounding a circular display. Dark/light variants follow Qt's desktop color scheme rather than the application theme, since the system panel may use a different appearance. A medium-green fallback is used when the scheme is unknown; desktop scheme changes update the existing tray icon. No manufacturer logo or vendor asset was recovered or copied.

All 80 tests pass. The tray integration check now renders the selected icon at 16, 22, and 32 pixels in both schemes and the fallback, checks nonempty/different theme renders, and exercises icon updates without changing the worker lifecycle. The artwork and provenance README are packaged in the wheel/source distribution. Native panel appearance still requires user confirmation.

## Application name and title branding

The selected name is **FX240 LCD STUDIO**. It is used unchanged across interface languages for the native window title, application metadata, README heading, and tray tooltip. The selected original LCD icon is shared by the tray and application/window icon. A 30 px version sits next to FX240 in the sidebar, with LCD STUDIO beneath it; its foreground follows the application's Light/Dark appearance. Native window/tray artwork follows the desktop scheme. Native title-bar icon presentation remains subject to the desktop/window manager.

The package name (`fx240-linux`), command (`fx240`), and existing private preference location are retained, so saved configuration remains compatible. All 80 tests pass, including application/window identity, icon presence, both theme variants, and the unchanged title after a language switch. A synthetic Spanish/light render was visually inspected. The English Reddit announcement is a draft in `docs/community/reddit-announcement.md`; nothing has been posted or published.

## Aligned wordmark and actionable preference notices

The FX240 title and LCD STUDIO subtitle now share a left edge in a single text column beside the LCD icon. Recovery notices are separate from rendering/USB errors: a themed information banner opens an in-window Details dialog. It explains whether settings were reset on load or could not be saved, shows the local configuration path, lists affected fields with reasons and fallback values, and includes technical details where available. Save failures expose a Retry saving action without stopping the LCD. A successful save clears the notice and closes its dialog. Messages are available in English and Spanish; native technical details are retained.

A real loader defect was found during this refinement: float-annotated FPS/delay settings had integer default literals, and the loader inferred their accepted type from those literals. Values such as 24.0 and 2.0 written by the GUI were incorrectly treated as invalid on restart. Validation now uses dataclass field types, accepting finite valid integer or float representations for float fields while retaining strict integer validation for quality/weight/rotation/precision. No existing user file is modified by the tests.

All 82 tests pass. Regression coverage includes decimal timing round-trips without warnings, exact recovery field lists, save-error details/retry, text-column alignment, opening notice details without another native window, and preserving valid timing settings after a recovery save. Synthetic Spanish/light recovery and detail views were inspected. No new hardware, long-run, or suspend result is claimed.

The sidebar icon was subsequently centered vertically against the complete FX240 / LCD STUDIO text block, replacing its title-only top alignment. The existing geometry check now verifies that shared vertical center; the focused test passes and a synthetic render was visually inspected.

## Experimental high-rate measurement seam

`Session` accepts an optional theme factory, and `create_engine` accepts an optional session factory, so external instruments can exercise diagnostic counters and experimental settings through the same transport/preview pipeline. Normal startup uses the unchanged Focus/Session factories and 24 FPS settings cap. The benchmark uses no preference store. Python render-thread callbacks were removed from the instrument after a shutdown hang; native measurement now uses GUI-thread queued swap notifications, described as a presentation proxy. Details and remaining validation gates are in the [extended trial report](benchmarks/2026-11-01/README.md).
