# Boot, endurance, and suspend/resume validation

**Status: one full host shutdown/startup and graphical-login trial reported successful by the owner. Warm reboot, prolonged operation, and physical suspend/resume remain pending. Arch Linux only.** Run these trials with the packaged executable as a separate validation target; source tests do not establish packaged hardware behavior.

## Completed preflight

The owner confirmed that the packaged native GUI opens, updates the preview and physical LCD, and closes normally with the recreated standby frame. The managed login entry passed desktop-file validation and points to the current executable with `gui --start-minimized`. Its configuration and preference file were checked locally without publishing their paths or contents. A manual minimized relaunch was confirmed to start in the tray, resume LCD output, allow tray restoration, and preserve theme, accent, and comet speed. The initial process exited with code 0.

These are preflight results, **not** an actual boot/login or suspend pass. See [packaged runtime evidence](packaged-runtime-2026-11-01.json). A subsequent full shutdown/startup result is recorded below; the next planned physical phase is Trial B.

## Full shutdown/startup result — 2026-11-01

The owner performed a complete PC shutdown and power-on instead of the requested warm reboot, then reported that it worked perfectly. The preceding checklist covered automatic tray startup without manually launching Studio, updating LCD readings, and restored theme/accent/comet speed. This is recorded as one overall user-confirmed pass; individual checklist answers and an independent process/resource capture were not obtained for this boot.

This verifies the observed host shutdown/startup/login workflow on this Arch Linux machine. It does not establish that USB standby power was removed, that the LCD lost all state, or that prior vendor initialization is unnecessary. No AC disconnection or internal cable manipulation is required for the next trials. Warm reboot remains a separate unchecked case. See [structured evidence](packaged-runtime-2026-11-01.json).

## Preparation

1. Finish and verify a local build using [the build guide](building.md). Keep its executable in a stable directory and record its SHA-256, application commit, Python/Qt versions, session type, target FPS, JPEG quality, and report delay. Keep raw logs and local paths private.
2. Close other LCD sender processes, including tray instances. Start one Studio instance from the terminal. Confirm physical output and the four sensor targets before testing automatic startup.
3. Make a recognizable preference change: application theme/language, LCD accent, comet speed, and temperature unit. Close Studio normally, launch it again without overriding CLI settings, and verify every selection is restored.
4. Enable **Settings → Start at login → Minimized in tray**. Verify that restoring from the tray works. With no supported tray host, confirm the minimized taskbar window remains accessible. Startup must remain opt-in.

## Trial A: boot and graphical login

Save unrelated work, close Studio normally, and reboot manually when ready. The trial begins after graphical login: this is a desktop application, not a pre-login system service.

Record these observations without publishing a screenshot of the desktop:

- Studio starts without a terminal, Python environment activation, or manual intervention.
- Exactly one instance is running; one tray icon appears when the desktop provides a tray.
- LCD output begins and the displayed readings update.
- Restoring the window works, all chosen preferences remain, and Diagnostics has no output error.
- If device permissions/discovery fail, an accessible window and useful error remain available.

Repeat as a second, separate trial after a full power-off/startup. This cold-boot test also checks whether the device relies on earlier vendor-software initialization. Do not infer cold-boot success from a warm restart.

## Trial B: normal workload and endurance

Use the conservative application profile first: 24 FPS, quality 65, 2 ms report delay. Run for one hour, then extend to several hours after reviewing the result. Avoid changing timing settings during the initial steady phase.

At startup, after warmup, and every 10–15 minutes, record process RSS, CPU (with its percentage convention), descriptor/thread counts if available, output errors, and whether the window is visible, in the tray, or the monitor is locked/off. Note desktop workload changes separately. CPU/RSS readings from a desktop system monitor are adequate for the first manual screen; do not mistake them for a controlled benchmark.

Restore the UI periodically, compare LCD TARGET against the physical screen, and verify animation and current readings. Lack of Qt window swaps while hidden or with the monitor off is not alone an LCD failure. A stable RSS interval is evidence for that run, not proof of no memory leak.

## Trial C: suspend and resume

After a successful baseline interval, use the desktop's normal Suspend action. Do not trigger suspension automatically during an unattended test or while unrelated work is unsaved.

1. Confirm Diagnostics reports whether the logind delay inhibitor is available.
2. With physical output active, suspend. If visibly observable before sleep, note whether the recreated standby frame appears; otherwise mark that observation unavailable.
3. Resume and unlock. Check LCD animation, current readings, restored UI/tray access, and any errors. Time the return of output. Check again after two minutes.
4. Repeat at least three cycles, with a short and a longer sleep interval. Record every attempt, including failures.
5. Separately pause physical output with **Stop display**, suspend, and resume. Output should remain paused, while preview/telemetry resume. Then use **Start display** and verify recovery.
6. Close Studio normally after the final cycle. Verify the standby frame and process termination.

A delay inhibitor limits best-effort shutdown time; it does not guarantee that USB survives suspend. If a device disappears/reappears or an output error occurs, retain the failure, record whether manual Start display recovers, and investigate before adding retries. Do not silently restart the application and count that as automatic recovery.

## Private trial record

Keep the raw record outside the repository. Use a simple table:

| Trial / cycle | Elapsed time | Window / monitor state | LCD output | Preferences | RSS / CPU | Errors / recovery | Outcome |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Example only | — | — | — | — | — | — | Not run |

Use relative elapsed times and generic hardware descriptions in public summaries. Exclude login names, hostnames, home-directory paths, IP/MAC addresses, serials, machine/boot IDs, full process environments, personal screenshots, and unreviewed journal dumps. Retain only reviewed aggregate measurements and observations in the eventual public report.

## Pass criteria and limits

Each case needs a recorded result, not just an absence of a crash: one-instance login startup, preference restoration, accessible tray/taskbar behavior, continuing LCD data, repeatable resume, paused-state preservation, and orderly exit. A failure blocks a stable-release claim for that case, not publication of an honestly labeled experimental source baseline. Other distributions remain untested.
