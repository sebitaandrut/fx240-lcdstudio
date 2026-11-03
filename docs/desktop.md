# Using FX240 LCD STUDIO

Install `.[desktop]` and run `fx240 gui`, or open your locally built executable. See [building](building.md) for dependencies and packaging. Qt is optional for CLI media playback; the GUI uses PySide6 and QML.

## Display and live settings

The preview starts automatically. Physical output also starts when exactly one matching LCD is accessible, or an explicit device is selected. No match or ambiguous discovery leaves preview available. The transport validates the device identity and takes a cooperative exclusive lock.

- **Stop display** finishes the current frame, attempts one recreated standby image, and releases USB. Preview and sensor sampling continue.
- **Start display** resumes output using the current settings.
- Appearance controls change the accent, rainbow/accent comet, speed, temperature unit, and decimal precision live. The base arc/comet stroke is 8 LCD pixels, with rounded ends.
- Appearance contains Focus typography/background controls and saved designs. Settings contains language, startup, and transmission settings. Advanced settings adds device, FPS, JPEG quality, and report delay. Information icons explain the controls.
- Edits apply between complete frames after a short debounce. Invalid edits keep the last working configuration. Pause physical output before changing devices.

Outfit is bundled under its upstream license; no global font installation is required. Comet speed ranges from 0.25× to 3×, independently of sensor sampling and FPS. The application supports Focus and a local experimental composition editor; Dual remains planned.

## Sensors and diagnostics

One sensor snapshot feeds the rendered frame and diagnostics. Sensors are normally sampled once per second; animation can run at 24 FPS. Stable readings, driver cadence, and display rounding can leave a number unchanged. Numbers switch directly to the new sample; only the decorative arc interpolates.

**RAW SAMPLE** shows the provider value and source unit. **LCD TARGET** shows its display formatting. The preview is the encoded JPEG decoded back to upright orientation; completed writes do not prove immediate physical presentation. CPU/GPU summaries and target values use the same snapshot. Missing sensors show `N/A` rather than a retained old value.

Fahrenheit is converted from the original Celsius sample before rounding. Raw diagnostics and arc scaling remain Celsius. Sensor names and paths preserve driver distinctions such as CPU Tctl, GPU edge, and individual CPUFreq policies; they are not interchangeable measurements. Review sensor paths and error details before sharing screenshots.

## Preferences and language

English/Spanish and dark/light appearance switch live. Render and interface settings persist in `$XDG_CONFIG_HOME/fx240-linux/settings.json`, defaulting to `~/.config/fx240-linux/settings.json`. Writes are validated, debounced, atomic, and private to the user. Corrupt fields fall back with an explanatory notice. A custom font path remains in this local file.

The selected device path, sensor samples, and sending/paused state are not saved. Explicit CLI options override the corresponding saved GUI fields. Named compositions are available in the editor described below.

## Tray, login, and standby

Minimize or **Hide to tray** keeps rendering and physical output active. Restore the window from the tray. If the tray host is unavailable, a normal taskbar window remains accessible; losing the tray restores a hidden window. **Quit** or the window's close button exits and attempts standby; close does not mean hide.

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

Appearance → Focus offers Comet, Orbit (two moving points), Pulse (a slow brightness cycle), and Static. Effect color and speed apply live; background GIF timing remains independent. Numeric readings still change atomically at the sensor sampling cadence. The existing 24 FPS generation cap remains; this is not a new physical refresh-rate claim.

Focus background, Clear, and Dimming are available in Appearance → Focus. Custom compositions use independent media layers in Editor. A backdrop sits behind the readings; higher dimming improves legibility. Desktop GIFs accept up to 2000 frames, 4 megapixels per source frame, 300 million cumulative source pixels, and 64 MiB per file. Static images retain the 16 megapixel limit. GIFs above 120 frames use a bounded 12-frame queue automatically; shorter assets use a two-entry decoded-frame cache. These limits do not cap total application memory. Frame delays are clamped to 40 ms–60 s and playback follows elapsed time without increasing output FPS. Initial inspection and seeks may pause; invalid live selections preserve the previous renderer. Clearing/removing media releases its renderer lease.

In Focus appearance or editor typography, **Installed fonts → Refresh** discovers local scalable TTF/OTF faces by family/style through Fontconfig. Choose a face without finding its file manually; bundled Outfit and the custom-file option remain available. Font collections/named instances are omitted until face-index support is implemented. Static fonts keep their own weight. Discovery runs off the UI thread, with a timeout and output/entry limits. If Fontconfig is unavailable, Outfit/custom files still work. The Arch package already depends on Fontconfig. [Fontconfig's fc-list manual](https://xorg.freedesktop.org/archive/X11R7.0/doc/html/fc-list.1.html) describes local font enumeration.

Animation, dimming, and selected font/background paths are saved in the private local preferences file. No source image/font, complete font catalog, or path is uploaded or copied into this repository. Paths are personal information: do not share settings or raw error screenshots unreviewed. JPEG composition removes source metadata, not personal content visible in an image. Installed fonts/media remain untrusted native-decoder inputs; use trusted files and updated dependencies.

Synthetic examples can be generated without USB or sensors:

```bash
PYTHONPATH=src .venv-build/bin/python examples/generate_composition_previews.py --output-dir /tmp/fx240-synthetic-previews
```


## Named compositions

**Appearance** is a unified workspace: Designs on the left, live preview in the center, and contextual properties on the right. Selecting Focus exposes its appearance and typography controls. A single Editor button in the preview header opens the selected design, with layers, draft canvas, and selected-layer properties. New designs are created with New inside the editor. Saved designs hide the Focus-only inspector and give the space to the preview. Settings contains language, startup, and transmission controls. Outside a temporary LCD trial, moving a layer changes only the draft. Choose **Save and show**, or save and select the profile in Designs. Saving changes to an already-active profile updates that profile's output after renderer validation.

Editor retains Studio's sidebar, theme, typography, panels, and output controls. Its workspace has Layers, a circular 240×240 canvas, and Properties. Drag or resize with the mouse, enter exact coordinates, reorder, hide, delete, and undo. The first draft contains the four existing readings and a CPU label, without an arc; local image/GIF, text, and optional CPU-temperature arc layers can be added. Rectangle bounds stay within the square canvas and the circular viewport clips its corners. Long drags retain their pointer grab instead of being taken by the parent scrolling area.

Give the draft a name and use Save, Save copy, or Save and show. Up to eight named compositions are stored in private `profiles.json` beside `settings.json`; names never become filenames. Draft and active profile are restored separately. New/Open ask before replacing an unsaved draft. Delete a profile only after switching away from it in Designs; its draft remains available. Missing assets preserve editable references and prevent invalid previews from being saved/activated. An unavailable startup profile falls back to Focus without deleting the library.

Variable fonts expose a supported weight axis. Static fonts expose their installed styles (Regular/Bold/etc.) instead of a numeric weight control that cannot affect that face; refresh installed fonts to discover variants. Font collection/named-instance support remains limited as documented above. Per-layer fonts, sizes, colors, alignment, opacity, and geometry are stored in each composition. Temperature units/precision and global output settings remain shared.

Bounds: declarative JSON, 24 KiB per scene, at most 16 layers including two media and two arcs; text up to 160 characters; eight profiles and a 256 KiB library. Private preferences are capped at 64 KiB before atomic replacement. Neither file embeds media or executable expressions/QML. Only runtime-validated drafts are autosaved; wait for a valid preview before closing. Files are local references, not portable exported packages. Import/export, weather/clocks, and per-layer rotation are not implemented.

The draft worker has a permanently rejecting USB transport, no device, and output disabled. It uses cached main-session metrics instead of querying sensors again. Closing Editor stops its worker; font faces are cached separately per rendering thread. Cache limits bound cached canvases, not total active-scene or decoder memory. Native LCD editing, complex asset loading during shutdown, and endurance/resource checks remain necessary before release.

Installed-font selectors use a searchable, in-window popup in both application themes. Search filters the local catalog in memory; it does not run a command or send font names elsewhere. File browsing uses the embedded Studio asset picker with the application palette. These interface changes do not establish compatibility with additional hardware or distributions.

Draft-discard and profile-delete confirmations use the Studio theme and translated action labels in the same window. Escape or Cancel preserves an unsaved draft; discarding requires its explicit action.

The window has a minimum size of 1200 × 760 logical pixels to preserve a usable three-column workspace and circular preview. Inspector content reserves scrollbar space, palette items wrap, and narrow sensor cards place frequency below temperature. Qt regression checks cover widths of 1200, 1280, 1440, and 1600 at minimum height, in English/Spanish and both themes. Smaller window layouts are not supported.

Composition actions keep two rows at every supported width: navigation, profile name, Save, and Save and show on the first; New, Save copy, and Delete profile on the second. The name field expands into available space. Layout checks cover both themes and languages without toolbar/canvas overlap.

## Temporary live LCD drafts

In Editor, **Visualize on LCD** sends the validated draft through the existing main sender without saving a named profile. Valid layer edits are coalesced by the 40 ms draft update timer, validated by the draft renderer, then replaced at a main-output frame boundary. During a live trial the editor canvas uses the main sender’s decoded JPEG preview, so it displays the same frame and telemetry sample as output; after returning, it resumes the independent draft preview. It uses the existing configured FPS limit; this is not a new physical refresh-rate claim. A missing device or invalid draft prevents starting. Invalid assets keep the last working output.

**Finish LCD preview** offers Save and apply, Save and return to previous output, Return without saving, or Keep editing live. The dialog includes the profile name. Save/apply failures remain actionable. Draft autosave is separate from named-profile saves. Saving an already-active profile and returning restores the pre-trial scene for the current session; selecting that profile again or restarting loads its saved version.

Navigation away from Editor or ordinary application exit asks for a decision while a trial is active. Stop LCD immediately requests standby and remains paused after the decision. Suspension uses the existing standby/resume path; system shutdown exits without blocking on a dialog. Temporary output settings are never committed to preferences. An ordinary exit that returns to the previous output goes directly to standby, so unavailable old assets cannot prevent closing.

These paths are covered with synthetic transports, including save failures, invalid media, restoration failures and retries, stale frame notifications, paused output, Stop during a queued apply, and close decisions. The owner confirmed initial suspend/resume with both a saved long-GIF profile and a temporary LCD draft on Arch Linux; repeated cycles remain pending. Local media/font references remain private local files; no new network access or executable scene format was added.

## Local asset picker

Image/GIF and manual font-file selection use an in-window Studio dialog, translated and styled for both themes. Shortcuts use existing directories returned by Qt's XDG-aware standard paths; missing and duplicate shortcuts are omitted. Double-click a folder to enter it, enter an absolute local folder path, or filter the current folder by name. Images and fonts use separate extension filters. Hidden files, symlink files, and special files are not listed. Selected content still passes the existing bounded regular-file loaders.

Directory enumeration runs on one background worker, with one coalesced pending navigation request and a 4096-entry visit limit. Stale/cancelled results cannot replace the current folder. No file catalog, navigation history, or shortcut paths are logged or saved; the last folder per type is kept in memory only. This provides no new application network capability; local paths on user-mounted filesystems follow the filesystem's behavior.

For isolated candidate testing, use `gui --config-home /absolute/test/config` and keep the normal `XDG_CONFIG_HOME`. The option isolates Studio preferences, profiles, and its managed autostart entry without hiding the desktop's `user-dirs.dirs` settings from Qt. `XDG_STATE_HOME` may remain isolated for lifecycle diagnostics. Older test commands that override all of `XDG_CONFIG_HOME` can make Qt fall back to nonexistent English folder names on a localized desktop.

## GIF diagnostics

Long-GIF buffering is automatic; no extra playback switch or footer badge is needed. Diagnostics shows queue occupancy/capacity and decoder waits only while the output renderer owns a long-GIF stream. These counters omit filenames and asset paths. A wait includes startup, seeking, or decoding that has not reached the requested frame; it is not a measured physical LCD frame drop. The draft preview uses its own clock and decoder, so its queue is not included in the output counters. See [performance and limits](performance.md#long-gif-playback).
