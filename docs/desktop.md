# Using FX240 LCD STUDIO

Install `.[desktop]` and run `fx240 gui`, or open your locally built executable. See [building](building.md) for dependencies and packaging. Qt is optional for CLI media playback; the GUI uses PySide6 and QML.

## Display and live settings

The preview starts automatically. Physical output also starts when exactly one matching LCD is accessible, or an explicit device is selected. No match or ambiguous discovery leaves preview available. The transport validates the device identity and takes a cooperative exclusive lock.

- **Stop display** finishes the current frame, attempts one recreated standby image, and releases USB. Preview and sensor sampling continue.
- **Start display** resumes output using the current settings.
- Appearance controls change the accent, rainbow/accent comet, speed, temperature unit, and decimal precision live. The base arc/comet stroke is 8 LCD pixels, with rounded ends.
- Settings contains language, transmission preset, font file, and font weight. Advanced settings adds device, FPS, JPEG quality, and report delay. Information icons explain the controls.
- Edits apply between complete frames after a short debounce. Invalid edits keep the last working configuration. Pause physical output before changing devices.

Outfit is bundled under its upstream license; no global font installation is required. Comet speed ranges from 0.25× to 3×, independently of sensor sampling and FPS. The application supports Focus; Dual and a desktop content editor are planned.

## Sensors and diagnostics

One sensor snapshot feeds the rendered frame and diagnostics. Sensors are normally sampled once per second; animation can run at 24 FPS. Stable readings, driver cadence, and display rounding can leave a number unchanged. Numbers switch directly to the new sample; only the decorative arc interpolates.

**RAW SAMPLE** shows the provider value and source unit. **LCD TARGET** shows its display formatting. The preview is the encoded JPEG decoded back to upright orientation; completed writes do not prove immediate physical presentation. CPU/GPU summaries and target values use the same snapshot. Missing sensors show `N/A` rather than a retained old value.

Fahrenheit is converted from the original Celsius sample before rounding. Raw diagnostics and arc scaling remain Celsius. Sensor names and paths preserve driver distinctions such as CPU Tctl, GPU edge, and individual CPUFreq policies; they are not interchangeable measurements. Review sensor paths and error details before sharing screenshots.

## Preferences and language

English/Spanish and dark/light appearance switch live. Render and interface settings persist in `$XDG_CONFIG_HOME/fx240-linux/settings.json`, defaulting to `~/.config/fx240-linux/settings.json`. Writes are validated, debounced, atomic, and private to the user. Corrupt fields fall back with an explanatory notice. A custom font path remains in this local file.

The selected device path, sensor samples, and sending/paused state are not saved. Explicit CLI options override the corresponding saved GUI fields. Named profiles are not implemented.

## Tray, login, and standby

Minimize or **Hide to tray** keeps rendering and physical output active. Restore the window from the tray. If the tray host is unavailable, a normal taskbar window remains accessible; losing the tray restores a hidden window. **Quit** or the window's close button exits and attempts standby; close does not mean hide.

Enable **Settings → Start at login → Minimized in tray** to install a per-user desktop autostart entry. Keep the executable/environment in a permanent location. It starts after graphical login, not before login. Disable and re-enable startup if the executable moves.

Standby is artwork recreated in code, not a recovered vendor bitmap or firmware reset. The application coordinates logind shutdown/sleep preparation and uses a separate fallback for abrupt graphical connection loss. Power loss, forced termination, a blocked driver, or another sender can prevent standby. Reboot/shutdown passed initial trials with desktop autostart; development-launched instances failed during reboot. An initial packaged suspend/resume success was owner-reported; repeated cycles, the manually paused case, and automatic recovery after USB errors remain unverified. See [validation](validation.md).

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
