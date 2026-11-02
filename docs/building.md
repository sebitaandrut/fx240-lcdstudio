# Build your own Linux executable

**Validation scope: Arch Linux x86_64 only. No other distribution has been tested.**

The build packages Python, the application, Qt/QML, Pillow, Outfit, icons, and their bundled notices into a Linux executable using PyInstaller. Running that executable does not require activating a virtual environment or separately installing Python. This is a frozen application, not ahead-of-time compilation of all Python logic. It still needs the host's graphics/session libraries and compatible system ABI. In particular, PyInstaller does not bundle glibc; a binary built on a newer distribution may fail on an older one. Building locally is the recommended initial workflow. See [PyInstaller operating mode](https://pyinstaller.org/en/stable/operating-mode.html) and [Linux portability notes](https://pyinstaller.org/en/stable/usage.html#making-gnu-linux-apps-forward-compatible).

## 1. Prepare Arch Linux

Use an up-to-date Arch installation with a working graphical session and graphics driver. Install the build tools and desktop runtime libraries:

```bash
sudo pacman -Syu --needed git python python-pip binutils zlib glib2 krb5 fontconfig libglvnd libxkbcommon libxkbcommon-x11 libxcb xcb-util-cursor wayland dbus
```

`binutils` supplies `objdump`; `glibc`, a base-system dependency, supplies `ldd`. Python development headers are part of the Arch Python package. A compiler is normally unnecessary with supported prebuilt wheels/bootloader; if pip reports a source build, install `base-devel` and investigate package/platform compatibility before proceeding. Qt/PySide and Pillow are installed in the build environment below; installing the separate system `pyside6` package is unnecessary for this recipe. The existing desktop provides a display server/compositor and appropriate GPU driver; this command does not install or configure a desktop. Arch's [Qt base dependency list](https://archlinux.org/packages/extra/x86_64/qt6-base/) is a reference for native desktop requirements.

All development trials used Arch Linux, Python 3.14.9, Qt/PySide 6.12.0, Pillow 13.0.0, PyInstaller 6.22.3, and glibc 2.44 on x86_64. The package command above has not been validated on a clean Arch installation; the tested development machine already had its desktop libraries. A clean-machine installation remains a release gate.

## 2. Create an isolated build environment

Clone the public repository and build inside a dedicated environment:

```bash
git clone https://github.com/sebitaandrut/fx240-lcdstudio.git
cd fx240-lcdstudio
python3 -m venv .venv-build
.venv-build/bin/python -m pip install -r packaging/requirements-build.txt
.venv-build/bin/python -m pip install --no-deps --no-build-isolation .
.venv-build/bin/python tools/build_binary.py
```

`packaging/requirements-build.txt` records the working Python dependency versions, including build tooling. Use a separate environment rather than installing these versions into system Python. Python itself is not pinned by pip: use the recorded Python version when reproducing this build. The manifest helps reproduce the recipe, but does not promise byte-for-byte identical binaries. The declared source minimum is Python 3.11; this packaging trial only validates Python 3.14.9.

A fresh clone of the public repository was built on the existing Arch development host using a new environment and uncached dependency downloads. Installation, `pip check`, the build, and installed/frozen self-tests passed. The standalone check temporarily made the source and build environment unavailable. This does not replace a clean OS/VM installation. The `arch-build` CI job also exercises this user recipe in an empty Arch container, without uploading the binary. See [validation](validation.md).

The normal application needs Pillow and, for the GUI, PySide6 Essentials (which supplies Qt Quick, Widgets, DBus, and SVG). NumPy/OpenCV are optional video-analysis dependencies and are not needed for the application or executable build. Tk, PyQt6, usbmon, Wireshark, and root privileges are not required for building or running the GUI. USB access still requires appropriate local permissions.

## 3. Verify and run the result

The one-file result is `dist/fx240-lcd-studio`. These commands work without activating the build environment:

```bash
./dist/fx240-lcd-studio self-test
./dist/fx240-lcd-studio --help
./dist/fx240-lcd-studio sensors
./dist/fx240-lcd-studio
```

The last command opens Studio and automatically sends to a uniquely identified FX240, as the source application does. Close any other LCD sender first. The `self-test` command is different: it uses synthetic sensors, software rendering, and a headless window. It checks QML, four pages, fonts, SVG assets, rendered frames, and orderly worker shutdown without sending to USB or writing preferences. Expect a JSON result with `frozen: true`, `errors: []`, and `hid_open_attempts: 0`. This check does not validate native Wayland/X11 rendering, tray behavior, actual USB access, suspend, or physical FPS.

For a stricter independence check, copy the executable outside the source tree, change to an unrelated directory, and run it with the build environment deactivated and `PYTHONPATH` unset. The recorded local check used `/tmp` as the working directory with `VIRTUAL_ENV` and `PYTHONPATH` removed; it passed on the same Arch machine, not on a clean machine.

The one-file format extracts its runtime to a temporary directory while running. If the temporary filesystem prevents executing extracted libraries, use a suitable executable temporary directory or build a directory bundle:

```bash
.venv-build/bin/python tools/build_binary.py --onedir
./dist/fx240-lcd-studio/fx240-lcd-studio self-test
```

For a directory build, keep the **entire** `dist/fx240-lcd-studio/` folder together. The two formats share an output name: move the previous output aside before switching formats. Keep build logs and the generated `build/build-environment.json` when reporting failures. The helper never enables login startup or edits the user's settings.

## 4. Desktop integration and permissions

The executable uses the same preference file as the source app, at `$XDG_CONFIG_HOME/fx240-linux/settings.json`, defaulting to `~/.config/fx240-linux/settings.json`. Keep the executable in a permanent location before enabling **Settings → Start at login → Minimized in tray**. This opt-in setting installs a per-user desktop entry; it runs after graphical login, not before login. Disable it in Settings to remove the managed entry. Moving the executable requires disabling and enabling the option again from its new location. Source-mode startup similarly depends on keeping its installed environment in place.

Run `./dist/fx240-lcd-studio gui --start-minimized` to try minimized startup. Without a tray host, the window remains accessible through the taskbar. For OS shutdown/reboot validation, leave the desktop-autostarted instance running: development-launched instances failed standby, while initial autostarted warm-reboot and full-shutdown trials passed. The exact termination difference is unproven. See [validation and limits](validation.md) and the [freedesktop autostart specification](https://specifications.freedesktop.org/autostart/latest/). Suspend/resume and repeatability remain pending.

Packaging does not grant access to `/dev/hidrawN`. Identify the LCD interface and configure access for your distribution; device numbering can change. The transport validates identity and takes a cooperative lock. Do not run the whole GUI as root to bypass access errors. See [the protocol](protocol.md) and [usage](desktop.md) for output behavior.

## Optional developer checks

Users building the application can use the packaged `self-test` above and then check the native interface/LCD. Running the full test suite is not required to build or use Studio. Contributors should run it after code changes; GitHub Actions runs it automatically, including tests for development/benchmark tools. The suite uses synthetic USB transports and does not transmit to the LCD.

```bash
.venv-build/bin/python -m unittest discover -s tests -v
```

A successful self-test or test suite does not establish physical LCD behavior, clean-machine compatibility, or long-term stability.

## Troubleshooting and unverified platforms

- **Qt platform plugin fails:** launch from a terminal with `QT_DEBUG_PLUGINS=1` and inspect missing native libraries. A headless self-test can pass while a display plugin is missing. Do not mix unrelated system Qt plugins with the bundled Qt version.
- **Permission denied on HID:** resolve device access; the preview should still remain available.
- **GLIBC version error:** rebuild on the target system or a deliberately chosen older compatible build system. Do not assume copying this Arch binary to Debian, Ubuntu, Fedora, or another distribution will work.
- **Missing build wheels:** record Python, architecture, OS, and package versions; this recipe has not validated other architectures or source compilation of Qt/Pillow.
- **Binary distribution:** the code is GPLv3-or-later; bundled dependency redistribution notices still need a release review before public binary publication. Local build success does not mark the project stable.

Other distributions need their own package mapping and installation, native UI, sensor, USB, tray, startup, and endurance validation. Add verified instructions when those tests actually occur.
