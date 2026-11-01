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

## Before committing

1. Review the actual changed files and diff.
2. Run checks appropriate to the change. For application changes, the current local suite is `python -m unittest discover -s tests -v`; install `.[desktop]` to include Qt/QML checks. Documentation-only edits do not need to repeat hardware trials.
3. Update README usage when behavior changes. Keep detailed protocol notes, hardware trial records, and evidence limits under `docs/` rather than turning the README into an edit-by-edit transcript.
4. Stage only the intended source, tests, documentation, and licensed assets. Keep environments, private media, raw captures, local trial logs, and credentials excluded. Inspect staged names and the staged diff before committing.
5. Create the local commit and verify its hash and final repository status. Commit subjects and descriptions must be in English.

A local commit does not authorize publishing. Creating a GitHub repository, adding/pushing to a remote, or sharing personal evidence requires the maintainer's explicit authorization.

## Initial history

The current implementation was developed before the first Git commit. Its history should start with an honest snapshot of the validated implementation, for example:

`feat: establish the validated FX240 Linux baseline`

Do not reconstruct fictional intermediate commits or backdate the earlier physical trials as commit history. The real trial sequence and its limits are documented separately in `docs/hardware-trials.md` and the associated records. Subsequent commits should record actual changes made from that baseline.

## Interface language and local preferences

Keep source keys, comments, docs, and commits in English. Add Spanish UI translations in `src/fx240/i18n.py` and route QML labels through the translation function. Do not translate canonical enum values or Linux sensor identities. Tests must use temporary preference paths or omit the optional preference store; never read/write a contributor's real configuration. Keep local preference files and font paths out of published evidence.
