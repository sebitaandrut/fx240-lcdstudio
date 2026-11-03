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

The follow-up analysis on `1773b03835e79e1a25153c0f011d3ac5087aeed1` automatically closed six original locations (#1–#3, #20–#22), retained fifteen, and added three. All three additions were also reviewed:

| Alert | Follow-up decision |
| --- | --- |
| #23 | `localfiles.py` lstat: intentional caller-selected regular-file input; metadata check before opening, no privilege boundary or remote path source. |
| #24 | `localfiles.py` open: the same path, opened no-follow/nonblocking; descriptor type/ownership/link checks as applicable, plus bounded bytes before decoding. |
| #25 | `tests/test_localfiles.py` mocked open: synthetic replacement-race regression only. Its closure uses a `TemporaryDirectory` path and replaces that file with a FIFO to verify descriptor rejection; it is not application code handling attacker input. |

These eighteen remaining injection/traversal alerts are classified as false positives for the reviewed local-app threat boundary, with individual GitHub comments. This does not classify future occurrences automatically. The [tests](https://github.com/sebitaandrut/fx240-lcdstudio/actions/runs/41391379387), [security workflow](https://github.com/sebitaandrut/fx240-lcdstudio/actions/runs/41391379492), and [CodeQL analysis](https://github.com/sebitaandrut/fx240-lcdstudio/actions/runs/41391379271) record the follow-up checks.

The follow-up CodeQL path alerts in `localfiles.py` identify the same intentional caller-selected input. The helper validates an opened descriptor and bounds reads; it does not introduce a privileged file-access service. Review new flows independently rather than automatically dismissing every occurrence of the rule.

## Validation and limits

129 unit/integration tests passed locally with Qt 6.11.3, including new FIFO, symlink/hardlink, file-replacement, growing-file, trace-target preservation, and command-argument regressions. Four bounded property tests passed. Bandit found no runtime/packaging issues. Tests use temporary paths and simulated devices; no real HID fuzzing, reboot, suspension, or installed-binary replacement was performed during this review.

CodeQL remains enabled with extended queries and the remote-and-local threat model. A completed review or empty open-alert list is not proof that no vulnerabilities exist. Dependency monitoring, review of future changes, independent review, and broader native-decoder testing remain necessary. Existing frozen installations need a rebuild to receive these source fixes.

## Editor, profiles, and GIF buffering

The scene schema accepts bounded geometry, enumerated readings/animations, plain text, finite opacity, hex colors, and absolute local asset references. Unknown fields, scripts/QML, URL resources, duplicate IDs, oversized scenes, and excess layers are rejected. Media/font loading uses the existing regular-file/byte/pixel/frame limits; output is composed on a fresh RGB canvas without source metadata. Paths stay in private configuration and user text/font/profile names render as plain text in Qt. Examples and screenshots use synthetic resources only.

Named profiles use a separate fixed `profiles.json` file: eight entries, 256 KiB, versioned metadata, unique IDs/names, atomic private replacement. Names cannot select a filesystem path. Malformed, oversized, symlinked, or multiply linked libraries are preserved rather than silently overwritten. A missing asset leaves the saved profile available for repair, while startup falls back to Focus. Saving validates the preview first; an unsaved draft changes active output only during an explicit temporary LCD trial. The last validated draft and selected saved profile are persisted independently. Global and per-profile data must be reviewed before sharing; asset paths and user-chosen names can be private.

Fontconfig uses a fixed executable lookup and fixed arguments through QProcess; no user family/path enters a command or shell. Discovery is asynchronous and capped at three seconds, 2 MiB, and 4096 supported entries. The font catalog remains in memory locally. Variable faces use their weight axis; static weights require actual installed styles. Rendering threads have independent FreeType faces.

The editor worker has an unset device, output disabled, and a transport that always rejects USB. Its metrics come from the main session snapshot. Pointer areas use [Qt's preventStealing](https://doc.qt.io/qt-6/qml-qtquick-mousearea.html#preventStealing-prop) to retain long drags through ancestor scrolling areas. Tests cover long real QML pointer drags, draft/output separation, save/copy/restart, active-profile switching, corruption/atomic-write preservation, static style selection, and metadata parsing without asset opens.

Local tests and scans are not an independent audit or a native decoder sandbox. Complex assets can take time to decode; initial resource/playback/resume observations are recorded in the validation guide, while multi-hour endurance and repeated lifecycle cycles remain pending. The published 0.2.0 integration completed CI/CodeQL; the separate review of its new findings is recorded below.

The reviewed source passed 177 unit/Qt tests, six bounded property checks, and runtime/packaging Bandit with zero findings. Optional desktop checks are skipped when Qt is absent. The default self-test exercises a synthetic long GIF, makes zero HID-open attempts, and uses no preferences store. Source/privacy candidate review identified no new private-data findings; this does not replace a remote CodeQL run or an independent audit.

Long desktop GIFs use automatic bounded decoding: 64 MiB input, 2000 frames, 4 megapixels per source frame, and 300 million cumulative source pixels. Each decoder queues at most 12 canvas frames. Session-owned leases share unchanged assets across renderer replacements and release on failed construction, replacement, validation, and exit. Workers have cancellation and a bounded join; a slow native operation can outlive that join temporarily. These controls bound selected resources, not total RAM or native decoder execution. Diagnostics exposes only aggregate stream/queue/wait counts, never media paths or content. Default self-test covers a synthetic long GIF and never opens HID. No new dependency or network client is introduced. The completed 0.2.0 CodeQL analysis produced four new path alerts, reviewed individually below.

## 0.2.0 path-alert follow-up — 2026-11-03

Reviewed all four new open `py/path-injection` alerts on `7d17f3b2d2d8747f0673bf5f7d496a00d9f2d6f6`, including the SARIF source-to-sink paths and actual GUI/developer-tool callers. [Tests and Arch builds](https://github.com/sebitaandrut/fx240-lcdstudio/actions/runs/41666259408), [security checks](https://github.com/sebitaandrut/fx240-lcdstudio/actions/runs/41666259160), and [CodeQL](https://github.com/sebitaandrut/fx240-lcdstudio/actions/runs/41666259010) completed successfully for that integration. Analysis success alone does not mean no alerts.

| Alert | Source, operation, and review decision |
| --- | --- |
| [#26](https://github.com/sebitaandrut/fx240-lcdstudio/security/code-scanning/26) | Offline GIF generator: the CLI argument is explicitly the intended output filename. It writes synthetic content as the invoking user, using exclusive `xb` creation. Existing regular files, hard links, symlinks (including dangling links), and FIFOs are rejected without following or overwriting them. There is no remote file-writing or privileged service. Classified as a false positive for this local tool's trust boundary. |
| [#27](https://github.com/sebitaandrut/fx240-lcdstudio/security/code-scanning/27) | Profile directory creation: the reported source is the launching user's XDG configuration root. The GUI also supports an explicitly selected configuration root and uses the fixed `profiles.json` basename. Profile names and scene fields never construct the destination. Normal-user configuration-directory creation is intentional; classified as a false positive. |
| [#28](https://github.com/sebitaandrut/fx240-lcdstudio/security/code-scanning/28) | Profile temporary file: `NamedTemporaryFile` exclusively creates a random file with private mode in the same caller-selected configuration directory. JSON is schema/size validated. The path does not originate in a profile name, media content, or remote client. Classified as a false positive, with interrupted-write and private-mode regressions. |
| [#29](https://github.com/sebitaandrut/fx240-lcdstudio/security/code-scanning/29) | Profile replacement: the temporary source is generated internally and the destination is the fixed library location under the user's chosen configuration root. Names stay metadata. Private bounded loading rejects linked/special library inputs; replacement failure preserves the old library. This is intentional same-user persistence, classified as a false positive. |

Each alert has its own GitHub dismissal rationale. No rule, query suite, language, or local threat model was disabled, and no suppression was added to source. These decisions do not automatically classify future alerts. Parent directories and the launching account/environment remain trusted; this is not protection against an attacker already controlling that account or permission to expose the API as a privileged/remote service.

Three additional regression tests cover default-XDG destination containment despite path-like profile names, preservation of hard-linked/FIFO libraries, and exclusive generator output against existing files/links/FIFOs. The full local suite passed **177 tests**, six bounded property checks passed, and Bandit reported zero runtime/packaging findings and zero medium/high developer-tool findings. Only explanatory comments/docstrings changed in production/tool implementation; no exploitable vulnerability was identified in these four flows and no functional security fix is claimed. Raw SARIF, local reports, and test artifacts remain outside the repository.
