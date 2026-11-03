# SPDX-License-Identifier: GPL-3.0-or-later
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock
from PIL import Image
from fx240.scene import parse_scene,scene_json,default_scene,layer,SceneRenderer
from fx240.focus import font,resolve_font
from fx240.preferences import Preferences
from fx240.session import Settings,Session
from fx240.telemetry import Metric
from fx240.media import encode


def metrics():
    return [Metric('ct','CPU synthetic',45.25,'C','synthetic'),Metric('cf','CPU synthetic',3900,'MHz','synthetic'),Metric('gt','GPU synthetic',38,'C','synthetic'),Metric('gf','GPU synthetic',1600,'MHz','synthetic')]


class SceneTests(unittest.TestCase):
    def test_declarative_schema_rejects_unknown_fields_and_resources(self):
        bad=[{'version':True,'layers':[]},{'version':1,'layers':[layer('a','script')]},
             {'version':1,'layers':[layer('a','text',qml='arbitrary code')]},
             {'version':1,'layers':[layer('a','media',path='https://example.invalid/image.gif')]},
             {'version':1,'layers':[layer('a','text',font_path='relative.ttf')]},
             {'version':1,'layers':[layer('a','text',size=9000)]},
             {'version':1,'layers':[layer('a','text',x=239)]},
             {'version':1,'layers':[layer('a','text',opacity=float('nan'))]},
             {'version':1,'layers':[layer('a','text',text='line\nbreak')]},
             {'version':1,'layers':[layer('a','text'),layer('a','text')]},
             {'version':1,'layers':[layer('a'+str(i),'text') for i in range(17)]},
             {'version':1,'layers':[layer('a'+str(i),'media',path='/synthetic/example.png') for i in range(3)]}]
        for value in bad:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):parse_scene(scene_json(value))
        for value in ('x'*24577,'['*2000+'0'+']'*2000):
            with self.assertRaises(ValueError):parse_scene(value)
        self.assertFalse(any(item['kind']=='arc' for item in parse_scene()['layers']))

    def test_layer_order_opacity_and_metadata_are_pixel_only(self):
        with tempfile.TemporaryDirectory() as folder:
            red=Path(folder)/'red.png';blue=Path(folder)/'blue.png'
            Image.new('RGB',(10,10),'red').save(red)
            Image.new('RGB',(10,10),'blue').save(blue)
            items=[layer('red','media',x=0,y=0,width=240,height=240,path=str(red)),
                   layer('blue','media',x=120,y=0,width=120,height=240,path=str(blue),opacity=.5)]
            renderer=SceneRenderer(scene_json=scene_json({'version':1,'layers':items}),provider=metrics)
            image,_=renderer(0)
            self.assertEqual(image.getpixel((60,120)),(255,0,0))
            pixel=image.getpixel((180,120));self.assertLess(abs(pixel[0]-127),2);self.assertLess(abs(pixel[2]-127),2)
            payload=encode(image)
            self.assertNotIn(str(red).encode(),payload)
            with Image.open(io.BytesIO(payload)) as output:self.assertFalse(output.getexif())

    def test_values_are_sampled_once_and_temperature_units_match(self):
        provider=Mock(return_value=metrics())
        renderer=SceneRenderer(provider=provider,temperature_unit='F')
        for elapsed in (0,.2,.9):renderer(elapsed)
        self.assertEqual(provider.call_count,1)
        self.assertEqual(renderer.text_value(layer('test','metric')),'113.5°F')
        renderer(1.1);self.assertEqual(provider.call_count,2)

    def test_private_roundtrip_preserves_missing_asset_references_for_repair(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.png';Image.new('RGB',(4,4),'navy').save(path)
            payload=scene_json({'version':1,'layers':[layer('a','media',x=0,y=0,width=240,height=240,path=str(path))]})
            settings=replace(Settings(),layout_mode='editor',scene_json=payload)
            store=Preferences(Path(folder)/'settings.json');store.save(settings,'es','dark')
            self.assertEqual(store.load()[0],settings)
            path.unlink();restored,_=store.load()
            self.assertEqual(restored.scene_json,payload)
            self.assertEqual(store.issues,[])

    def test_live_layout_switch_keeps_transport_and_valid_renderer(self):
        device=Mock();device.send.return_value=(1,[])
        manager=Mock();manager.__enter__=Mock(return_value=device);manager.__exit__=Mock(return_value=False)
        factory=Mock(return_value=manager)
        settings=Settings(device='/dev/fake')
        session=Session(settings,send=True,provider=metrics,transport_factory=factory)
        frames=[];publish=session.publish
        def capture(event):
            publish(event)
            if event['kind']=='frame':
                frames.append(session.settings.layout_mode)
                if len(frames)==1:session.configure(replace(settings,layout_mode='editor'))
                elif len(frames)==2:session.configure(settings)
                else:session.stop()
        session.publish=capture;session.run()
        self.assertEqual(frames,['focus','editor','focus'])
        self.assertIsNone(session.error);self.assertIsNone(session.config_error)
        factory.assert_called_once();manager.__exit__.assert_called_once()

    def test_font_cache_does_not_share_native_faces_between_threads(self):
        path=resolve_font();faces=[]
        def load():
            first=font(path,18);self.assertIs(first,font(path,18));faces.append(first)
        for _ in range(2):
            thread=threading.Thread(target=load);thread.start();thread.join()
        self.assertIsNot(faces[0],faces[1])
