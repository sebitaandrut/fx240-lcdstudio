# Boot, endurance, and suspend/resume validation

**Status: automatic startup after full host shutdown and warm reboot was reported successful. The owner observed missing standby on both system shutdown paths; the signal-based correction passed physical SIGTERM standby but failed a subsequent real reboot. The display-independent fallback passed an owned-screen-loss test with the physical LCD; a subsequent real reboot still retained the live frame. A bounded drain inside shutdown preparation is now being tested. Endurance and suspend/resume remain pending. Arch Linux only.** Run these trials with the packaged executable as a separate validation target; source tests do not establish packaged hardware behavior.

## Completed preflight

The owner confirmed that the packaged native GUI opens, updates the preview and physical LCD, and closes normally with the recreated standby frame. The managed login entry passed desktop-file validation and points to the current executable with `gui --start-minimized`. Its configuration and preference file were checked locally without publishing their paths or contents. A manual minimized relaunch was confirmed to start in the tray, resume LCD output, allow tray restoration, and preserve theme, accent, and comet speed. The initial process exited with code 0.

These are preflight results, **not** an actual boot/login or suspend pass. See [packaged runtime evidence](packaged-runtime-2026-11-01.json). A subsequent full shutdown/startup result is recorded below; the next planned physical phase is Trial B.

## Full shutdown/startup result — 2026-11-01

The owner performed a complete PC shutdown and power-on instead of the requested warm reboot, then reported that it worked perfectly. The preceding checklist covered automatic tray startup without manually launching Studio, updating LCD readings, and restored theme/accent/comet speed. This is recorded as one overall user-confirmed pass; individual checklist answers and an independent process/resource capture were not obtained for this boot.

This verifies the observed host shutdown/startup/login workflow on this Arch Linux machine. It does not establish that USB standby power was removed, that the LCD lost all state, or that prior vendor initialization is unnecessary. No AC disconnection or internal cable manipulation is required for the next trials. A subsequent warm reboot also started correctly; see the shutdown failure below. See [structured evidence](packaged-runtime-2026-11-01.json).

## Warm reboot and shutdown standby failure — 2026-11-01

The owner also confirmed automatic startup after a warm reboot. In both the reboot and full shutdown cases, the LCD retained the last transmitted live frame instead of showing standby; this was more visible on reboot. Updating output resumed after login. This refines the earlier overall success report: startup passed, while standby at system shutdown did not. Manual Quit had previously returned the LCD to standby successfully.

The original build handled manual exit and sleep preparation but did not explicitly subscribe to shutdown preparation or handle Unix termination signals. That is an implementation gap consistent with the symptom, not an independently traced proof of which shutdown path the desktop used. The correction adds logind shutdown preparation with a separate delay inhibitor, desktop session callbacks, termination handling, and bounded worker cleanup. See [shutdown design and verification](shutdown-standby.md). A subsequent owned-process SIGTERM test with the corrected executable returned exit code 0; the owner confirmed the standby image and closed tray instance, with the shutdown delay inhibitor active beforehand. The owner then repeated desktop reboot with that executable and again observed no standby. That attempt is failed; [the next investigation](display-loss.md) reproduced a Wayland-loss cleanup bypass without rebooting the PC. The subsequent frozen-executable test with the real LCD also passed standby after losing only the owned virtual screen. The owner then repeated actual OS reboot and still saw the final live frame: this result failed. The trace recorded shutdown preparation without cleanup completion; see the follow-up in [the display-loss investigation](display-loss.md).

## Preparation

1. Finish and verify a local build using [the build guide](building.md). Keep its executable in a stable directory and record its SHA-256, application commit, Python/Qt versions, session type, target FPS, JPEG quality, and report delay. Keep raw logs and local paths private.
2. Close other LCD sender processes, including tray instances. Start one Studio instance from the terminal. Confirm physical output and the four sensor targets before testing automatic startup.
3. Make a recognizable preference change: application theme/language, LCD accent, comet speed, and temperature unit. Close Studio normally, launch it again without overriding CLI settings, and verify every selection is restored.
4. Enable **Settings → Start at login → Minimized in tray**. Verify that restoring from the tray works. With no supported tray host, confirm the minimized taskbar window remains accessible. Startup must remain opt-in.

## Trial A: boot and graphical login

Save unrelated work, close Studio normally, and reboot manually when ready. The trial begins after graphical login: this is a desktop application, not a pre-login system service.

Record these observations without publishing a screenshot of the desktop:

- Studio starts without a terminal, Python environment activation, or manual intervention.
- Exactly one logical application instance is running; one tray icon appears when the desktop provides a tray. A frozen launcher, GUI, and standby helper may appear as multiple OS processes for that single instance.
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
