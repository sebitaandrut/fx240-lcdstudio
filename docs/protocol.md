# Observed protocol

This profile is implemented from local HID code; it is not an official specification.

| Offset | Length | Content |
|---|---|---|
| 0 | 8 | `43 52 54 00 00 44 52 41` (`CRT\0\0DRA`) |
| 8 | 4 | Big-endian length: 32 + JPEG size, excluding padding and hidraw prefix |
| 12 | 1 | `B1`, meaning undetermined |
| 13 | 19 | Observed zeros; semantics unknown |
| 32 | variable | RGB JPEG, 240×240 |
| JPEG end | 0–1023 | Zero padding to a multiple of 1024 |

The message is split into 1024-byte payloads. Each prototype `os.write` call receives `00 + payload`: 1025 bytes in userspace. The leading byte follows hidraw's report-number convention and is excluded from the DRA length. The [kernel documentation](https://docs.kernel.org/hid/hidraw.html) defines this convention; it does not establish the FX240's particular descriptor.

The minimal synthetic test vector uses JPEG markers, not a decodable image: `ff d8 61 62 63 ff d9`, DRA length 39 (`00 00 00 27`), and one report padded to 1024 bytes.

Identity checking uses `HIDIOCGRAWINFO`, USB bus 3, VID 0x2000, and PID 0x3000. A complete descriptor was not analyzed here, and not all devices sharing those IDs have been tested. The old inspector's search for byte `0x85` is insufficient to interpret Report IDs: that byte may also appear in another item's data.

The 180-degree orientation comes from validation comments in later scripts; the initial encoder still described it as a hypothesis. It remains configurable. Aspect-ratio preservation comes from the GIF player; the initial encoder stretched content to a square. JPEG equivalence was checked on a square image, not arbitrary images.

## Unknowns

The functional meaning of B1, cold-boot handshake requirements, LCD buffering, frame acknowledgements, refresh synchronization, size/rate limits, and brightness/firmware commands remain unknown. A complete write confirms host-call acceptance, not optical presentation or absence of internal losses.

The inspected historical capture contains the header and a decodable 240×240 JPEG, but payload lengths are 1024, 1024, and 1023. The JPEG segment selected by the declared length does not end at EOI and differs from the local file. It is therefore not presented as byte-for-byte validation of the current protocol. Capture this version again and compare boundaries, prefix, lengths, and content. The JSON verification record preserves hashes and measurements to distinguish this evidence from future trials.

## Current bus-level verification

A later controlled capture of this modular sender matched all 24 expected output reports exactly, each 1024 bytes, with 24 successful output completions and no packet truncation. The historical short final payload did not recur. Against the saved local historical report buffer, the old capture matches after removing byte 2048, at the third report boundary. This correspondence does not identify the original cause. See [hardware trials](hardware-trials.md) and [sanitized current verification](usb-trial-verification.json).
