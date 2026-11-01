# Roadmap

The current code is an experimental baseline. See [validation](validation.md) for what is actually checked; all hardware results are limited to Arch Linux and one FX240.

## Before an initial stable release

- Repeated reboot/shutdown and suspend/resume, including paused output and inaccessible/missing tray cases.
- One-hour and multi-hour native USB/resource runs, with live settings and monitor visibility recorded.
- Reconnection/error recovery, clean-machine build/installation, and public CI.
- Additional distribution/hardware checks before extending compatibility claims.
- Final source privacy review and dependency/notice review before binary redistribution.

## Planned features

- A live, persistent stroke-width control; the approved current base is **8 LCD pixels**.
- Additional time-based animations and a Dual CPU/GPU layout.
- Named profiles.
- A scene model and on-demand editor for image/GIF layers, text, and sensor fields, with circular safe bounds and persistent scene files.

Image/GIF playback already exists through the CLI; the desktop editor does not. Keep each feature separate from transport and sensor sampling, and measure its rendering cost before selecting defaults.
