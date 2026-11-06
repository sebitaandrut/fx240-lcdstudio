# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded local file reads; caller-selected paths are not a privilege boundary."""
import os
from pathlib import Path
import stat


def config_home():
    """Ignore relative XDG paths so runtime data cannot land in the working tree."""
    home=Path.home()/'.config'
    selected=Path(os.environ.get('XDG_CONFIG_HOME') or home)
    return selected if selected.is_absolute() else home


def regular_identity(path):
    """Cache identity only after rejecting leaf links and special files.

    Kept in memory, never exported. Inode/ctime prevent stale reuse after a
    same-size replacement or after restoring the modification timestamp.
    """
    info=Path(path).lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('Input must be a regular file, not a symbolic link or special file')
    return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def read_regular(path, limit, *, private=False):
    """Reject special files/leaf symlinks; validate the opened descriptor as well.

    Parents belong to the launching user's configuration or explicit selection.
    This is not isolation from an attacker already controlling that user's account.
    """
    path = Path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError('Input must be a regular file, not a symbolic link or special file')
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError('Input must be a regular file')
        if private and (opened.st_uid != os.getuid() or opened.st_nlink != 1):
            raise ValueError('Private input must be owned by the current user and have one link')
        if opened.st_size > limit:
            raise ValueError('Input exceeds the configured byte limit')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            payload = stream.read(limit + 1)
        if len(payload) > limit:
            raise ValueError('Input exceeds the configured byte limit')
        return payload
    finally:
        os.close(fd)
