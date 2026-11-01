# Observed HID protocol

This unofficial profile was reconstructed from the existing FX240 HID prototype and checked against generated packets and controlled USB output. No code or tests from the abandoned AIO Control Center project are used. Missing historical deductions are not reconstructed as facts.

## Framing

| Offset | Length | Content |
| --- | --- | --- |
| 0 | 8 | `43 52 54 00 00 44 52 41` (`CRT\0\0DRA`) |
| 8 | 4 | Big-endian length: 32 + JPEG size, excluding padding and hidraw prefix |
| 12 | 1 | `B1`, meaning unknown |
| 13 | 19 | Observed zeros, semantics unknown |
| 32 | Variable | RGB JPEG, 240 × 240 |
| JPEG end | 0–1023 | Zero padding to a multiple of 1024 |

The padded message is split into 1024-byte payloads. Each Linux `os.write` receives `00 + payload` (1025 bytes). The leading byte follows hidraw's report-number convention and is excluded from the DRA length. See the [kernel hidraw documentation](https://docs.kernel.org/hid/hidraw.html); the convention alone does not establish this device's complete descriptor.

The sender verifies USB bus 3, VID `0x2000`, and PID `0x3000` using `HIDIOCGRAWINFO`, rejects regular files/symlinks, and takes a cooperative lock. Matching IDs do not establish compatibility with every interface or revision. The default rotation is 180 degrees and remains configurable.

## Verification and limits

The modular sender matched the prototype's packets for 240/240 checked frames. A subsequent controlled capture matched all 24 expected 1024-byte reports for a two-frame trial, with successful USB completions and no truncation. Aggregate verification and encoding settings are in [evidence.json](evidence.json). No raw capture or personal image is distributed.

An older capture had a one-byte-short final payload and an inconsistent JPEG boundary; it is not exact-validation evidence. The controlled trial did not reproduce that discrepancy, and the historical cause remains unknown.

The meaning of `B1`, full descriptor semantics, initial device-state requirements, buffering, acknowledgements, refresh synchronization, size/rate limits, and brightness/firmware commands remain unknown. Host-call acceptance and USB completion do not prove optical presentation or absence of panel losses. Full PC shutdown was tested without verifying removal of USB standby power, so independence from earlier vendor initialization is not established.

Use `examples/compare_usb_capture.py` for controlled payload comparisons and `tests/test_fx240.py` for framing regressions. Keep captures private and inspect only the intended LCD traffic. Never treat a small diagnostic code region as proof of a complete tear-free LCD frame.
