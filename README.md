![FX240 LCD STUDIO](docs/assets/banners/b-stacked.png)

An experimental native Linux application for the **ID-COOLING FX240 LCD**, built with Python, PySide6, and QML. Display CPU/GPU telemetry and customize your LCD without the manufacturer's Windows software.

**Tested on Arch Linux x86_64 only, with one FX240.** Other distributions, hardware revisions, and clean-machine installation remain unverified. This is unofficial software with no affiliation with ID-COOLING. It controls the LCD only, not the pump, fans, or RGB.

## What works today

- **Focus dashboard:** CPU/GPU temperatures and frequencies, a circular layout, and an animated comet.
- **Live customization:** colors, rainbow comet, animation speed, fonts, and Celsius/Fahrenheit.
- **Desktop app:** dark/light themes, English/Spanish, saved preferences, and system tray support.
- **Image/GIF playback and telemetry overlays through the CLI.** A desktop content editor is planned.
- **Local executable builds** and opt-in minimized startup after graphical login. Automatic startup was reported successful after full shutdown and warm reboot on Arch Linux; shutdown standby and suspend/resume need further validation.

Sensor availability depends on the hardware and driver. Unsupported readings show `N/A`; proprietary NVIDIA/NVML support is not implemented.

## Get started

From the source directory, with Python 3.11+ and the native Qt desktop libraries available:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install '.[desktop]'
.venv/bin/fx240 gui
```

The GUI automatically sends to a uniquely identified FX240 when permissions allow. Close other LCD senders first. Without a usable device, the preview remains available. **Stop display** pauses physical output while keeping the preview active.

For native dependencies, recorded build versions, and an executable that runs without activating Python, follow the **[local build guide](docs/building.md)**. It includes a headless `self-test` that never transmits to USB. Python 3.14.9 was used for the packaged build; the declared source minimum is not a claim that every packaging configuration has been tested.

## Validation status

The application retains its conservative **24 FPS** default and cap. Short experimental instruments achieved higher host throughput; this does **not** establish the same number of complete physical LCD frames per second. A ten-minute USB trial completed without reported output errors; longer endurance tests remain pending.

The [performance and optical report](docs/benchmarks/2026-11-01/README.md) documents results, failed attempts, and evidence limits. Private videos, photos, raw USB captures, and local configuration are excluded from the repository.

## Documentation

| Topic | Guide |
| --- | --- |
| Dependencies and executable builds | [Build locally](docs/building.md) |
| GUI, preferences, tray, and controls | [Desktop guide](docs/desktop.md) |
| Boot/login, endurance, and suspend trials | [Next hardware validation](docs/lifecycle-validation.md) |
| HID protocol and reverse engineering | [Observed protocol](docs/protocol.md) |
| Hardware trials and validation history | [Hardware trials](docs/hardware-trials.md) · [Validation](docs/validation.md) |
| Performance and resource use | [Measurements](docs/benchmarks/2026-11-01/README.md) · [Profiling](docs/performance.md) |
| CLI examples and implementation details | [Development notes](docs/development-notes.md) |
| Publication privacy review | [Scope, findings, and repeatable checks](docs/privacy-review.md) |
| Next milestones | [Roadmap](docs/roadmap.md) |

## Development

Application code is in `src/fx240/`, automated checks in `tests/`, measurement/build tools in `tools/`, and executable build inputs in `packaging/`. QML, rendering, telemetry, and USB transport have separate responsibilities. See [architecture](docs/development-notes.md#architecture) and [contribution conventions](CONTRIBUTING.md).

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Code, documentation, and commits are maintained in English. The project was developed with AI assistance alongside hands-on hardware tests; its claims are limited to the recorded evidence.

## Project status and licensing

This is an **experimental baseline**, not a stable release. The packaged native GUI and LCD passed an initial visual smoke. Automatic startup passed owner trials after full shutdown and warm reboot. System shutdown still failed to show standby after the signal-based correction. A [display-independent fallback](docs/display-loss.md) passed Wayland-loss tests with simulated transport and the physical LCD; but subsequently failed standby during an actual reboot. A follow-up drains output inside shutdown preparation and passed a simulated notification with the physical LCD, but a manually launched actual reboot still failed. Shutdown remains unresolved. Suspend/resume, prolonged runs, and clean-machine installation remain release gates. GitHub CI is prepared but has not run yet.

Licensed under **GPLv3 or later**: you may use, modify, and redistribute the original project under its terms. See [LICENSE](LICENSE) and [third-party notices](NOTICE.md). Bundled dependencies retain their own licenses; public binary redistribution still requires a complete dependency/notice review.
