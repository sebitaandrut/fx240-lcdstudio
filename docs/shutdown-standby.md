# Standby during system shutdown

## Observed failure

On Arch Linux, the owner confirmed automatic login startup after both full PC shutdown/power-on and warm reboot. During system shutdown the LCD kept the final live frame, rather than showing the recreated standby artwork. The reboot made this especially visible. Readings resumed after login. Manual application Quit had previously displayed standby successfully.

The tested original executable is identified in [packaged runtime evidence](packaged-runtime-2026-11-01.json). Its startup success is retained alongside this failed shutdown behavior. The exact desktop termination path was not traced, so the implementation gap is not presented as a proven exclusive root cause.

## First correction

- Listen for logind `PrepareForShutdown` and hold a **shutdown delay** inhibitor, separate from the existing sleep inhibitor. Pause at a frame boundary, let the worker send standby and close HID, then release the inhibitor. If shutdown preparation is canceled, remove only the shutdown pause and preserve any sleep pause or manually paused output.
- Drain the output worker on Qt `commitDataRequest` and `aboutToQuit`. A session checkpoint alone saves preferences without stopping output. Session restoration is marked `RestartNever`; the user's opt-in desktop entry controls automatic startup.
- Handle SIGTERM/SIGINT by setting a flag. A Qt timer dispatches bounded cleanup on the main thread; the signal handler itself performs no USB, disk, or Qt work.
- Request worker termination and wait at most two seconds during terminal cleanup. The same worker release routine sends standby; there is no competing write from the UI thread and no retransmission of incomplete reports. Cleanup is idempotent.
- Show shutdown-inhibitor availability in Diagnostics, in English/Spanish.

The design follows the [logind interface and delay-inhibitor contract](https://www.freedesktop.org/software/systemd/man/latest/org.freedesktop.login1.html), [Qt session-management callbacks](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QGuiApplication.html), and [Qt restart hints](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QSessionManager.html).

## Verification and limits

The full suite passed 100 checks, including five shutdown-specific tests. The corrected frozen executable passed its headless self-test and includes the shutdown module; see [build evidence](shutdown-standby-2026-11-01.json). Automated tests use synthetic readings and a recording transport, not the physical LCD. They check the final standby report bytes, descriptor release after standby, shutdown cancellation, overlapping sleep/shutdown pauses, manually paused output, session checkpoint versus commit, about-to-quit cleanup, unavailable logind fallback, bounded joins, repeated cleanup, and actual SIGTERM delivery to an owned test process. No OS reboot, shutdown, or suspend is initiated by these tests.

The corrected executable passed a native SIGTERM trial with the physical LCD: the owner confirmed updating output, an active shutdown-delay inhibitor in Diagnostics, the standby image after termination, and removal of the tray instance. The owned process exited with code 0. This validates only the signal-driven path. The owner then repeated a real reboot and again saw the last live frame instead of standby. The system-shutdown issue therefore remains failed for this build. An isolated compositor-loss test subsequently reproduced Qt exiting without Python cleanup; see [display-loss investigation and independent fallback](display-loss.md).

This is best-effort shutdown cleanup. SIGKILL, immediate USB power loss, a blocked kernel write, or an exhausted system shutdown deadline can prevent standby. A delay inhibitor is bounded by logind; it does not guarantee an intact USB device or unlimited time. Startup and suspend/resume are separate results. No personal journal dump or process environment is needed for the public summary.
