# Tearing investigation

The owner's primary symptom is line-like spatial discontinuities within a moving object. Keep this separate from whole-frame timing irregularity, low-frame-rate stepping, and fading/ghost contours. More than one effect may be present. No tearing fix or hardware-only cause has been established.

## Existing evidence

- The symptom remained during precomputed GIF playback without runtime GIF decoding, rendering, JPEG encoding, sensor sampling, or preview. Host timing alone cannot establish optical presentation.
- The official-session capture reconstructs 720 complete JPEG messages, with the same DRA header layout used by Studio. No image fragment sequence was interrupted by another image header or a separate command. Every JPEG decoded successfully.
- No separate per-image commit/flip token appeared in that session. The three periodic `CON` payloads were identical, approximately ten seconds apart. Pending interrupt-IN requests returned no image acknowledgements before cancellation. This does not rule out an unused synchronization mechanism or an unobserved endpoint.
- Registered camera samples contain differing consecutive codes at different heights and overlapping contours. Isolated disappearance recordings also show fading that is absent from the transmitted images. Camera exposure, temporal processing, rolling shutter, display response, and scanout remain confounded. Four-height marker agreement is not proof of a complete tear-free image.

## Static software review

The manufacturer's public downloader led to the public 1.0.4 application archive. Files were inspected as data, without installation, execution, or access to the owner's VM. Matching this downloaded build to the build used for the capture has not been established.

The executable contains an `RLCD_1_5DeviceOperation` class. Its native transport library supports multiple device families and exposes heartbeat, handshake, image, upload, and finalization functions. The inspected heartbeat routine constructs `CONNECT`; this is consistent with the captured periodic `CON` messages. An inspected `getFinishCommand` constructs `STP`, not an identified per-JPEG buffer swap. A function name or a generic transport operation does not establish compatibility or semantics for this LCD. No new command was replayed.

Tracing the class's virtual methods resolves its image-ready callback: it obtains the Qt capture, scales and rotates the image, calls the image-to-byte conversion helper, checks whether HID is open, and dispatches the resulting image structure to `SDDevice::appendSendData`. The callback's `ready` signal belongs to `QQuickItemGrabResult`; it indicates capture availability in Qt, not LCD presentation readiness.

The reviewed image helper initializes an internal image type of `0x10`, disables the optional completion wait, and sets the DRA format byte to `0xB1`. The queue accounts for pending bytes, rejects overflow, and wakes the writer when an image is appended. The corresponding writer branch prepends the 32-byte DRA header, splits the payload into reports, pads the final report, and calls `hid_write` through its virtual write method. On this path, the fragment loop bypasses waits used by other transfer types; the disabled completion flag also bypasses its final acknowledgement wait. An additional one-millisecond sleep follows the image. The empty-queue wait is woken by the producer and is not evidence of panel refresh synchronization. These are static control-flow findings for the downloaded build, not a runtime trace or proof that no other mechanism exists.

Studio likewise sends complete framed images through sequential HID writes, with a configurable inter-report delay and host frame scheduling. Its optional delay differs from the reviewed normal official fragment loop. Previous owner trials with shorter delays, including zero, did not establish a tearing fix. A USB write returning successfully in either implementation does not establish presentation of a complete image.

The independent [FX LCD implementation](https://github.com/w1n-ror/fx_lcd_software-for-linux/blob/master/core.py) sends initialization messages and repeated image chunks; it does not provide a verified presentation-synchronization solution. [SignalRGB lists FX-LCD support](https://signalrgb.com/devices/), but that listing alone provides no protocol or tear-free guarantee.

This comparison has not identified a missing per-frame synchronization command to test in Studio. Further physical experiments should specify a new mechanism and a discriminating outcome rather than repeat delay or frame-rate sweeps. Unknown header bytes, generic finish commands, and firmware writes are not experimental fixes justified by the current evidence.

## Firmware search

Inspection covered the 2,123 archive entries and 848 decoded Qt resource entries across the main application and transport library. No identifiable FX240 firmware image or bundled `FirmwareUpgradeTool.exe` was found; the archive's two `.bin` media files have GIF89a signatures. The application references a firmware-update function and tool name. Its embedded ID-COOLING configuration points to a shared MiraBoxCraft firmware index, but a read-only retrieval returned HTTP 404. This establishes an update-related code path, not an available or compatible FX240 update. Opaque or encrypted payloads have not been ruled out, and the controller, framebuffer layout, and panel interface remain unidentified.

[Lumi](https://github.com/waldokilian2/lumi) documents a different architecture: a Space Series 2.1-inch, 480-by-480 USB-CDC panel with stored-media playback. Its documented USB identities and serial protocol differ from the FX240 HID/JPEG interface. It is a comparative reference, not evidence that its commands, firmware, or onboard playback capabilities apply to the FX240.

Only these reviewed conclusions belong in the repository. Captures, recordings, reconstructed images, vendor executables/libraries, disassembly, detailed traces, identifiers, and local paths remain private and excluded.
