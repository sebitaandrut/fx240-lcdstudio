# Pre-publication privacy review — 2026-11-01

## Scope and approach

This review covers the current repository contents, every blob reachable from the local Git refs, the source ZIP, wheel, and frozen executable. It combines whole-file candidate scanning with manual inspection of application data flows, report fields, tracked-file inventory, asset metadata, and dependency provenance. It is not a claim of a formal security audit or a mathematical guarantee that every possible secret format can be recognized.

Git author/committer attribution is deliberately retained at the owner's request. A public commit identity is not classified as a source-content leak. No history rewrite or identity change was performed.

## Checks and observations

- No maintainer-specific identity or home-directory match was found in the scanned source, reports, archive contents, or inspected executable contents. The checks used local identity strings in memory; those strings are not included in this report.
- Credential signatures, email addresses, home paths, private network addresses, MAC-like values, UUIDs, sensitive file types, and PNG text/EXIF chunks were screened as review candidates. Candidates are not automatically treated as either real secrets or harmless values.
- The observed font email/copyright metadata belongs to the unmodified upstream Outfit font. Its required notices remain intact. Third-party dependency candidates were examined separately rather than deleting upstream copyright/license information.
- Frozen dependency candidates include public examples, protocol/file-format constants, generic TLS key-format markers, upstream build paths, and incidental byte-pattern matches. Native candidate entries were compared against installed dependency files; all matched byte for byte except the generated standard-library ZIP, which was inspected as an archive. No maintainer-specific identity or home-path match was found in those entries. Short hostname comparisons also produced generic-word coincidences in unmodified native dependencies; those are not records collected from this PC. Machine/boot IDs and interface identifiers were compared in memory where readable; optional network enumeration may be unavailable in restricted environments.
- Generated banner PNGs contain no text/EXIF chunks. SVG sources contain original artwork and fixed English text, not personal images or embedded source photographs.
- A numeric personal-recording basename was removed from the current development notes. Earlier README revisions still contain that non-identifying numeric basename, but no recording, personal directory, or identifying media metadata. The source history contains no personal media files.
- No actual hostname, personal network address, MAC, machine/boot ID, device serial, account credential, or private key was identified in application-owned source or committed result data. Numeric measurements and reproducibility metadata such as Arch Linux, software versions, display refresh rate, and timing profiles remain intentionally documented.

## Application data boundaries

The application reads sysfs sensor values locally and sends rendered JPEG reports to the selected HID interface. There is no application analytics, account login, remote collector, automatic upload, or network client in the reviewed application code. Qt's bundled network library is a dependency, not evidence that the application sends telemetry externally. logind integration communicates over the local system bus.

Preferences and the optional login entry stay in the user's configuration directory; they are not repository assets. A custom font selection or an OS error can contain a local path, and Sensors displays live sysfs paths. Screenshots, error details, CLI sensor output, and raw diagnostic logs therefore still need review before sharing. Automated tests use temporary configuration and synthetic data.

Image composition creates a fresh LCD canvas. Regression checks verify that source EXIF does not appear in the encoded LCD JPEG, including after loading a file. This removes metadata, not the visible content of an image: a personal photo remains personal content if intentionally displayed or shared.

## Repeating the review

From the repository root:

```bash
.venv/bin/python tools/audit_privacy.py --output /tmp/fx240-privacy-candidates.json
.venv/bin/python tools/audit_privacy.py --artifact dist/fx240-lcd-studio --output /tmp/fx240-binary-candidates.json
```

The executable inspection needs the build extra/PyInstaller. Repeat `--artifact` for a wheel or source ZIP. Reports contain candidate categories and locations, never matched credentials or identity strings. Exit code 1 means candidates need review; upstream font/dependency notices can legitimately trigger it. Do not publish raw reports automatically, because filenames and paths added in future work may themselves be private.

Before each publication, inspect the exact files and Git refs to be pushed and the actual release archives, not only the checkout. Ignore rules are a convenience, not a privacy guarantee. Keep private captures, environments, settings, raw logs, and unreviewed screenshots outside publication inputs. Rerun this review after any new hardware logs, media, dependency updates, or packaging changes. No repository or media publication has been performed by this review.
