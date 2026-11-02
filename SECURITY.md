# Security policy

FX240 LCD STUDIO is experimental. Automated scans and hardware observations are not an independent security audit or a hardware-safety certification. Use the latest reviewed source; historical frozen executables retain their bundled dependencies until rebuilt.

## Report privately

Use [GitHub private vulnerability reporting](https://github.com/sebitaandrut/fx240-lcdstudio/security/advisories/new). Please include the affected commit/package version, impact, and a minimal reproducible example, preferably with synthetic input and a simulated transport. Do not post exploit details or private captures in a public issue. Volunteer response times are not guaranteed.

Remove credentials, personal media, home paths, host/device identifiers, and unrelated USB traffic before sharing diagnostics. Ask before including an unredacted configuration or recording. For ordinary bugs, use the public issue tracker with sanitized information.

## Controls and boundaries

- CodeQL default setup analyzes Python and GitHub Actions with extended queries and the remote-and-local threat model.
- The security workflow runs Bandit, known-advisory checks, and bounded property-based tests. Runtime/packaging Bandit findings fail the job. Developer tools are gated at medium severity or higher; reviewed low-severity subprocess/import notices are not a security clearance.
- Python advisory databases do not comprehensively cover bundled Qt, CPython, native libraries, malicious packages, or unreported defects. Track upstream advisories and inspect the build inventory as well.
- Property-based tests exercise framing, rejected paths, malformed preferences, and small image/GIF inputs without opening USB. They do not constitute exhaustive native-decoder fuzzing.
- Never fuzz arbitrary HID commands against a physical cooler. Hardware checks must use the intended LCD, observed valid framing, appropriate access permissions, and a controlled test plan.

## Independent review scope

An independent reviewer should pin a commit and examine HID selection/identity/locking, partial writes, shutdown/helper file descriptors, media/font resource limits, preference and path handling, build/download integrity, PKGBUILD installation, bundled components, and QML handling of user-controlled text. Record findings with reproduction, severity, remediation, and remaining uncertainty. A contributor review or automated report must not be presented as a guarantee of safety.

See [validation](docs/validation.md) and [privacy review](docs/privacy-review.md) for the evidence and its limits. No personal recordings or local configurations are included in the repository; authorized Git attribution (including the chosen email) and the public GitHub account remain public. Personal development-environment data is excluded.

See the [CodeQL alert review](docs/security-review.md) for per-alert decisions, corrections, tests, and trust boundaries.

## Reproduce the checks

In a separate developer environment, install `packaging/requirements-security.txt` and Pillow 13.0.0, then run the commands in `.github/workflows/security.yml`. The build requirements contain platform-specific wheel hashes for Arch x86_64/CPython 3.14; these hashes are also verified by the PKGBUILD. These checks are optional for end users.

After building, `tools/inventory_binary.py` accepts the trusted local executable and its `build/build-environment.json` manifest. It records package/framework versions and shared-object hashes without home paths or machine identifiers. The report is a partial component inventory, not a complete SBOM or a vulnerability verdict; CI does not upload the executable.
