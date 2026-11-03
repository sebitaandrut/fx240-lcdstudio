# SPDX-License-Identifier: GPL-3.0-or-later
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from fx240.background import Background,cached_frames
from fx240.focus import Focus
from fx240.media import encode
from fx240.preferences import Preferences
from fx240.session import Settings,Session
from fx240.systemfonts import catalog
from fx240.telemetry import Metric


def synthetic_metrics():
    return [Metric('ct','CPU synthetic',45.2,'C','synthetic'),Metric('cf','CPU synthetic',3800,'MHz','synthetic'),
            Metric('gt','GPU synthetic',38.1,'C','synthetic'),Metric('gf','GPU synthetic',1600,'MHz','synthetic')]


class CompositionTests(unittest.TestCase):
    def tearDown(self):cached_frames.cache_clear()

    def test_background_timing_dimming_and_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.gif'
            first=Image.new('RGB',(240,240),'red');second=Image.new('RGB',(240,240),'blue')
            first.save(path,save_all=True,append_images=[second],duration=[100,200],loop=0,comment=b'synthetic metadata')
            background=Background(path,.5)
            self.assertEqual(background.frame(.05).getpixel((120,120)),(127,0,0))
            self.assertEqual(background.frame(.15).getpixel((120,120)),(0,0,127))
            self.assertEqual(background.frame(.35).getpixel((120,120)),(127,0,0))
            theme=Focus(provider=synthetic_metrics,background_path=str(path),background_dim=0,animation='none')
            image,_=theme(.05)
            self.assertGreater(image.getpixel((120,32))[0],200)
            # The source comment/path never enters the composed JPEG metadata.
            payload=encode(image)
            self.assertNotIn(b'synthetic metadata',payload)
            self.assertNotIn(str(path).encode(),payload)
            with Image.open(io.BytesIO(payload)) as decoded:self.assertFalse(decoded.getexif())

    def test_background_frame_budget_and_invalid_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'budget.gif'
            frames=[Image.new('RGB',(1,1),(i,0,0)) for i in range(121)]
            frames[0].save(path,save_all=True,append_images=frames[1:],duration=40)
            with self.assertRaisesRegex(ValueError,'120'):Background(path)
            path.write_bytes(b'not image data')
            with self.assertRaisesRegex(ValueError,'could not be loaded'):Background(path)
        for dim in (-.1,1,float('nan')):
            with self.assertRaises(ValueError):Background(None,dim)

    def test_effects_animate_while_static_and_numbers_remain_stable(self):
        for effect in ('comet','orbit','pulse','none'):
            theme=Focus(provider=synthetic_metrics,animation=effect)
            theme(0)
            first,_=theme(.65);second,_=theme(.95)
            if effect=='none':self.assertEqual(first.tobytes(),second.tobytes())
            else:self.assertNotEqual(first.tobytes(),second.tobytes(),effect)
            # Animation stays outside the central numeric content.
            self.assertEqual(first.crop((50,60,190,155)).tobytes(),second.crop((50,60,190,155)).tobytes())
        with self.assertRaises(ValueError):replace(Settings(),animation='unknown').validate()

    def test_private_preferences_roundtrip_and_missing_background_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'synthetic.png';Image.new('RGB',(4,4),'navy').save(source)
            path=Path(folder)/'settings.json';store=Preferences(path)
            settings=replace(Settings(),animation='orbit',background_path=str(source),background_dim=.4)
            store.save(settings,'es','dark')
            self.assertEqual(store.load()[0],settings)
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            source.unlink();restored,_=store.load()
            self.assertIsNone(restored.background_path)
            self.assertEqual(restored.animation,'orbit')
            self.assertTrue(store.warning)

    def test_bad_live_background_keeps_previous_worker_and_renderer(self):
        session=Session(Settings(),provider=synthetic_metrics)
        events=[];publish=session.publish
        def capture(event):
            publish(event)
            if event['kind']=='frame':
                events.append(event)
                if len(events)==1:session.configure(replace(Settings(),background_path='/missing/synthetic-background'))
                elif len(events)==2:session.stop()
        session.publish=capture;session.run()
        self.assertIsNone(session.error)
        self.assertIsNone(session.settings.background_path)
        self.assertTrue(session.config_error)
        self.assertEqual(events[0]['display_values'],events[1]['display_values'])

    def test_font_catalog_rejects_unsupported_records_without_commands_from_input(self):
        text='Zeta\tRegular\t/usr/share/fonts/example.ttf\t0\nAlpha\tLight\t/usr/share/fonts/alpha.otf\t0\n'
        text+='Collection\tRegular\t/usr/share/fonts/example.ttc\t1\nRelative\tRegular\trelative.ttf\t0\ninvalid\n'
        with patch('fx240.systemfonts.fontconfig_output',return_value=text.encode()):
            self.assertEqual(catalog(),[('Alpha · Light','/usr/share/fonts/alpha.otf'),('Zeta · Regular','/usr/share/fonts/example.ttf')])
        with patch('fx240.systemfonts.fontconfig_output',side_effect=OSError('synthetic path detail')):
            with self.assertRaisesRegex(ValueError,'^System font discovery failed$'):catalog()
