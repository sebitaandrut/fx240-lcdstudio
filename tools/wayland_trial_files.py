# SPDX-License-Identifier: GPL-3.0-or-later
"""Private run directories and regular-file I/O for the synthetic Wayland trial."""
import os
from pathlib import Path
import stat
import tempfile


def checked_directory(path, forbidden_mode):
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & forbidden_mode:
        raise ValueError('The Wayland trial needs an owned directory with private write access')
    return path


def new_run_directory(parent, guard):
    parent = Path(parent).absolute()
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    checked_directory(parent, 0o022)
    return Path(tempfile.mkdtemp(prefix='guard-' if guard else 'baseline-', dir=parent))


def private_run_directory(path):
    return checked_directory(path, 0o077)


def open_trial_file(path, mode):
    flags = {
        'r': os.O_RDONLY,
        'x': os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        'a': os.O_WRONLY | os.O_CREAT | os.O_APPEND,
    }[mode]
    fd = os.open(path, flags | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_nlink != 1 or info.st_mode & 0o077):
            raise ValueError('The Wayland trial requires a private regular file with one link')
        return os.fdopen(fd, mode, encoding='utf-8')
    except BaseException:
        os.close(fd)
        raise


def read_trial_file(path, *, missing_ok=False):
    limit = 1024 * 1024
    try:
        with open_trial_file(path, 'r') as stream:
            payload = stream.read(limit + 1)
    except FileNotFoundError:
        if missing_ok:
            return ''
        raise
    if len(payload) > limit:
        raise ValueError('The Wayland trial file exceeds the read limit')
    return payload
