"""Observed DRA framing; no device I/O."""
MAGIC = b"CRT\x00\x00DRA"
REPORT_SIZE = 1024
HEADER_SIZE = 32


def build_reports(jpeg: bytes) -> list[bytes]:
    if not jpeg.startswith(b"\xff\xd8") or not jpeg.endswith(b"\xff\xd9"):
        raise ValueError("JPEG is missing SOI/EOI markers")
    total = HEADER_SIZE + len(jpeg)
    header = MAGIC + total.to_bytes(4, "big") + b"\xb1" + bytes(19)
    payload = header + jpeg
    payload += bytes((-len(payload)) % REPORT_SIZE)
    return [payload[i:i + REPORT_SIZE] for i in range(0, len(payload), REPORT_SIZE)]
