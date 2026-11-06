# Development and commit workflow

This repository contains the native FX240 project only. Do not import code, UI assets, dependencies, or tests from the abandoned AIO Control Center project.

## Language

Write source comments, documentation, tests, commit messages, pull request descriptions, and release notes in English. Maintainer discussion may take place in Spanish.

## Commit boundaries

Create one commit for a coherent, reviewable change rather than one commit per chat message or intermediate edit. Include implementation, relevant regression tests, and documentation in the same commit when they describe the same behavior.

Use a short imperative subject with a type prefix:

- `feat: add a dual CPU and GPU display theme`
- `fix: keep the degree symbol next to decimal temperatures`
- `docs: record the Outfit readability trial`
- `test: cover sensor removal during desktop output`
- `refactor: share frame diagnostics between output modes`
- `chore: update desktop dependency constraints`

Use the body for motivation, relevant tradeoffs, and validation results when needed. Clearly distinguish host timing, simulated checks, USB captures, and human observations of the physical display. Do not present a render, test count, or host frame rate as proof of optical refresh behavior.

The [user build guide](docs/building.md) makes the full suite optional for end users. Contributors should run the relevant regression checks, and CI continues to run the complete suite.

## Before committing

1. Review the actual changed files and diff.
2. Run checks appropriate to the change. For application changes, the current local suite is `python -m unittest discover -s tests -v`; install `.[desktop]` to include Qt/QML checks. Documentation-only edits do not need to repeat hardware trials.
3. Update README usage when behavior changes. Keep detailed protocol notes, hardware trial records, and evidence limits under `docs/` rather than turning the README into an edit-by-edit transcript.
4. Stage only the intended source, tests, documentation, and licensed assets. Keep environments, private media, raw captures, local trial logs, and credentials excluded. Inspect staged names and the staged diff before committing.
5. Create the local commit and verify its hash and final repository status. Commit subjects and descriptions must be in English.

A local commit does not authorize publishing. Creating a GitHub repository, adding/pushing to a remote, or sharing personal evidence requires the maintainer's explicit authorization.

## Reviewing CodeQL path alerts

Trace the input to the filesystem operation and identify the trust boundary. For an explicitly selected local asset, use the bounded regular-file reader in `src/fx240/localfiles.py` for content and keep cache metadata local. For paths derived from untrusted names, enforce the intended directory and test traversal and link handling. Record the reasoning when dismissing an individual false positive. Keep the query enabled so it can still detect new unsafe flows. See the [security review](docs/security-review.md).

## Code structure

| Responsibility | Location |
| --- | --- |
| Qt/QML interface and application controller | `src/fx240/qml/`, `gui.py`, `i18n.py` |
| Worker, live configuration, and frame events | `src/fx240/session.py` |
| Telemetry collection | `src/fx240/telemetry.py` |
| Focus rendering, media, and overlays | `src/fx240/focus.py`, `media.py`, `background.py`, `gifstream.py`, `overlay.py`, `dashboard.py` |
| Composition schema, editing, and private profiles | `src/fx240/scene.py`, `editor.py`, `workspace.py`, `livepreview.py`, `profiles.py` |
| Local fonts, asset browsing, and circular preview | `src/fx240/typography.py`, `systemfonts.py`, `filebrowser.py`, `preview.py` |
| HID framing and verified transport | `src/fx240/protocol.py`, `transport.py` |
| Preferences, tray, and login startup | `src/fx240/preferences.py`, `tray.py`, `autostart.py` |
| Sleep/shutdown coordination and standby fallback | `src/fx240/sleep.py`, `shutdown.py`, `guard.py`, `idle.py`, `lifecycle.py` |
| CLI and scheduling | `src/fx240/cli.py`, `player.py` |
| Regression checks, diagnostic tools, and build inputs | `tests/`, `tools/`, `examples/`, `packaging/` |

Keep rendering, sensor acquisition, output scheduling, and UI responsibilities separate. A bounded latest-frame queue connects the worker to the GUI. Add regression checks for behavior changes; exploratory measurement output belongs outside the repository. Keep only concise validation conclusions and the aggregate evidence needed to support them.

The first commit snapshots the implementation developed before Git tracking. Do not reconstruct fictional earlier commits or backdate tests. Consolidating documentation does not rewrite the existing Git history.

## Interface language and local preferences

Keep source keys, comments, docs, and commits in English. Add Spanish UI translations in `src/fx240/i18n.py` and route QML labels through the translation function. Do not translate canonical enum values or Linux sensor identities. Tests must use temporary preference paths or omit the optional preference store; never read/write a contributor's real configuration. Keep local preference files and font paths out of published evidence.
