# SPDX-License-Identifier: GPL-3.0-or-later
"""Linux hidraw transport. Validate identity and lock the device before every output connection."""
import fcntl
import math
import os
import re
import stat
import struct
import time
from .protocol import REPORT_SIZE

VID, PID = 0x2000, 0x3000
HIDIOCGRAWINFO = 0x80084803


class Hidraw:
    def __init__(self, path):
        self.path = path
        self.fd = None

    def __enter__(self):
        path = os.fspath(self.path)
        # Reject unrelated character devices before opening them can have effects.
        if not isinstance(path, str) or re.fullmatch(r'/dev/hidraw[0-9]+', path) is None:
            raise ValueError('Select a /dev/hidrawN LCD interface')
        fd = os.open(path, os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            if not stat.S_ISCHR(os.fstat(fd).st_mode):
                raise RuntimeError("A hidraw character device is required")
            info = bytearray(8)
            fcntl.ioctl(fd, HIDIOCGRAWINFO, info, True)
            bus, vendor, product = struct.unpack("IHH", info)
            if (bus, vendor, product) != (3, VID, PID):
                raise RuntimeError("Unexpected USB identity; transmission cancelled")
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(fd)
            raise
        self.fd = fd
        return self

    def send(self, reports, delay_ms=10.0):
        if self.fd is None:
            raise RuntimeError("Transport is closed")
        if not math.isfinite(delay_ms) or delay_ms < 0:
            raise ValueError("Invalid delay")
        if not reports or any(len(r) != REPORT_SIZE for r in reports):
            raise ValueError("Invalid reports")
        writes = []
        start = time.monotonic()
        for i, report in enumerate(reports):
            data = b"\x00" + report
            before = time.monotonic()
            count = os.write(self.fd, data)
            writes.append((time.monotonic() - before) * 1000)
            if count != len(data):
                # A retry could create a second malformed HID report.
                raise RuntimeError(f"Incomplete write: {count}/{len(data)}")
            if i + 1 < len(reports):
                time.sleep(delay_ms / 1000)
        return (time.monotonic() - start) * 1000, writes

    def __exit__(self, *exc):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
