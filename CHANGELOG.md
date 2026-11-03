# Changelog

## 0.2.0 — experimental

- Unify Focus and saved designs under Appearance, with responsive panels, themed local file/font pickers, and English/Spanish controls.
- Add a composition editor for movable/resizable text, CPU/GPU readings, images/GIFs, and optional arcs; save up to eight local named profiles.
- Preview unsaved drafts on the LCD and edit live, then explicitly save/apply or return to the previous output.
- Add installed-font selection with real static styles and variable weights, plus Orbit, Pulse, and Static effects.
- Decode desktop GIFs above 120 frames automatically with bounded queues, up to 2000 frames within byte/pixel/work limits. Keep technical buffer counters in Diagnostics.
- Preserve local-only asset references and bounded private settings; validate renderer ownership, replacement, failure, and cleanup.

The application remains experimental and capped at 24 FPS. Initial long-GIF playback/resume checks and a 30-minute resource run are limited to Arch Linux and one FX240; they do not establish optical FPS, leak freedom, or compatibility elsewhere. See [validation](docs/validation.md) and [performance](docs/performance.md).

## 0.1.0 — initial experimental baseline

Native Qt/QML Focus dashboard, CPU/GPU telemetry, image/GIF CLI playback, live appearance controls, tray and login startup, standby/lifecycle coordination, local build/Arch packaging, and initial protocol/security documentation.
