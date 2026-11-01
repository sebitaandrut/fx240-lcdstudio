# Roadmap to an initial stable release

The first commit is an experimental baseline, not a stable-release claim. Reports and aggregate benchmark data are part of the repository; personal videos, extracted images, raw USB captures, environments, and local configuration are excluded.

All validation to date is on Arch Linux. Other distributions require their own installation, desktop, sensor, USB, and endurance checks.

## Next milestones

1. **Distributable Linux executable (local build implemented).** The one-file build and headless packaged-runtime check passed on the development Arch Linux x86_64 machine; see [build instructions](building.md). An initial native packaged GUI/USB smoke was subsequently confirmed by the owner. Still required: clean-machine installation and prolonged packaged validation. Build without requiring a user-managed Python environment, bundle QML/fonts/icons and required runtime libraries, validate startup/CLI/GUI in an isolated environment, and document architecture/distribution limits. Freezing an interpreter is distinct from compiling all application logic to native machine code. A build on one distribution does not establish portability to every Linux distribution.
2. **Login startup and minimized operation (implementation added).** Managed-entry generation, opt-in UI, and tray fallback have automated checks. A manual packaged minimized relaunch, output recovery, standby on close, and preference preservation were confirmed; one full host shutdown/startup/login trial was subsequently reported successful on Arch Linux. Warm reboot and repeated trials remain pending. Add an opt-in desktop-session autostart entry with an explicit background startup mode, preserve the existing settings file, and keep the window accessible when a tray host is unavailable. Verify both startup configuration and a real logout/login or reboot. A desktop GUI starts after graphical login, not before login as a system service.
3. **Longer endurance testing.** Repeat native USB runs for one hour and several hours, record visibility/monitor-power context, exercise live settings and tray restoration, and validate graceful exit. Keep suspend/resume, repeated host startup, verified device power-on initialization, USB reconnection, clean installation, and additional hardware as separate gates.
4. **Comet thickness.** Add an independent live/persistent thickness control with matching rounded head/tail geometry, circular clipping checks, and physical evaluation. Do not conflate stroke width with animation speed or USB frame rate.
5. **Additional animations.** Introduce interchangeable time-based animation strategies with shared color, timing, telemetry, and transport infrastructure. Compare rendering cost and LCD legibility before selecting defaults.
6. **On-demand content editor.** Start with a versioned scene model for image/GIF layers, text, and sensor fields; separate media loading, layout, animation, and output. Add safe circular bounds, preview, persistent scene files, and then editing controls. Existing CLI image/GIF support does not mean a desktop editor already exists.

## Release gates

- Repeatable installation or packaged startup without modifying system Python.
- Preferences survive full process restart and graphical-session startup.
- No inaccessible hidden process when the tray is missing or disappears.
- Native long-run results and error recovery documented without treating host/Qt updates as optical LCD FPS.
- Personal-file inventory, third-party notices, and GPLv3-or-later license and bundled-runtime obligations reviewed before publication.
- CI results on the public repository before calling the initial release stable.

Commit each coherent implementation and its relevant validation separately after the baseline. Do not reconstruct fictional earlier commits. Publishing the repository still requires the owner's confirmation.
