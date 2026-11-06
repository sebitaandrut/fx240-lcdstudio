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
from fx240.scene import parse_scene,scene_json,default_scene,layer,SceneRenderer,gradient_surface
from fx240.focus import font,resolve_font
from fx240.preferences import Preferences
from fx240.profiles import ProfileStore
from fx240.session import Settings,Session
from fx240.telemetry import Metric
from fx240.media import encode


def metrics():
    return [Metric('ct','CPU synthetic',45.25,'C','synthetic'),Metric('cf','CPU synthetic',3900,'MHz','synthetic'),Metric('gt','GPU synthetic',38,'C','synthetic'),Metric('gf','GPU synthetic',1600,'MHz','synthetic')]


class SceneTests(unittest.TestCase):
    def test_gradient_is_bounded_static_and_needs_no_asset(self):
        gradient = layer('glow', 'gradient', x=0, y=0, width=240, height=240,
                         color='#ff0000', gradient_color='#0000ff', opacity=.5)
        payload = scene_json({'version': 1, 'layers': [gradient]})
        parsed = parse_scene(payload)['layers'][0]
        self.assertIsNone(parsed['path'])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'profiles.json'
            identifier = ProfileStore(path).save('Gradient', payload)
            self.assertEqual(parse_scene(ProfileStore(path).get(identifier)['scene'])['layers'][0], parsed)
        with self.assertRaises(ValueError):
            parse_scene(scene_json({'version': 1, 'layers': [{**gradient, 'gradient_color': '/test/image.png'}]}))
        with self.assertRaises(ValueError):
            parse_scene(scene_json({'version': 1, 'layers': [gradient, {**gradient, 'id': 'second'}]}))
        with self.assertRaises(ValueError):
            parse_scene(scene_json({'version': 1, 'layers': [layer('label', 'text', gradient_color='#0000ff')]}))
        renderer = SceneRenderer(scene_json=payload, provider=metrics)
        try:
            frame, _ = renderer(0)
            self.assertEqual(frame.size, (240, 240))
            red = frame.getpixel((46, 192))
            blue = frame.getpixel((199, 55))
            self.assertGreater(red[0], red[2] + 80)
            self.assertGreater(blue[2], blue[0] + 80)
            self.assertLessEqual(max(red + blue), 128)
            self.assertEqual(renderer(.5)[0].tobytes(), frame.tobytes())
            self.assertFalse(renderer.assets)
        finally:
            renderer.close()

    def test_gradient_modes_directions_and_legacy_defaults(self):
        legacy = {'id': 'glow', 'kind': 'gradient', 'color': '#ff0000', 'gradient_color': '#0000ff',
                  'x': 0, 'y': 0, 'width': 240, 'height': 240}
        scene = {'version': 1, 'layers': [legacy]}
        item = parse_scene(scene_json(scene))['layers'][0]
        self.assertEqual((item['gradient_style'], item['gradient_angle']), ('aurora', 0))
        for invalid in ({'gradient_style': 'invalid'}, {'gradient_angle': 360}, {'gradient_angle': True}):
            with self.assertRaises(ValueError):
                parse_scene(scene_json({**scene, 'layers': [{**legacy, **invalid}]}))
        for style, angle, first, second in (
            ('linear', 0, (.1, .5), (.9, .5)),
            ('linear', 90, (.5, .1), (.5, .9)),
            ('radial', 0, (.5, .5), (.95, .5)),
            ('aurora', 180, (.81, .20), (.17, .77)),
        ):
            with self.subTest(style=style, angle=angle):
                image = gradient_surface({**item, 'gradient_style': style, 'gradient_angle': angle})
                r = image.getpixel((int(image.width*first[0]), int(image.height*first[1])))
                b = image.getpixel((int(image.width*second[0]), int(image.height*second[1])))
                self.assertGreater(r[0], r[2]+100)
                self.assertGreater(b[2], b[0]+100)

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
