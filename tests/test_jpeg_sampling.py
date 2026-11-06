# SPDX-License-Identifier: GPL-3.0-or-later
"""Session-only sampling experiment preserves framing and private preferences."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageDraw,JpegImagePlugin
from fx240.media import encode
from fx240.preferences import Preferences
from fx240.protocol import build_reports
from fx240.session import Session,Settings


class JpegSamplingTests(unittest.TestCase):
    def test_default_stays_444_and_experiment_is_420_without_source_metadata(self):
        image=Image.new('RGB',(240,240),'#ef409a')
        ImageDraw.Draw(image).ellipse((30,40,160,170),fill='#f2ea43')
        image.info.update(comment=b'private source comment',exif=b'private source exif')
        encoded=[]
        for sampling in (0,2):
            data=encode(image,65,180,subsampling=sampling);encoded.append(data)
            with Image.open(io.BytesIO(data)) as decoded:
                decoded.load()
                self.assertEqual(JpegImagePlugin.get_sampling(decoded),sampling)
                self.assertEqual(decoded.size,(240,240))
                self.assertNotIn('exif',decoded.info)
                self.assertNotIn('comment',decoded.info)
            reports=build_reports(data)
            self.assertTrue(all(len(r)==1024 for r in reports))
            joined=b''.join(reports)
            self.assertEqual(joined[32:32+len(data)],data)
        self.assertEqual(encode(image,65,180),encoded[0])
        for invalid in (True,1,3,'2',None):
            with self.assertRaises(ValueError):encode(image,subsampling=invalid)

    def test_output_and_standby_use_sampling_after_live_configuration(self):
        uploads=[]
        class Transport:
            def __init__(self,*args):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def send(self,reports,delay):
                data=b''.join(reports);end=int.from_bytes(data[8:12],'big')
                with Image.open(io.BytesIO(data[32:end])) as image:
                    uploads.append(JpegImagePlugin.get_sampling(image))
                return 0,[]
        session=Session(Settings(device='/dev/hidraw999'),send=True,provider=lambda:[],transport_factory=Transport,jpeg_subsampling=2)
        publish=session.publish
        def capture(event):
            publish(event)
            if event['kind']=='frame':
                if session.frames==1:session.configure(Settings(device='/dev/hidraw999',font_weight=400))
                else:session.stop()
        session.publish=capture;session.run()
        self.assertIsNone(session.error)
        self.assertIsNone(session.config_error)
        self.assertEqual(uploads,[2,2,2])
        with tempfile.TemporaryDirectory() as folder:
            store=Preferences(Path(folder)/'settings.json');store.save(session.settings,'en','dark')
            saved=json.loads(store.path.read_text())
            self.assertNotIn('jpeg_subsampling',saved['display'])
            loaded,_=store.load()
            self.assertEqual(Session(loaded,provider=lambda:[]).jpeg_subsampling,0)
        for invalid in (True,1,3,'2',None):
            with self.assertRaises(ValueError):Session(Settings(),jpeg_subsampling=invalid)

    def test_experimental_cli_flag_is_rejected_outside_gui(self):
        from contextlib import redirect_stderr
        from fx240.cli import main
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as raised:
            main(['sensors','--experimental-jpeg-420'])
        self.assertEqual(raised.exception.code,2)


if __name__=='__main__':unittest.main()
