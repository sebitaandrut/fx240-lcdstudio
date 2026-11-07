# Using FX240 LCD STUDIO

Install `.[desktop]` and run `fx240 gui`, or open your locally built executable. See [building](building.md) for dependencies and packaging. Qt is optional for CLI media playback; the GUI uses PySide6 and QML.

## Display and live settings

The preview starts automatically. Physical output also starts when exactly one matching LCD is accessible, or an explicit device is selected. No match or ambiguous discovery leaves preview available. The transport validates the device identity and takes a cooperative exclusive lock.

- **Stop display** finishes the current frame, attempts one recreated standby image, and releases USB. Preview and sensor sampling continue.
- **Start display** resumes output using the current settings.
- The editor customizes layer colors, effects, animation speed, temperature units and precision. The base Focus arc and comet are 8 LCD pixels wide, with rounded ends.
- Designs opens the built-in and saved galleries. Settings contains language, startup, and transmission settings. Advanced settings adds device, FPS, JPEG quality, and report delay.
- Edits apply between complete frames after a short debounce. Invalid edits keep the last working configuration. Pause physical output before changing devices.

Outfit is bundled under its upstream license; no global font installation is required. Comet speed ranges from 0.25× to 3×, independently of sensor sampling and FPS. The application includes Focus, Dual, Trace, and Halo, with a local composition editor.

## Sensors and diagnostics

One sensor snapshot feeds the rendered frame and diagnostics. Sensors are normally sampled once per second; animation defaults to 24 FPS, independently of sensor sampling. Stable readings, driver cadence, and display rounding can leave a number unchanged. Numbers switch directly to the new sample; only the decorative arc interpolates.

**RAW SAMPLE** shows the provider value and source unit. **LCD TARGET** shows its display formatting. The preview is the encoded JPEG decoded back to upright orientation; completed writes do not prove immediate physical presentation. CPU/GPU summaries and target values use the same snapshot. Missing sensors show `N/A` rather than a retained old value.

Fahrenheit is converted from the original Celsius sample before rounding. Raw diagnostics and arc scaling remain Celsius. Sensor names and paths preserve driver distinctions such as CPU Tctl, GPU edge, and individual CPUFreq policies; they are not interchangeable measurements. Review sensor paths and error details before sharing screenshots.

## Preferences and language

English/Spanish and dark/light appearance switch live. Render and interface settings persist in `$XDG_CONFIG_HOME/fx240-linux/settings.json`, defaulting to `~/.config/fx240-linux/settings.json`. Writes are validated, debounced, atomic, and private to the user. Corrupt fields fall back with an explanatory notice. A custom font path remains in this local file.

The selected device path, sensor samples, and sending/paused state are not saved. Explicit CLI options override the corresponding saved GUI fields. Named compositions are available in the editor described below.

## Tray, login, and standby

With **Start at login → Minimized in tray** enabled, closing the window with X hides it in the tray and keeps preview/rendering and LCD output active. With this option disabled, X exits and attempts standby. **Quit** in the tray always exits, including when startup is enabled or a live draft requires a decision. If no tray is available, X follows the exit path; losing the tray restores a hidden window. The separate Hide to tray button has been removed.

Enable **Settings → Start at login → Minimized in tray** to install a per-user desktop autostart entry. Keep the executable/environment in a permanent location. It starts after graphical login, not before login. Disable and re-enable startup if the executable moves.

Standby is artwork recreated in code, not a recovered vendor bitmap or firmware reset. The application coordinates logind shutdown/sleep preparation and uses a separate fallback for abrupt graphical connection loss. Power loss, forced termination, a blocked driver, or another sender can prevent standby. Reboot/shutdown passed initial trials with desktop autostart; development-launched instances failed during reboot. Initial packaged suspend/resume checks with active and manually paused output passed owner observation; repeated cycles and automatic recovery after USB errors remain unverified. See [validation](validation.md).

## CLI media and telemetry

CLI modes simulate by default; these examples do not send to USB:

```bash
fx240 sensors
fx240 focus --duration 2 --preview /tmp/fx240-focus.png
fx240 image /path/to/image.png --duration 2
fx240 gif /path/to/animation.gif --duration 10
```

For physical output, identify the LCD's `/dev/hidrawN`, configure local access, and explicitly add `--device /dev/hidrawN --send`. The number can change after reconnection. For example:

```bash
fx240 gif /path/to/animation.gif --overlay --device /dev/hidrawN --send --duration 10
```

Use `fx240 --help` for orientation, timing, encoding, font, and sensor options. CLI defaults are independent of saved GUI preferences. No administrator privileges are needed for simulation; do not run the GUI as root to bypass USB access errors.

CLI media input is limited to regular files up to 64 MiB, source frames up to 16 megapixels, and at most 1,000 frames. Invalid/truncated media is rejected rather than treated as a successful playback. Saved preferences are limited to 64 KiB; malformed or overly nested data falls back to defaults with a notice. These bounds reduce resource exposure but do not sandbox native decoders.

Local media and font inputs must be regular files selected by their actual path (leaf symlinks/special files are rejected). Font snapshots are limited to 16 MiB. See [security review](security-review.md) for the file-handling boundary.

## Animation, backgrounds, and installed fonts

The Focus arc in the editor offers Comet, Orbit (two moving points), Pulse (a slow brightness cycle), and Static. Effect color and speed update the draft preview; background GIF timing remains independent. Numeric readings still change atomically at the sensor sampling cadence.

Add a background as an image/GIF layer or use a two-color Gradient layer. Aurora blends two glows over a dark base, Linear blends along an angle, and Radial blends from the center to the edge. Adjust the direction for Aurora and Linear independently of layer rotation. Change layer opacity to dim the background and improve legibility. Select an image/GIF layer to adjust Image zoom from 25% to 400%, centered within the layer; 100% restores the existing fit. Zoom crops enlarged content to the layer, applies before rotation, and is saved with the profile. It scales the bounded decoded frame, so it does not restore source detail lost during initial fitting. The output stays 240 × 240, and zoom does not enlarge the GIF buffer. Desktop GIFs accept up to 2000 frames, 4 megapixels per source frame, 300 million cumulative source pixels, and 64 MiB per file. Static images retain the 16 megapixel limit. GIFs above 120 frames use a bounded 12-frame queue automatically; shorter assets use a two-entry decoded-frame cache. These limits do not cap total application memory. Frame delays are clamped to 40 ms–60 s and playback follows elapsed time without increasing output FPS. Initial inspection and seeks may pause; invalid live selections preserve the previous renderer. Clearing/removing media releases its renderer lease.

In the editor’s typeface controls, **Refresh** discovers local scalable TTF/OTF faces by family/style through Fontconfig. Choose a face without finding its file manually; bundled Outfit and the custom-file option remain available. Font collections/named instances are omitted until face-index support is implemented. Static fonts keep their own weight. Discovery runs off the UI thread, with a timeout and output/entry limits. If Fontconfig is unavailable, Outfit/custom files still work. The Arch package already depends on Fontconfig. [Fontconfig's fc-list manual](https://xorg.freedesktop.org/archive/X11R7.0/doc/html/fc-list.1.html) describes local font enumeration.

Animation, dimming, and selected font/background paths are saved in the private local preferences file. No source image/font, complete font catalog, or path is uploaded or copied into this repository. Paths are personal information: do not share settings or raw error screenshots unreviewed. JPEG composition removes source metadata, not personal content visible in an image. Installed fonts/media remain untrusted native-decoder inputs; use trusted files and updated dependencies.

Synthetic examples can be generated without USB or sensors:

```bash
PYTHONPATH=src .venv-build/bin/python examples/generate_composition_previews.py --output-dir /tmp/fx240-synthetic-previews
```


## Named compositions

**Designs** opens with the active design selected and lists **Originals** and **My designs**. Select a tile to activate it immediately. The preview follows the accepted design, and transmission keeps its running or paused state. **Edit copy** opens a built-in design as layers and retains its existing settings in the draft. **Edit design** opens a saved profile. Use **New design** for a new composition, or **Continue draft** to return to unsaved edits. In **My designs**, choose **Select**, mark saved profiles, and confirm **Delete selected**. Activate another design before removing the one in use. Profile removal leaves source media and fonts on disk.

The editor’s properties include visual color pickers with optional hex entry, layer typography, and background opacity. Animation speed applies to the current design. Temperature precision and units are available when a temperature layer is selected. Outside a temporary LCD trial, edits affect the draft. Choose **Save and show**, or save and activate the profile from Designs. Saving changes to an already-active profile updates its output after renderer validation.

Editor retains Studio's sidebar, theme, typography, panels, and output controls. Its workspace has Layers, a circular 240×240 canvas, and Properties. Drag or resize with the mouse, enter exact coordinates, reorder, hide, delete, and undo. A new draft starts with four readings and a CPU label. Add readings, text, local images/GIFs, or a gradient. Open **+ Effects** to add the CPU temperature arc from Focus, either decorative arc from Dual, the CPU temperature history from Trace, the radial pulse from Halo, a segmented ring, or a radar sweep. Each effect is an editable layer. Trace fills in as readings arrive. Rectangle bounds stay within the square canvas and the circular viewport clips its corners. Long drags retain their pointer grab instead of being taken by the parent scrolling area.

Shift-click layers in the canvas or list, or use the list checkboxes to build a selection. Drag any selected layer to move the group. The shared corner handle scales it proportionally, and the rotation buttons turn it around its center. Properties can apply opacity, visibility, and color to the selection. Color affects text and graphics layers; images retain their original colors. Delete selected layers and use Undo to restore them in one step. Geometry stays within the square canvas.

With the canvas or layer list focused, press an arrow key to move the selection by one LCD pixel or Delete to remove it. Use Ctrl+Z to undo a composition edit and Ctrl+Y to redo it. Text fields keep their own editing shortcuts.

Select one layer and use **Layer zoom** in Properties to scale its contents from 25% to 400% around the center. This works for effects such as Halo as well as text, readings, and gradients. The layer keeps its position and dimensions, and content outside it is cropped. Use **100%** to reset. Image and GIF layers keep the equivalent **Image zoom** control.

Give the draft a name and use Save, Save copy, or Save and show. Up to eight named compositions are stored in private `profiles.json` beside `settings.json`; names never become filenames. Draft and active profile are restored separately. New/Open ask before replacing an unsaved draft. Delete a profile only after switching away from it in Designs; its draft remains available. Missing assets preserve editable references and prevent invalid previews from being saved/activated. An unavailable startup profile falls back to Focus without deleting the library.

Variable fonts expose a supported weight axis. Static fonts expose their installed styles (Regular/Bold/etc.) instead of a numeric weight control that cannot affect that face; refresh installed fonts to discover variants. Font collection/named-instance support remains limited as documented above. Per-layer fonts, sizes, colors, alignment, opacity, and geometry are stored in each composition. Temperature units/precision and global output settings remain shared.

Bounds: declarative JSON, 24 KiB per scene, at most 16 layers including two media and two arcs; text up to 160 characters; eight profiles and a 256 KiB library. Private preferences are capped at 64 KiB before atomic replacement. Neither file embeds media or executable expressions/QML. Only runtime-validated drafts are autosaved; wait for a valid preview before closing. Files are local references, not portable exported packages. Import/export, weather/clocks, and per-layer rotation are not implemented.

The draft worker has a permanently rejecting USB transport, no device, and output disabled. It uses cached main-session metrics instead of querying sensors again. Closing Editor stops its worker; font faces are cached separately per rendering thread. Cache limits bound cached canvases, not total active-scene or decoder memory. Native LCD editing, complex asset loading during shutdown, and endurance/resource checks remain necessary before release.

Installed-font selectors use a searchable, in-window popup in both application themes. Search filters the local catalog in memory; it does not run a command or send font names elsewhere. File browsing uses the embedded Studio asset picker with the application palette. These interface changes do not establish compatibility with additional hardware or distributions.

Draft-discard and profile-delete confirmations use the Studio theme and translated action labels in the same window. Escape or Cancel preserves an unsaved draft; discarding requires its explicit action.

The window has a minimum size of 1200 × 760 logical pixels to preserve a usable three-column workspace and circular preview. Inspector content reserves scrollbar space, palette items wrap, and narrow sensor cards place frequency below temperature. Qt regression checks cover widths of 1200, 1280, 1440, and 1600 at minimum height, in English/Spanish and both themes. Smaller window layouts are not supported.

Composition actions keep two rows at every supported width: navigation, profile name, Save, and Save and show on the first; New, Save copy, and Delete profile on the second. The name field expands into available space. Layout checks cover both themes and languages without toolbar/canvas overlap.

## Temporary live LCD drafts

In Editor, **Visualize on LCD** sends the validated draft through the existing main sender without saving a named profile. Valid layer edits are coalesced by the 40 ms draft update timer, validated by the draft renderer, then replaced at a main-output frame boundary. The editor keeps its draft preview until the main sender delivers the first matching trial frame. It then shows the sender’s decoded JPEG and telemetry sample; after returning, it resumes the independent draft preview. It uses the existing configured FPS limit; this is not a new physical refresh-rate claim. A missing device or invalid draft prevents starting. Invalid assets keep the last working output.

**Finish LCD preview** offers Save and apply, Save and return to previous output, Return without saving, or Keep editing live. The dialog includes the profile name. Save/apply failures remain actionable. Draft autosave is separate from named-profile saves. Saving an already-active profile and returning restores the pre-trial scene for the current session; selecting that profile again or restarting loads its saved version.

Navigation away from Editor or ordinary application exit asks for a decision while a trial is active. Stop LCD immediately requests standby and remains paused after the decision. Suspension uses the existing standby/resume path; system shutdown exits without blocking on a dialog. Temporary output settings are never committed to preferences. An ordinary exit that returns to the previous output goes directly to standby, so unavailable old assets cannot prevent closing.

These paths are covered with synthetic transports, including save failures, invalid media, restoration failures and retries, stale frame notifications, paused output, Stop during a queued apply, and close decisions. The owner confirmed initial suspend/resume with both a saved long-GIF profile and a temporary LCD draft on Arch Linux; repeated cycles remain pending. Local media/font references remain private local files; no new network access or executable scene format was added.

## Local asset picker

Image/GIF and manual font-file selection use an in-window Studio dialog, translated and styled for both themes. Shortcuts use existing directories returned by Qt's XDG-aware standard paths; missing and duplicate shortcuts are omitted. Double-click a folder to enter it, enter an absolute local folder path, or filter the current folder by name. Images and fonts use separate extension filters. Hidden files, symlink files, and special files are not listed. Selected content still passes the existing bounded regular-file loaders.

Directory enumeration runs on one background worker, with one coalesced pending navigation request and a 4096-entry visit limit. Stale/cancelled results cannot replace the current folder. No file catalog, navigation history, or shortcut paths are logged or saved; the last folder per type is kept in memory only. This provides no new application network capability; local paths on user-mounted filesystems follow the filesystem's behavior.

For isolated candidate testing, use `gui --config-home /absolute/test/config` and keep the normal `XDG_CONFIG_HOME`. The option isolates Studio preferences, profiles, and its managed autostart entry without hiding the desktop's `user-dirs.dirs` settings from Qt. `XDG_STATE_HOME` may remain isolated for lifecycle diagnostics. Older test commands that override all of `XDG_CONFIG_HOME` can make Qt fall back to nonexistent English folder names on a localized desktop.

## GIF diagnostics

Long-GIF buffering is automatic; no extra playback switch or footer badge is needed. Diagnostics shows queue occupancy/capacity and decoder waits only while the output renderer owns a long-GIF stream. These counters omit filenames and asset paths. A wait includes startup, seeking, or decoding that has not reached the requested frame; it is not a measured physical LCD frame drop. The draft preview uses its own clock and decoder, so its queue is not included in the output counters. See [performance and limits](performance.md#long-gif-playback).

## Editor rotation, temperature units, and clearing (unreleased)

Every layer has a clockwise rotation from 0 to 359 degrees, plus quarter-turn buttons. Rotation is around the layer center and works on image/GIF frames, text, readings, and arcs. The numeric X/Y/width/height describe the unrotated rectangle. Drag handles follow the rotated layer; rendering expands into transparency and the final canvas/circular viewport clips overflow. Rotation does not rotate the complete LCD or change its configured orientation. Bounds limit transformed surfaces to LCD-scale images; this does not guarantee 24 FPS for every composition.

The °C/°F switch appears only in the properties of a selected CPU/GPU temperature reading, hidden for frequencies, text, images, and arcs. It selects one unit for the composition and stores that choice in its profile/draft. Raw sensors and CPU arc scaling remain Celsius. Focus retains its own unit. Legacy scenes without a unit override inherit the global setting until a composition unit is chosen. Output diagnostics uses the renderer's effective unit, including during live LCD trials.

**Clear all** asks for confirmation and removes every layer from the draft while keeping its name, profile association, and temperature unit. Undo restores the composition as one action. The saved profile is preserved until Save is explicitly used. During a temporary LCD trial, the empty draft is rendered live after validation, like any other valid edit.

Older scenes load with zero layer rotation and inherited units. Older application versions cannot interpret the new rotation/unit metadata: use an isolated `--config-home` for candidate trials rather than mixing a new writer with an older installed/autostarted application. No script, URL, executable expression, network provider, or external-data query is added by these controls.

Local candidate checks passed 201 source tests with Qt and seven bounded input-property checks; an additional synthetic-sender trial exercised rotation, Fahrenheit, clearing, and undo during live output. The standalone self-test opened no HID and used no preference store. An eight-second backend-only stress sample with two full-canvas long GIFs rotated 45/135 degrees and five text/reading layers rotated 15 degrees observed 24.01 host FPS, 33.13 ms p95 pipeline time, and no pipeline deadline misses/decoder waits; this excludes real USB and QML presentation and does not measure physical LCD FPS or endurance. Device validation of these new controls remains pending.

### GIF playback during editing

Geometry-only edits reuse bounded GIF-inspection and font-validation results while the selected files retain the same regular-file identity. Leaf links/special files are rejected before cache lookup; replacement, size, modification time, or change time invalidates reuse. Registry locks do not cover file indexing/decoder startup. A validated configuration frame is rendered once and reused for that output iteration. Reported pipeline timing now includes configuration validation; earlier timings that excluded this work are not directly comparable during live edits.

For GIF layers, **Match GIF to output FPS** lengthens frames that would be faster than the selected output interval. This reduces periodic skips caused by a source/output-rate mismatch, at the cost of slower playback. For example, a uniform 25 FPS clip becomes 24 FPS at the standard output setting. The switch is opt-in, stored per layer, and follows later output-FPS changes. Disabled mode retains the existing player timing rules, including the 40 ms–60 s frame-delay bounds. Separate clocks have separate streaming decoders even when two layers use the same file. Input files are never rewritten.

This option adjusts the timing of existing GIF frames within the selected output rate. Missed render/USB deadlines and panel presentation artifacts require separate checks; a short ideal sampling check is not optical verification. During a four-second synthetic 120-frame/512×512 GIF editing exercise, the same host observed 9.19 frames/s and 108.65 ms p95 frame gaps before the cache/render fix, versus 23.86 frames/s and 42.26 ms after. No USB or Qt presentation was included. Tests use synthetic files; owner media and raw reports remain private.

### Delivery scheduling candidate

The worker prepares and JPEG-encodes each upcoming frame before its intended USB delivery deadline. Rendering/sensor work that fits in the available interval therefore does not delay the start of every report burst. Late preparations remain best effort; this is not panel-vsync synchronization. Intentional alignment waits are excluded from pipeline processing time.

Residual physical motion artifacts remain under investigation. The owner still observed the defect with a 1 ms report delay and with a 20 FPS target. A subsequent synthetic 24 FPS trial bypassed GIF decoding and editor updates while retaining the session/JPEG/HID path: host frame IDs were consecutive, and private camera footage showed both matching and differing consecutive IDs at four image heights during transitions. Camera exposure/rolling shutter, panel scanout, and pixel response remain confounded. This does not establish complete-frame presentation, a panel fault, or a synchronization fix. Raw footage and decoded traces are private and excluded from the repository.

The owner also reported stutter with the same GIF in the official Windows application running in a VM. Qualitative review of that private recording showed overlapping sphere contours during some transitions. Vendor cadence was not instrumented or matched to Studio, and guest/USB timing adds another uncontrolled variable. This supports the symptom not being exclusive to Studio; it does not prove identical causes, equal severity, or an unavoidable hardware limitation.

For controlled comparison, `gui --experimental-jpeg-420` changes the main session's JPEG chroma subsampling from the default 4:4:4 to 4:2:0, including its decoded sent-frame preview. This session-only flag is not saved in preferences/profiles or added to managed autostart. Close all senders before launching another candidate, keep the same composition, 24 FPS, quality 65, 2 ms delay, and GIF pacing setting, and change only this flag between runs. The independent draft preview keeps its default encoder; use Visualize on LCD to compare the sent frame. Standby remains available. Smaller JPEGs can reduce report count but may soften colored text/edges; this experiment does not establish a motion-artifact fix or new physical FPS. Omit the flag to return to 4:4:4.

Stop interrupts an alignment wait and discards the prepared frame; pause/sleep are rechecked before USB upload so pending work does not bypass standby. Synthetic-clock tests cover variable rendering costs, pause, sleep/resume, and stop during this wait. With a synthetic 15 ms sensor delay, a short simulated transport exercise reduced the maximum completion gap from 56.8 to 41.8 ms after startup. This does not measure the real panel or establish a physical fix; native optical comparison remains pending.

## Advanced output timing

Output defaults to 24 FPS, JPEG quality 65, and a 2 ms pause between HID reports. Settings has no output-preset selector. Advanced settings allow 1–60 host FPS, quality, and report delay independently; accepted changes persist. Rates above 24 are experimental and may increase CPU use, USB traffic, and incomplete optical transitions. The GUI polls the bounded latest-frame mailbox more often above 24 FPS; this does not certify native preview or LCD FPS.

Trying a 1 or 0 ms pause may help when USB transmission exceeds the requested frame budget. It cannot create intermediate GIF frames, synchronize LCD scanout, or guarantee elimination of tearing. Previous shorter-delay trials did not establish a tearing fix. Restore 2 ms if problems appear. Source GIF timing is preserved, including the existing 40 ms minimum frame duration; raising output FPS does not accelerate the source animation or interpolate it. Match GIF to output FPS only slows source frames when they are faster than output.

Line-like cuts on moving content remain under investigation; see [the focused tearing report](tearing.md). No new protocol command or firmware-writing capability was added.
