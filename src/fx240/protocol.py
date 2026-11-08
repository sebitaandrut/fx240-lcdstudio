# SPDX-License-Identifier: GPL-3.0-or-later
"""Observed DRA and LIG framing; no device I/O."""
MAGIC = b"CRT\x00\x00DRA"
REPORT_SIZE = 1024
HEADER_SIZE = 32


def validate_brightness(level: int) -> None:
    if type(level) is not int or not 0 <= level <= 100:
        raise ValueError("Invalid LCD brightness level")


def build_brightness_report(level: int) -> bytes:
    validate_brightness(level)
    return (b"CRT\x00\x00LIG\x00\x00" + bytes([level])).ljust(REPORT_SIZE, b"\x00")


def build_reports(jpeg: bytes) -> list[bytes]:
    if not jpeg.startswith(b"\xff\xd8") or not jpeg.endswith(b"\xff\xd9"):
        raise ValueError("JPEG is missing SOI/EOI markers")
    total = HEADER_SIZE + len(jpeg)
    header = MAGIC + total.to_bytes(4, "big") + b"\xb1" + bytes(19)
    payload = header + jpeg
    payload += bytes((-len(payload)) % REPORT_SIZE)
    return [payload[i:i + REPORT_SIZE] for i in range(0, len(payload), REPORT_SIZE)]
