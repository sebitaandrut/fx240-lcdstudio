# SPDX-License-Identifier: GPL-3.0-or-later
"""Experimental host rate bounds and GIF timing; no physical LCD access."""
from dataclasses import replace
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock
from PIL import Image
from fx240.session import Settings,Session
from fx240.focus import Focus
from fx240.background import Background
from fx240.preferences import Preferences
from fx240.scene import layer,scene_json


class AdvancedFpsTests(unittest.TestCase):
    def test_bounds_defaults_and_preference_roundtrip(self):
        self.assertEqual(Settings().fps,24)
        for rate in (False,True,None,'60',0,-1,60.01,float('inf'),float('nan')):
            with self.subTest(rate=rate),self.assertRaises(ValueError):replace(Settings(),fps=rate).validate()
        with tempfile.TemporaryDirectory() as folder:
            prefs=Preferences(Path(folder)/'settings.json')
            for rate in (1,24,30,48,60):
                settings=replace(Settings(),fps=rate);settings.validate()
                renderer=Focus(fps=rate,provider=lambda:[])
                try:self.assertAlmostEqual(renderer(0)[1],1/rate)
                finally:renderer.close()
                prefs.save(settings,'es','dark');loaded,_=prefs.load()
                self.assertEqual(loaded.fps,rate);self.assertFalse(prefs.warning)

    def test_higher_rates_support_scenes_and_preserve_gif_timing(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.gif'
            Image.new('RGB',(16,16),'red').save(path,save_all=True,
                append_images=[Image.new('RGB',(16,16),'blue')],duration=40,loop=0)
            asset=Background(path,0,pacing_fps=60)
            try:
                self.assertEqual(asset.frame(.02).getpixel((120,120)),(255,0,0))
                self.assertEqual(asset.frame(.05).getpixel((120,120)),(0,0,255))
                self.assertAlmostEqual(asset.duration,.08)
            finally:asset.close()
            scene=scene_json({'version':1,'layers':[layer('media','media',path=str(path),gif_pacing='smooth',media_zoom=2)]})
            for mode in ('focus','editor'):
                transport=Mock(side_effect=AssertionError('No HID access'))
                session=Session(Settings(fps=60,layout_mode=mode,scene_json=scene if mode=='editor' else ''),provider=lambda:[],transport_factory=transport)
                original=session.publish
                def publish(event):
                    original(event)
                    if event['kind']=='frame':session.stop()
                session.publish=publish;session.run()
                self.assertIsNone(session.error);self.assertEqual(session.frames,1)
                transport.assert_not_called()
