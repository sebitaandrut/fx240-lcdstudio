# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded property-based input checks; no real HID or personal configuration.

Run with PYTHONPATH=src after installing packaging/requirements-security.txt and Pillow.
These properties are not exhaustive native decoder/font fuzzing or a hardware test.
"""
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
from hypothesis import given, settings, strategies as st
from PIL import Image, UnidentifiedImageError
from fx240.media import load
from fx240.preferences import Preferences
from fx240.protocol import build_reports
from fx240.transport import Hidraw

PROPERTY = settings(max_examples=100, deadline=None, database=None, derandomize=True)
scalar = st.one_of(st.none(), st.booleans(), st.integers(-10000, 10000),
                   st.floats(allow_nan=False, allow_infinity=False), st.text(max_size=32))
json_value = st.recursive(scalar, lambda child: st.one_of(
    st.lists(child, max_size=5), st.dictionaries(st.text(max_size=12), child, max_size=5)),
    max_leaves=15)


preference_payload = st.one_of(json_value, st.fixed_dictionaries({
    'version': st.sampled_from([0, 1, 2, None, '1']),
    'display': st.one_of(json_value, st.dictionaries(st.sampled_from([
        'fps', 'quality', 'delay_ms', 'rotation', 'font_weight', 'comet_speed',
        'accent', 'comet_style', 'temperature_decimals', 'temperature_unit', 'device'
    ]), scalar, max_size=8)),
    'application': st.one_of(json_value, st.fixed_dictionaries({
        'language': scalar, 'theme': scalar
    }))
}))


class InputProperties(unittest.TestCase):
    @PROPERTY
    @given(st.binary(max_size=8192))
    def test_framing_preserves_payload_and_declared_length(self, payload):
        jpeg = b'\xff\xd8' + payload + b'\xff\xd9'
        reports = build_reports(jpeg)
        raw = b''.join(reports)
        self.assertTrue(all(len(report) == 1024 for report in reports))
        self.assertEqual(int.from_bytes(raw[8:12], 'big'), 32 + len(jpeg))
        self.assertEqual(raw[32:32 + len(jpeg)], jpeg)
        self.assertFalse(any(raw[32 + len(jpeg):]))

    @PROPERTY
    @given(st.text(max_size=128).filter(lambda value: re.fullmatch(r'/dev/hidraw[0-9]+', value) is None))
    def test_other_paths_never_reach_device_open(self, path):
        with patch('fx240.transport.os.open') as opened:
            with self.assertRaises(ValueError):
                with Hidraw(path):
                    self.fail('Rejected path was opened')
            opened.assert_not_called()

    @PROPERTY
    @given(preference_payload)
    def test_malformed_private_preferences_keep_valid_defaults(self, value):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'settings.json'
            path.write_text(json.dumps(value), encoding='utf-8')
            settings_value, application = Preferences(path).load()
            settings_value.validate()
            self.assertIn(application['language'], ('en', 'es'))
            self.assertIn(application['theme'], ('dark', 'light'))

    @PROPERTY
    @given(st.integers(1, 24), st.integers(1, 24), st.integers(1, 4),
           st.tuples(st.integers(0, 255), st.integers(0, 255), st.integers(0, 255)))
    def test_small_gif_and_truncation_are_bounded(self, width, height, count, color):
        frames = [Image.new('RGB', (width, height), tuple((v+i*31)%256 for v in color))
                  for i in range(count)]
        stream = io.BytesIO()
        frames[0].save(stream, format='GIF', save_all=True, append_images=frames[1:],
                       duration=40, loop=0)
        data = stream.getvalue()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'synthetic.gif'
            path.write_bytes(data)
            loaded = load(path, max_frames=4)
            self.assertTrue(1 <= len(loaded) <= count)
            self.assertTrue(all(image.size == (240, 240) and delay > 0
                                for image, delay in loaded))
            path.write_bytes(data[:len(data)//2])
            try:
                partial = load(path, max_frames=4)
            except (OSError, ValueError, SyntaxError, UnidentifiedImageError):
                pass  # A damaged decoder input is expected to be rejected.
            else:
                self.assertLessEqual(len(partial), 4)


if __name__ == '__main__':
    unittest.main(verbosity=2)
