# SPDX-License-Identifier: GPL-3.0-or-later
"""Media viewport scaling with bounded output and synthetic local assets."""
import tempfile
from pathlib import Path
import unittest
from PIL import Image
from fx240.scene import layer,parse_scene,scene_json,SceneRenderer
from fx240.profiles import ProfileStore


class MediaZoomTests(unittest.TestCase):
    def test_legacy_profiles_and_invalid_zoom(self):
        item=layer('image','media',path='/synthetic/image.png');item.pop('media_zoom')
        self.assertEqual(parse_scene(scene_json({'version':1,'layers':[item]}))['layers'][0]['media_zoom'],1)
        for zoom in (True,False,None,'2',[],{},float('nan'),float('inf'),.249,4.001):
            with self.subTest(zoom=zoom),self.assertRaises(ValueError):
                parse_scene(scene_json({'version':1,'layers':[dict(item,media_zoom=zoom)]}))

    def test_static_and_gif_center_crop_zoom_out_and_immutable_frames(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);first=Image.new('RGB',(240,240),'red');first.paste('blue',(80,80,160,160))
            second=Image.new('RGB',(240,240),'yellow');second.paste('cyan',(80,80,160,160))
            for suffix in ('png','gif'):
                path=root/('source.'+suffix)
                if suffix=='gif':first.save(path,save_all=True,append_images=[second],duration=100,loop=0)
                else:first.save(path)
                def render(zoom):
                    return SceneRenderer(provider=lambda:[],scene_json=scene_json({'version':1,'layers':[
                        layer('back','media',x=0,y=0,width=240,height=240,path=str(path),media_zoom=zoom)]}))
                original=render(1);enlarged=render(2);reduced=render(.5)
                try:
                    baseline=original(0)[0].tobytes();image,delay=enlarged(0)
                    self.assertEqual(image.size,(240,240));self.assertEqual(delay,1/24)
                    self.assertEqual(image.getpixel((60,120)),(0,0,255))
                    self.assertEqual(original(0)[0].getpixel((60,120)),(255,0,0))
                    small,_=reduced(0)
                    self.assertEqual(small.getpixel((15,120)),(0,0,0))
                    self.assertEqual(small.getpixel((75,120)),(255,0,0))
                    if suffix=='gif':self.assertEqual(enlarged(.11)[0].getpixel((60,120)),(0,255,255))
                    self.assertEqual(original(0)[0].tobytes(),baseline)
                    self.assertEqual(enlarged.assets['back'].frame(0).size,(240,240))
                finally:original.close();enlarged.close();reduced.close()

    def test_zoom_profile_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profiles.json';store=ProfileStore(path)
            scene={'version':1,'layers':[layer('a','media',path='/synthetic/image.gif',media_zoom=2.25,rotation=90)]}
            identifier=store.save('Synthetic zoom',scene_json(scene))
            loaded=parse_scene(ProfileStore(path).get(identifier)['scene'])
            self.assertEqual(loaded['layers'][0]['media_zoom'],2.25)
            self.assertEqual(loaded['layers'][0]['rotation'],90)
