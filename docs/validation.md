# Validation status

**Scope:** Arch Linux x86_64, one FX240. Other distributions, hardware revisions, and clean-machine installation are untested. This is an experimental baseline. The [aggregate evidence](evidence.json) retains the measurements supporting these statements; exploratory reports and visual tuning steps are omitted from the current documentation.

## What has been checked

| Area | Result and scope |
| --- | --- |
| Automated checks | 113 tests passed on the current 8 px source with desktop dependencies installed. Synthetic transports and sensors do not establish hardware behavior. |
| HID packets | Prototype comparison matched 240 frames; a controlled two-frame USB capture matched 24 expected reports exactly. |
| Physical content | Images, GIF movement/counter, circular telemetry layout, CPU/GPU target agreement, live edits, Outfit, and the 8 px arc/comet were confirmed visually. |
| Packaged application | Frozen GUI/USB smoke passed on the development machine. The 8 px executable also passed a no-USB self-test. |
| Repository build | A fresh public clone, empty Python environment, uncached dependencies, install, build, and standalone self-test passed on the existing Arch host. The `arch-build` CI job checks the user recipe in a minimal Arch container; neither case establishes a clean native desktop/VM or physical USB installation. |
| Arch package | Build/install/self-test/removal passed in clean Arch CI. Native operation with fresh settings, a warm reboot, and suspend/resume with active and manually paused output passed initial owner checks. Repeated cycles and full shutdown with this package remain pending. |
| Preferences and tray | Restarted/minimized operation and saved settings passed initial owner checks. |
| Reboot and full shutdown | One warm reboot and one full shutdown/power-on passed standby with the desktop-autostarted instance; traces corroborated output release and cleanup. These lifecycle trials preceded the visual-only 8 px rebuild. |
| FPS and resources | The application remains capped at 24 FPS. Experimental host/optical trials and a ten-minute USB run are summarized in [performance](performance.md). |
| Publication checks | Source/history/archive candidate scans and dependency metadata were reviewed; this is not a formal security audit. [GitHub Actions passed](https://github.com/sebitaandrut/fx240-lcdstudio/actions/runs/41365473570) for Python 3.11/3.13 core jobs and a Python 3.13 offscreen Qt/QML job on Ubuntu runners; this is software CI, not Ubuntu hardware validation. |

## Lifecycle limits

Reboot trials launched from the development environment failed standby; the same shutdown build passed when left running from desktop autostart. Launch ownership correlates with the difference, but its exact termination mechanism is unproven. For repeatable desktop tests, use the autostarted instance instead of relaunching from a development terminal. One successful trial of each operation does not establish reliability across all sessions.

The worker is asked to pause on logind shutdown preparation, with a bounded wait for standby/output release before preferences are saved. Qt exit and signal handlers provide orderly cleanup; a small headless process forked before Qt attempts standby after unexpected GUI loss. Normal worker completion disarms it. Physical standby after loss of an owned virtual display and a private simulated logind notification also passed; neither test alone was counted as an OS reboot pass.

GUI mode keeps a bounded private event trace at `$XDG_STATE_HOME/fx240-linux/shutdown.jsonl`, defaulting to `~/.local/state/fx240-linux/shutdown.jsonl`. It contains only allowlisted event codes and relative seconds, with mode 0600 and an approximately 64 KiB limit. It contains no selected device, sensor value, identifier, or arbitrary error text. Output release is not optical proof; the hardware confirmations above are separate observations.

No removal of USB standby power or complete loss of device state was verified. Initial packaged suspend/resume checks with active output and manually paused output are owner-reported; the paused LCD remained in standby after wake. The trace does not independently identify the OS sleep event. Repeated suspend cycles, reconnect recovery, and multi-hour stability remain unverified.

## Repeat software checks

```bash
python3 -m venv .venv
.venv/bin/python -m pip install '.[desktop]'
.venv/bin/python -m unittest discover -s tests -v
```

Without the desktop extra, optional Qt checks may be skipped. For a built executable, `./dist/fx240-lcd-studio self-test` loads the QML/assets with synthetic readings and never opens USB or saves preferences. It does not replace native-desktop or hardware tests.

## Remaining stable-release checks

- Repeated suspend/resume cycles, including a manually paused LCD that must stay paused after wake.
- One-hour and multi-hour native runs with real USB/sensors, live edits, tray use, and monitor visibility recorded.
- Repeated reboot/shutdown using the final executable, plus device reconnection and error recovery.
- Clean installation/build and additional hardware/distributions; keep software CI passing.
- Exact-source publication review and dependency/license review for any binary release.

Record host timing, USB completion, Qt presentation proxies, and physical observation separately. Keep raw captures, videos, screenshots, local settings, and native logs private unless explicitly reviewed for sharing.
