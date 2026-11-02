# SPDX-License-Identifier: GPL-3.0-or-later
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from PIL import Image
from fx240 import media
from fx240.preferences import Preferences, MAX_PREFERENCE_BYTES
from fx240.session import Settings


class InputLimitTests(unittest.TestCase):
    def test_truncated_gif_rejected_as_invalid_data(self):
        stream = io.BytesIO()
        frames = [Image.new('RGB', (1, 1), (i*31,)*3) for i in range(3)]
        frames[0].save(stream, format='GIF', save_all=True, append_images=frames[1:], duration=40)
        data = stream.getvalue()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'truncated.gif'
            path.write_bytes(data[:len(data)//2])
            with self.assertRaises((ValueError, OSError)):
                media.load(path)

    def test_image_size_checked_before_conversion(self):
        image = Mock(width=5000, height=5000)
        with self.assertRaisesRegex(ValueError, 'megapixel'):
            media.canvas(image)
        image.convert.assert_not_called()

    def test_media_byte_limit_checked_before_decoder(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'large.bin'; path.write_bytes(b'x'*20)
            with patch.object(media, 'MAX_FILE_BYTES', 10), patch.object(media.Image, 'open') as opened:
                with self.assertRaisesRegex(ValueError, 'MiB'):
                    media.load(path)
                opened.assert_not_called()

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'FIFO support required')
    def test_media_fifo_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'input'; os.mkfifo(path)
            with self.assertRaisesRegex(ValueError, 'regular file'):
                media.load(path)

    def test_oversized_and_deep_preferences_fall_back(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'settings.json'; store = Preferences(path)
            for data in (b'x'*(MAX_PREFERENCE_BYTES+1), b'['*2000+b'0'+b']'*2000):
                path.write_bytes(data)
                restored, _ = store.load()
                self.assertEqual(restored, Settings())
                self.assertTrue(store.load_error)
