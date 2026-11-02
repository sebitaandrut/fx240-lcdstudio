![FX240 LCD STUDIO](docs/assets/banners/b-stacked.png)

An experimental native Linux application for the **ID-COOLING FX240 LCD**, built with Python, PySide6, and QML. Show CPU/GPU telemetry and customize the display without the manufacturer's Windows software.

**Tested on Arch Linux x86_64 only, with one FX240.** This unofficial project controls the LCD, not the pump, fans, or RGB. Other distributions, hardware revisions, and clean-machine installation remain unverified.

## Features

- Focus dashboard with CPU/GPU temperatures and frequencies, Outfit typography, and an animated comet.
- Live colors, rainbow effect, animation speed, fonts, precision, and Celsius/Fahrenheit.
- Dark/light interface, English/Spanish, saved settings, tray support, and opt-in login startup.
- Image/GIF playback and telemetry overlays through the CLI. A desktop editor is planned.
- A locally built executable that runs without an activated Python environment.

Sensor support depends on Linux drivers; unavailable readings show `N/A`. Proprietary NVIDIA/NVML support is not implemented.

## Get started

With Python 3.11+ and the native Qt libraries available, run from the source directory:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install '.[desktop]'
.venv/bin/fx240 gui
```

The GUI starts preview and physical output automatically when one matching LCD is accessible. Close other senders first. **Stop display** leaves a recreated standby image while the preview continues. For a pacman-managed Arch installation, use the [PKGBUILD instructions](docs/building.md#install-with-pacman-using-pkgbuild). The same guide covers native dependencies, USB permissions, and manual executable builds.

## Status

This is an **experimental baseline**, not a stable release. The application is capped at **24 FPS**; higher host throughput is not proof of complete physical LCD frames. Packaged operation and desktop-autostarted reboot/shutdown passed initial hardware checks. Suspend/resume, prolonged stability, repeated lifecycle trials, and clean installation remain pending. See [validation and limits](docs/validation.md).

## Documentation

| Topic | Guide |
| --- | --- |
| Dependencies and executable builds | [Build locally](docs/building.md) |
| GUI controls, sensors, preferences, and CLI | [Usage](docs/desktop.md) |
| HID framing and reverse engineering | [Protocol](docs/protocol.md) |
| Tested behavior and remaining checks | [Validation](docs/validation.md) |
| FPS, resource measurements, and evidence limits | [Performance](docs/performance.md) |
| Privacy and publication boundaries | [Privacy review](docs/privacy-review.md) |
| Planned work | [Roadmap](docs/roadmap.md) |

For code structure, tests, and commit conventions, see [Contributing](CONTRIBUTING.md). Code, documentation, and commits are in English. Development combined **AI assistance** with hands-on hardware testing.

Licensed under **GPLv3 or later**. See [LICENSE](LICENSE) and [third-party notices](NOTICE.md). Bundled dependencies retain their own licenses; public binary releases require a dependency/notice review.
