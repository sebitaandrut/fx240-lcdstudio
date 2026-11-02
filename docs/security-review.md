# CodeQL alert review — 2026-11-02

Scope: all 21 open alerts on `5b6e65a89a184d09da0ba598cd5faeda7fa1288c`, plus findings raised by the follow-up analysis. This is a maintainer code review with synthetic regression tests, not an independent audit or a guarantee of security.

## Trust boundary and corrections

This is a normal-user local desktop/CLI application, not a privileged service accepting paths or commands from remote clients. CLI file selection, XDG directory overrides, and the optional test harness output directory are intentional caller-controlled inputs. A caller selecting their own path is not by itself traversal across a trust boundary. Do not run the application as root or expose these interfaces through a network service. Parent directories and the launching user's environment are trusted; these controls do not isolate the app from an attacker already controlling that account.

The review nevertheless found concrete special-file handling weaknesses. Preferences and autostart could block reading a FIFO; a saved font could reach the font decoder as a FIFO; media checked a pathname before reopening it, leaving a replacement race; the lifecycle trace could chmod/append to a hard-linked regular file. These cases are corrected:

- Local input reads reject leaf symlinks and special files, open with `O_NONBLOCK`, `O_NOFOLLOW`, and `O_CLOEXEC`, then recheck the descriptor's file type. Reads are bounded even if a file grows after its initial size check.
- Preferences/autostart require the opened file to belong to the current user with one hard link. Existing invalid startup entries are preserved. Preference failures fall back with a visible warning.
- Media is decoded from a bounded in-memory snapshot (64 MiB); fonts likewise use a bounded snapshot (16 MiB). Image pixel/frame limits remain. This is not a native decoder sandbox.
- Lifecycle output rejects foreign-owned or multiply linked descriptors before changing permissions or writing. Symlink rejection, regular-file validation, the size cap, and fixed event schema remain.

Inputs that are symlinks must now be selected by their actual regular-file path. Config/state parent directories can still be relocated by the local user; no arbitrary home-directory restriction was added to silence CodeQL.

## Decisions for the original alerts

The table classifies the reported injection/traversal claim after examining the source and sink. The additional weaknesses above were fixed rather than ignored. GitHub dismissal comments link this rationale; obsolete locations may instead close automatically after analysis.

| Alert | Reviewed operation and decision |
| --- | --- |
| #17 | Offline `tshark` invocation: false positive for command injection. No shell; one absolute capture filename argument; fixed option/field names; USB address validated as integer 1–127; executable comes from the caller's trusted PATH. Metacharacters and option-like filenames are tested. Capture content still requires an up-to-date trusted tshark installation. |
| #18 | Capture path resolution: intentional explicit local input, not a service-controlled path. No extraction or constructed child path. |
| #19 | Capture regular-file check: intentional local input; it does not write the selected file. |
| #20 | Media regular-file check: intentional selected input; replaced with bounded descriptor-validated reading to address special-file/replacement concerns. |
| #21 | Media size check: same explicit input; size and actual bytes are now bounded on the opened file/snapshot. |
| #22 | Preference read: fixed application filename under local configuration or explicit caller path; bounded/private regular-file checks now reject special files, leaf symlinks, and hard links. |
| #11 | Preference parent creation: fixed app filename under caller-selected configuration; no remote/less-privileged input source. |
| #12 | Preference temporary creation: exclusive random file in the same caller-selected directory, atomic replacement, private mode. No attacker-selected temporary basename. |
| #13 | Preference temporary cleanup: only the generated temporary filename is removed; no arbitrary input filename is deleted. |
| #1 | Autostart symlink check: defensive validation of the fixed managed entry, now descriptor-validated reading. |
| #2 | Autostart entry read: same fixed managed entry; now bounded/private regular-file reading. |
| #3 | Autostart existence check: same local configuration choice, not concatenation of an untrusted entry name. |
| #4 | Autostart temporary creation: exclusive random temporary file in the entry directory, followed by atomic replacement. Desktop Exec arguments are escaped and never passed through a shell by this code. |
| #5 | Autostart parent creation: fixed `autostart` directory below explicit/user XDG configuration. |
| #6 | Autostart disable/unlink: deletes only the fixed managed entry after validating its ownership marker; does not follow a leaf symlink. |
| #7 | Autostart temporary cleanup: only the generated temporary filename, not an input-selected file. |
| #8 | Trace parent creation: fixed app state subdirectory or explicit synthetic-test path; caller-owned environment, no remote source. |
| #9 | Trace open: fixed log filename, no-follow/nonblocking flags and descriptor validation; ownership/link checks added before chmod/write. |
| #14 | HID open: anchored full match `/dev/hidraw[0-9]+` before open; no-follow, character-device and USB identity checks, then exclusive cooperative lock before any report. Negative path/identity tests cover this boundary. No arbitrary filesystem path or unrelated character-device selection is accepted. |
| #15 | Synthetic Wayland client log: fixed basename below the optional harness's explicitly chosen output directory; only synthetic events, no real HID implementation. Local artifact output is the purpose of this helper. |
| #16 | Synthetic Wayland ready marker: fixed basename in that same test directory; not remote data or a production path. Harness logs remain private and require review before sharing. |

Any follow-up CodeQL path alerts in `localfiles.py` identify the same intentional caller-selected input. The helper validates an opened descriptor and bounds reads; it does not introduce a privileged file-access service. Review new flows independently rather than automatically dismissing every occurrence of the rule.

## Validation and limits

129 unit/integration tests passed locally with Qt 6.11.3, including new FIFO, symlink/hardlink, file-replacement, growing-file, trace-target preservation, and command-argument regressions. Four bounded property tests passed. Bandit found no runtime/packaging issues. Tests use temporary paths and simulated devices; no real HID fuzzing, reboot, suspension, or installed-binary replacement was performed during this review.

CodeQL remains enabled with extended queries and the remote-and-local threat model. A completed review or empty open-alert list is not proof that no vulnerabilities exist. Dependency monitoring, review of future changes, independent review, and broader native-decoder testing remain necessary. Existing frozen installations need a rebuild to receive these source fixes.
