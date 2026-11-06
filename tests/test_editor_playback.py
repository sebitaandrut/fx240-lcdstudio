# SPDX-License-Identifier: GPL-3.0-or-later
"""Playback/configuration regressions using synthetic media and forbidden USB."""
from dataclasses import replace
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from PIL import Image
from fx240 import gifstream,typography
from fx240.background import Background
from fx240.focus import Focus
from fx240.scene import default_scene,layer,scene_json,parse_scene
from fx240.session import Settings,Session


def make_gif(path,count=75):
    frames=[Image.new('RGB',(16,16),(index,40,80)) for index in range(count)]
    frames[0].save(path,save_all=True,append_images=frames[1:],duration=40,loop=0)


class EditorPlaybackTests(unittest.TestCase):
    def test_geometry_edits_do_not_reinspect_media_or_revalidate_fonts(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.gif';make_gif(path,5)
            scene=default_scene();scene['layers'].insert(0,layer('media','media',x=0,y=0,width=240,height=240,path=str(path)))
            config=Settings(layout_mode='editor',scene_json=scene_json(scene),font_path=typography.resolve_font())
            forbid=Mock(side_effect=AssertionError('No USB in playback tests'))
            session=Session(config,provider=lambda:[],transport_factory=forbid)
            counts=[];publish=session.publish
            with patch('fx240.gifstream.inspect_gif',wraps=gifstream.inspect_gif) as inspected,patch('fx240.typography.load_font',wraps=typography.load_font) as loaded:
                def capture(event):
                    publish(event)
                    if event['kind']=='frame':
                        counts.append((inspected.call_count,loaded.call_count))
                        if len(counts)<8:
                            scene['layers'][2]['x']=20+len(counts)
                            session.configure(replace(config,scene_json=scene_json(scene)),False)
                        else:session.stop()
                session.publish=capture;session.run()
            self.assertIsNone(session.error);self.assertIsNone(session.config_error)
            self.assertEqual(len(counts),8);self.assertGreaterEqual(counts[0][0],1)
            self.assertTrue(all(value==counts[0] for value in counts))
            forbid.assert_not_called()

    def test_validated_configuration_frame_is_rendered_only_once(self):
        calls=[]
        class Instrumented(Focus):
            def __call__(self,elapsed):calls.append(1);return super().__call__(elapsed)
        session=Session(Settings(),provider=lambda:[],theme_factory=Instrumented)
        frames=[];publish=session.publish
        def capture(event):
            publish(event)
            if event['kind']=='frame':
                frames.append(event)
                if len(frames)<6:session.configure(replace(Settings(),font_weight=350+len(frames)*25),False)
                else:session.stop()
        session.publish=capture;session.run()
        self.assertIsNone(session.error)
        self.assertEqual(len(calls),len(frames))
        self.assertEqual(session.config_revision,5)

    def test_warm_cache_rejects_leaf_links_and_invalidates_same_size_replacements(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'synthetic.gif';make_gif(path,5)
            original=Background(path,0);original.close();before=path.stat()
            replacement=root/'replacement.gif';make_gif(replacement,5)
            os.utime(replacement,ns=(before.st_atime_ns,before.st_mtime_ns))
            os.replace(replacement,path)
            with patch('fx240.gifstream.inspect_gif',wraps=gifstream.inspect_gif) as inspected:
                changed=Background(path,0);changed.close();self.assertGreater(inspected.call_count,0)
            saved=root/'saved.gif';path.rename(saved);path.symlink_to(saved)
            with self.assertRaises(ValueError):Background(path,0)
            path.unlink();os.mkfifo(path)
            with self.assertRaises(ValueError):Background(path,0)
            self.assertEqual(gifstream.statistics()['streams'],0)

    def test_font_validation_cache_rechecks_changed_and_linked_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'font.ttf';path.write_bytes(Path(typography.resolve_font()).read_bytes())
            typography.resolve_font(path)
            with patch('fx240.typography.load_font',wraps=typography.load_font) as loaded:
                typography.resolve_font(path);loaded.assert_not_called()
                path.write_bytes(b'invalid font')
                with self.assertRaises(OSError):typography.resolve_font(path)
            path.unlink();path.symlink_to(typography.resolve_font())
            with self.assertRaises(ValueError):typography.resolve_font(path)

    def test_inspection_cache_is_bounded_and_does_not_block_registry_during_io(self):
        with tempfile.TemporaryDirectory() as folder:
            for index in range(gifstream.MAX_INSPECTION_CACHE+3):
                path=Path(folder)/f'synthetic-{index}.gif';make_gif(path,2)
                asset=Background(path,0);asset.close()
            self.assertLessEqual(len(gifstream._small_assets),gifstream.MAX_INSPECTION_CACHE)
        # Another owner must be able to query/use the registry while input is
        # indexed. Checking ownership here avoids timing-dependent assertions.
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.gif';make_gif(path,2)
            original=gifstream.inspect_gif
            def inspect(payload):
                import threading
                result={}
                reader=threading.Thread(target=lambda:result.update(gifstream.statistics()))
                reader.start();reader.join(2)
                self.assertFalse(reader.is_alive());self.assertNotIn('preparing',result)
                return original(payload)
            with patch('fx240.gifstream.inspect_gif',side_effect=inspect):
                asset=Background(path,0);asset.close()

    def test_smooth_timing_shows_uniform_25fps_gif_frames_at_24fps_in_order(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.gif';make_gif(path,75)
            asset=Background(path,0);paced=Background(path,0,pacing_fps=24)
            try:
                normal=[asset.frame(.001+index/24).getpixel((120,120))[0] for index in range(150)]
                smooth=[paced.frame(.001+index/24).getpixel((120,120))[0] for index in range(150)]
                self.assertNotEqual(normal,[index%75 for index in range(150)])
                self.assertEqual(smooth,[index%75 for index in range(150)])
                exact=[paced.frame(index/24).getpixel((120,120))[0] for index in range(300)]
                self.assertEqual(exact,[index%75 for index in range(300)])
                self.assertAlmostEqual(paced._pacing[1][-1],75/24)
                for invalid in (0,-1,61,float('nan'),True):
                    with self.assertRaises(ValueError):Background(path,0,pacing_fps=invalid)
                self.assertEqual(asset.frame(0).getpixel((120,120)),(0,40,80))
            finally:asset.close();paced.close()
            parsed=parse_scene(scene_json({'version':1,'layers':[layer('a','text')]}))
            self.assertEqual(parsed['layers'][0]['gif_pacing'],'source')
            with self.assertRaises(ValueError):parse_scene(scene_json({'version':1,'layers':[layer('a','text',gif_pacing='script')]}))

    def test_smooth_streaming_uses_bounded_queue_and_preserves_reference_pixels(self):
        import time
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.gif';make_gif(path,121)
            asset=Background(path,0,pacing_fps=24)
            try:
                for index in (0,24,120,121):
                    deadline=time.monotonic()+4
                    while True:
                        value=asset.frame(.001+index/24).getpixel((120,120))[0]
                        if value==index%121:break
                        if time.monotonic()>deadline:self.fail('Paced streaming frame did not arrive')
                        time.sleep(.01)
                self.assertLessEqual(gifstream.statistics()['queued_frames'],12)
            finally:asset.close()
            self.assertEqual(gifstream.statistics()['streams'],0)

    def test_two_streaming_layers_with_distinct_clocks_do_not_reset_each_other(self):
        import time
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.gif';make_gif(path,121)
            source=Background(path,0);smooth=Background(path,0,pacing_fps=24)
            try:
                self.assertIsNot(source._stream.decoder,smooth._stream.decoder)
                self.assertEqual(gifstream.statistics()['streams'],2)
                for index in range(28):
                    elapsed=.001+index/24;deadline=time.monotonic()+3
                    while True:
                        first=source.frame(elapsed).getpixel((120,120))[0]
                        second=smooth.frame(elapsed).getpixel((120,120))[0]
                        if (first,second)==(int(elapsed/.04),index):break
                        if time.monotonic()>deadline:self.fail('Independent clock did not progress')
                        time.sleep(.005)
                self.assertEqual(source._stream.decoder.generation,0)
                self.assertEqual(smooth._stream.decoder.generation,0)
            finally:source.close();smooth.close()
            self.assertEqual(gifstream.statistics()['streams'],0)

    def test_eager_decode_rechecks_budget_on_actual_snapshot_after_classification(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.gif';make_gif(path,2)
            with patch('fx240.gifstream.acquire',return_value=None),patch('fx240.gifstream.MAX_PIXELS',1):
                with self.assertRaises(ValueError):Background(path,0)
