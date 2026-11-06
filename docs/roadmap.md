# Roadmap

The current code is an experimental baseline. See [validation](validation.md) for what is actually checked; all hardware results are limited to Arch Linux and one FX240.

## Before an initial stable release

- Repeated reboot/shutdown and suspend/resume, including paused output and inaccessible/missing tray cases.
- One-hour and multi-hour native USB/resource runs, with live settings and monitor visibility recorded.
- Reconnection/error recovery and clean-machine build/installation; keep the now-passing public CI green.
- Additional distribution/hardware checks before extending compatibility claims.
- Final source privacy review and dependency/notice review before binary redistribution.

## Planned features

- A live, persistent stroke-width control; the approved current base is **8 LCD pixels**.
- Additional animation styles and a Dual CPU/GPU layout.
- Profile import/export with explicit asset/privacy boundaries.

The desktop editor, local named profiles, and bounded long-GIF playback are implemented. Keep each feature separate from transport and sensor sampling, and measure its rendering cost before selecting defaults.

## External data and extensions

A future weather/data provider should use explicit user configuration, bounded validated values, caching, timeouts, and an opt-in network boundary. Manual city selection avoids automatic location discovery; any remote request still reveals information to the provider, including the requested city and connection IP. Profiles should contain presentation and provider identifiers, not executable code or secrets.

User scripts are a separate design question: a separate process and timeout alone are not a sandbox. Before enabling arbitrary code, define filesystem/network permissions, resource limits, consent, and a versioned data-only result schema. Do not execute scripts, QML, shell commands, or downloaded templates from scene/profile content. These are future proposals, not implemented capabilities.
