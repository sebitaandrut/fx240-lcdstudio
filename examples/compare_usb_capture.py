# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare captured FX240 output payloads with a generated image's reports.

Requires tshark and a private, full-length usbmon capture. Prints only a
summary; never embeds captured payloads, serial numbers, or absolute paths.
"""
import argparse
import collections
import hashlib
import json
import subprocess
from pathlib import Path
from fx240.media import encode, load
from fx240.protocol import build_reports


def compare(payloads, reports, frames):
    expected = reports * frames
    differences = []
    for index, (actual, wanted) in enumerate(zip(payloads, expected)):
        if actual != wanted:
            first = next((i for i, (a, b) in enumerate(zip(actual, wanted)) if a != b), None)
            differences.append({'report_index': index, 'actual_bytes': len(actual),
                                'expected_bytes': len(wanted), 'first_different_offset': first})
    return {
        'expected_frames': frames,
        'expected_reports': len(expected),
        'captured_payload_reports': len(payloads),
        'payload_length_counts': dict(sorted(collections.Counter(map(len, payloads)).items())),
        'count_matches': len(payloads) == len(expected),
        'content_mismatches': differences,
        'exact_match': len(payloads) == len(expected) and not differences,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('image', type=Path)
    parser.add_argument('--address', required=True, type=int)
    parser.add_argument('--frames', type=int, default=2)
    parser.add_argument('--quality', type=int, default=85)
    parser.add_argument('--rotation', type=int, choices=(0,90,180,270), default=180)
    args = parser.parse_args()
    if not 1 <= args.address <= 127 or not 1 <= args.frames <= 10000:
        parser.error('Invalid address or frame count')
    image = load(args.image)[0][0]
    reports = build_reports(encode(image, args.quality, args.rotation))
    fields = ['usb.urb_type', 'usbhid.data', 'usb.capdata', 'usb.urb_status', 'frame.len', 'frame.cap_len']
    command = ['tshark', '-r', str(args.capture), '-Y',
               f'usb.device_address == {args.address} && usb.endpoint_address.direction == 0 && usb.endpoint_address.number != 0',
               '-T', 'fields']
    for field in fields:
        command.extend(['-e', field])
    output = subprocess.check_output(command, text=True, timeout=60)
    payloads, completion_statuses = [], []
    truncated_packets = 0
    for line in output.splitlines():
        kind, hid, raw, status, length, captured = (line.split('\t') + ['']*6)[:6]
        kind = kind.strip("'\"")
        if length and captured and int(captured) < int(length):
            truncated_packets += 1
        if kind in ('0x53', 'S') and (hid or raw):
            payloads.append(bytes.fromhex((hid or raw).replace(':', '')))
        if kind in ('0x43', 'C') and status:
            completion_statuses.append(int(status, 0))
    result = compare(payloads, reports, args.frames)
    result.update(capture_sha256=hashlib.sha256(args.capture.read_bytes()).hexdigest(),
                  truncated_output_packets=truncated_packets,
                  completion_status_counts=dict(collections.Counter(completion_statuses)),
                  scope='Output submissions only; bus identity and optical behavior require separate verification.')
    if truncated_packets:
        result['exact_match'] = False
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['exact_match'] else 1)


if __name__ == '__main__':
    main()
