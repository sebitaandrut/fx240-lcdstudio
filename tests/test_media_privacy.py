# SPDX-License-Identifier: GPL-3.0-or-later
import io
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from fx240.media import encode,load


class MediaPrivacyTests(unittest.TestCase):
    def test_lcd_jpeg_does_not_inherit_source_exif(self):
        image=Image.new('RGB',(240,240),'navy')
        exif=Image.Exif();exif[315]='Synthetic author';exif[272]='Synthetic camera'
        image.info['exif']=exif.tobytes()
        with Image.open(io.BytesIO(encode(image))) as sent:
            self.assertFalse(sent.getexif())
            self.assertNotIn('exif',sent.info)

    def test_loading_and_reencoding_a_file_removes_its_exif(self):
        with tempfile.TemporaryDirectory() as home:
            path=Path(home)/'synthetic.jpg'
            exif=Image.Exif();exif[315]='Synthetic author'
            Image.new('RGB',(120,80),'navy').save(path,exif=exif)
            frames=load(path)
            with Image.open(io.BytesIO(encode(frames[0][0]))) as sent:
                self.assertFalse(sent.getexif())
