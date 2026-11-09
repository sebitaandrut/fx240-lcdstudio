# Changelog

## 0.3.0rc3 — release candidate

- Apply typefaces, compatible static styles, and variable font weights to selected text and reading layers in one edit.

Multi-hour playback and repeated lifecycle checks remain part of release candidate validation on Arch Linux x86_64.

## 0.3.0rc2 — release candidate

- Add centered content zoom to effects, text, readings, and gradient layers in the composition editor.
- Add a per-design physical LCD brightness slider to the composition editor, including during live LCD preview.

The owner confirmed brightness changes between saved designs and visible content at level 0 on one FX240 under Arch Linux. Reapplying the selected level after suspend and reboot, and multi-hour playback, remain part of the release candidate validation.

## 0.3.0rc1 — release candidate

- Add editor shortcuts for undo and redo (Ctrl+Z and Ctrl+Y), deleting selected layers (Delete), and moving the selection one LCD pixel at a time (arrow keys).
- Align the draft action with the saved-design controls on wide displays.
- Harden the USB capture comparison and Wayland diagnostic tools.
- Document how to build the Arch package from the release tag. The package CI job builds the exact commit under test.

The default output remains 24 FPS with a 2 ms inter-report delay. Testing on physical hardware is limited to Arch Linux x86_64 and one FX240. Tearing on some moving content remains [under investigation](docs/tearing.md). Multi-hour playback and repeated suspend/resume, reboot, and shutdown checks are pending for this candidate.

## 0.3.0a1 — experimental alpha

- Add Dual, Trace, and Halo alongside Focus. The Designs gallery switches directly between built-in and saved designs, renders thumbnails using synthetic readings, and supports confirmed bulk deletion of saved profiles.
- Open originals as editable copies and keep appearance controls in the composition editor. Add responsive layouts, a direct light/dark toggle, and a wider gallery on large displays.
- Select layers with Shift-click or checkboxes. Move, resize, rotate, recolor, and delete selections with undo, or clear the entire draft after confirmation.
- Add a visual color picker, independent CPU and GPU accents for Dual, and an effects catalog with a temperature arc, Dual arcs, temperature history, radial pulse, segmented ring, and radar sweep.
- Add Aurora, Linear, and Radial gradients without image assets. Save animation speed and temperature precision per design, and edit Celsius/Fahrenheit in temperature-layer properties.
- Add per-layer image and GIF zoom, optional GIF timing matched to output FPS, and reuse unchanged media and fonts across edits.
- Keep the draft visible until the first matching frame is sent during temporary LCD preview. Improve host delivery pacing and keep 24 FPS as the default, with experimental 1–60 host FPS in Advanced settings.
- Keep 2 ms as the default inter-report delay. Add a session-only JPEG 4:2:0 diagnostic option and document the unresolved tearing investigation without publishing private evidence.
- Close to the tray when minimized login startup is enabled. Explicit Quit and lifecycle shutdown retain the standby path.
- Expand Spanish translation coverage and add tests for scene bounds, playback, editor interactions, and wide layouts.

## 0.2.0 — experimental

- Unify Focus and saved designs under Appearance, with responsive panels, themed local file/font pickers, and English/Spanish controls.
- Add a composition editor for movable/resizable text, CPU/GPU readings, images/GIFs, and optional arcs; save up to eight local named profiles.
- Preview unsaved drafts on the LCD and edit live, then explicitly save/apply or return to the previous output.
- Add installed-font selection with real static styles and variable weights, plus Orbit, Pulse, and Static effects.
- Decode desktop GIFs above 120 frames automatically with bounded queues, up to 2000 frames within byte/pixel/work limits. Keep technical buffer counters in Diagnostics.
- Preserve local-only asset references and bounded private settings; validate renderer ownership, replacement, failure, and cleanup.

At the 0.2.0 baseline, the application was capped at 24 FPS. Initial long-GIF playback/resume checks and a 30-minute resource run are limited to Arch Linux and one FX240; they do not establish optical FPS, leak freedom, or compatibility elsewhere. See [validation](docs/validation.md) and [performance](docs/performance.md).

## 0.1.0 — initial experimental baseline

Native Qt/QML Focus dashboard, CPU/GPU telemetry, image/GIF CLI playback, live appearance controls, tray and login startup, standby/lifecycle coordination, local build/Arch packaging, and initial protocol/security documentation.
