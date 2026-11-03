# Privacy and security review boundaries

## Scope and approach

This review covers the current repository contents, every blob reachable from the local Git refs, the source ZIP, wheel, and frozen executable. It combines whole-file candidate scanning with manual inspection of application data flows, report fields, tracked-file inventory, asset metadata, and dependency provenance. It is not a claim of a formal security audit or a mathematical guarantee that every possible secret format can be recognized.

Git author/committer attribution is deliberately retained at the owner's request. A public commit identity is not classified as a source-content leak. No history rewrite or identity change was performed.

## Checks and observations

- No private maintainer home paths, device identifiers, or credentials were identified in the reviewed project content. Public GitHub attribution and repository URLs are intentional; matching those against local identity strings is not classified as a private-data leak. The scanner compares private tokens in memory and does not include them in its reports.
- Credential signatures, email addresses, home paths, private network addresses, MAC-like values, UUIDs, sensitive file types, and PNG text/EXIF chunks were screened as review candidates. Candidates are not automatically treated as either real secrets or harmless values.
- The observed font email/copyright metadata belongs to the unmodified upstream Outfit font. Its required notices remain intact. Third-party dependency candidates were examined separately rather than deleting upstream copyright/license information.
- Frozen dependency candidates include public examples, protocol/file-format constants, generic TLS key-format markers, upstream build paths, and incidental byte-pattern matches. Native candidate entries were compared against installed dependency files; all matched byte for byte except the generated standard-library ZIP, which was inspected as an archive. No maintainer-specific identity or home-path match was found in those entries. Short hostname comparisons also produced generic-word coincidences in unmodified native dependencies; those are not records collected from this PC. Machine/boot IDs and interface identifiers were compared in memory where readable; optional network enumeration may be unavailable in restricted environments.
- Generated banner PNGs contain no text/EXIF chunks. SVG sources contain original artwork and fixed English text, not personal images or embedded source photographs.
- A numeric personal-recording basename was removed from the current development notes. Earlier README revisions still contain that non-identifying numeric basename, but no recording, personal directory, or identifying media metadata. The source history contains no personal media files.
- No actual hostname, personal network address, MAC, machine/boot ID, device serial, account credential, or private key was identified in application-owned source or committed result data. Numeric measurements and reproducibility metadata such as Arch Linux, software versions, display refresh rate, and timing profiles remain intentionally documented.

## Application data boundaries

The application reads sysfs sensor values locally and sends rendered JPEG reports to the selected HID interface. There is no application analytics, account login, remote collector, automatic upload, or network client in the reviewed application code. Qt's bundled network library is a dependency, not evidence that the application sends telemetry externally. logind integration communicates over the local system bus.

Preferences and the optional login entry stay in the user's configuration directory; they are not repository assets. GUI mode now also keeps a private, bounded lifecycle trace in the state directory. Its fixed two-field schema contains only an allowlisted event code and relative elapsed seconds; no identifiers, device paths, readings, or arbitrary error strings are recorded. See [lifecycle trace boundaries](validation.md#lifecycle-limits). A custom font selection or an OS error can contain a local path, and Sensors displays live sysfs paths. Screenshots, error details, CLI sensor output, and raw diagnostic logs therefore still need review before sharing. Automated tests use temporary configuration and synthetic data.

Image composition creates a fresh LCD canvas. Regression checks verify that source EXIF does not appear in the encoded LCD JPEG, including after loading a file. This removes metadata, not the visible content of an image: a personal photo remains personal content if intentionally displayed or shared.

## Repeating the review

From the repository root:

```bash
.venv/bin/python tools/audit_privacy.py --output /tmp/fx240-privacy-candidates.json
.venv/bin/python tools/audit_privacy.py --artifact dist/fx240-lcd-studio --output /tmp/fx240-binary-candidates.json
```

The executable inspection needs the build extra/PyInstaller. Repeat `--artifact` for a wheel or source ZIP. Reports contain candidate categories and locations, never matched credentials or identity strings. Exit code 1 means candidates need review; upstream font/dependency notices can legitimately trigger it. Do not publish raw reports automatically, because filenames and paths added in future work may themselves be private.

Before each publication, inspect the exact files and Git refs to be pushed and the actual release archives, not only the checkout. Ignore rules are a convenience, not a privacy guarantee. Keep private captures, environments, settings, raw logs, and unreviewed screenshots outside publication inputs. Rerun this review after any new hardware logs, media, dependency updates, or packaging changes. The source repository is now public; personal media and raw private trial logs have not been included.

Intermediate trial reports were consolidated into current-state guides and aggregate evidence. Originals are retained in a private local archive outside the repository. Earlier Git commits still contain their previous versions; this cleanup does not rewrite history or erase data. No personal media was added to that history.

## Security scope

Privacy scanning looks for accidentally shared information; it does not establish runtime security or hardware safety. Functional tests and code review also do not establish absence of vulnerabilities. No independent security audit, full fuzzing campaign, or hardware-safety certification has been performed.

On 2026-11-02, an OSV batch query for the nine exact PyPI versions pinned in `packaging/requirements-build.txt` returned no advisory matches. Only package names and versions were submitted. This is a point-in-time database result, not a clean bill of health: unreported issues, Python itself, native/system libraries, and Qt advisories tracked outside the PyPI entries are not covered comprehensively. Updating a frozen package requires rebuilding it to update its bundled components. The [aggregate evidence](evidence.json) records this limited check.

Upstream review also identified [CVE-2026-105924](https://www.qt.io/blog/security-advisory-cve-2026-105924) in Qt 6.12.0, despite the empty PyPI advisory query. Qt describes a crash in untrusted CBOR-to-JSON conversion and lists 6.11.3 as fixed. No application flow processing untrusted CBOR was identified in this review; that is not proof of non-exploitability. The build pins and PKGBUILD now select PySide6/shiboken6 6.11.3, and source dependencies exclude 6.12.0. Existing frozen installations retain their embedded version until rebuilt. Other Qt/system components still need ongoing advisory monitoring.

The maintainer explicitly permits publication of their Git author name/email and public GitHub account. Those are not redaction targets. The privacy boundary protects the personal development environment: private home/build paths, hostnames, network/machine/device identifiers, credentials, settings, captures, and raw local logs. Public usernames, dates, and technical reproducibility data can also be linked to other public posts. No finding of credentials/private files should be described as “risk free.” Locally generated pacman packages and build logs can contain build metadata; review them separately before redistribution.

GitHub secret scanning and push protection are enabled, and private vulnerability reporting is available. Provider-pattern scanning and local privacy checks cannot identify every possible personal datum or secret format. See [SECURITY.md](../SECURITY.md) for the automated checks and independent-review scope.

The 2026-11-02 follow-up also inspected the pacman-installed executable and the reachable Git history. Static candidates in upstream libraries were separated from actual developer identifiers; the private review report stays outside the repository. The ongoing automated security controls, input limits, and bounded input tests are recorded in [the aggregate evidence](evidence.json). CodeQL alerts are a code-review queue, not evidence that personal PC data was published. No independent security audit is claimed.

The editor/profile implementation stores user-chosen names and media/font references in private configuration only. `profiles.json` and `settings.json` are ignored by Git; relative XDG configuration roots fall back to the home configuration directory to avoid accidental working-tree writes. These controls do not replace inspecting publication inputs and actual archives. No system font inventory, personal screenshots, media, or runtime profile library is bundled by the new application workflow.

## Local 0.2.0 integration review

The integration review checked the source worktree, reachable local Git blobs, and rebuilt Qt 6.11.3 executable. No new source privacy candidate locations appeared. The executable had no exact development-home, workspace-path, machine-ID, or boot-ID match, including nested ZIP contents. Flagged dependency entries matched the previously reviewed candidate; the changed standard-library ZIP container had identical member contents. These comparisons do not establish absence of every possible private datum or vulnerability. Private reports, test media, runtime profiles, and font catalogs remain outside publication inputs. Git author attribution remains intentionally public.

Only aggregate long-GIF resource measurements and scoped owner observations are documented. Buffer diagnostics adds numeric stream/queue/wait counts, without media names, paths, identifiers, or content. A future public binary/package still needs review of its exact build artifacts and third-party notices; this local integration is not a new binary redistribution approval.
