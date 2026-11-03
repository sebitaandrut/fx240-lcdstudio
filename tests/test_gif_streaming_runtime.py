# SPDX-License-Identifier: GPL-3.0-or-later
import json
from dataclasses import replace
from pathlib import Path
import tempfile
import time
import unittest
from PIL import Image
from experiments.gif_buffering import generate
from fx240.background import Background
from fx240.media import canvas
from fx240.scene import SceneRenderer,layer,scene_json
from fx240.session import Settings,Session
from fx240.preferences import Preferences
from fx240 import gifstream


class GifStreamingTests(unittest.TestCase):
    def wait(self,condition):
        deadline=time.monotonic()+4
        while not condition() and time.monotonic()<deadline:time.sleep(.01)
        self.assertTrue(condition())

    def test_shared_leases_seek_rewind_and_last_release(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.gif';generate(path,121)
            first=Background(path,0);second=None
            try:
                second=Background(path,0)
                decoder=first._stream.decoder
                self.assertIs(decoder,second._stream.decoder);self.assertEqual(decoder.refs,2)
                with Image.open(path) as reference:
                    for index in (0,100,123,3):
                        elapsed=index*.04+.001
                        def ready():second.frame(elapsed);return decoder.index==index
                        self.wait(ready)
                        reference.seek(index%121)
                        self.assertEqual(second.frame(elapsed).tobytes(),canvas(reference.copy()).tobytes())
                self.assertLessEqual(decoder.peak_queue,12)
                first.close();self.assertTrue(decoder.thread.is_alive())
                second.close();self.assertFalse(decoder.thread.is_alive())
                self.assertEqual(gifstream.statistics()['streams'],0)
            finally:
                first.close()
                if second:second.close()

    def test_failed_scene_constructor_releases_prepared_assets(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.gif';generate(path,121)
            scene={'version':1,'layers':[layer('layer-1','media',path=str(path)),layer('layer-2','text',font_path=str(Path(folder)/'missing.ttf'))]}
            with self.assertRaises((ValueError,OSError)):SceneRenderer(scene_json=scene_json(scene))
            self.assertEqual(gifstream.statistics()['streams'],0)

    def test_session_replacements_keep_one_decoder_and_stop_cleans_up(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.gif';generate(path,121)
            config=Settings(background_path=str(path))
            def forbid(path):raise AssertionError('No physical USB in runtime tests')
            session=Session(config,provider=lambda:[],transport_factory=forbid)
            session.start()
            try:
                self.wait(lambda:session.frames>=3)
                with gifstream._pool_lock:
                    decoder=next(value for key,value in gifstream._pool.items() if key[0] is session.thread)
                for index in range(6):
                    session.configure(replace(config,font_weight=350+index*25),False)
                    self.wait(lambda:session.config_revision==index+1)
                    self.assertTrue(decoder.thread.is_alive());self.assertEqual(decoder.refs,1)
                    self.assertEqual(gifstream.statistics(session.thread)['streams'],1)
                session.suspend(True)
                self.wait(lambda:session.output_released.is_set())
                paused=session.frames;time.sleep(.15)
                self.assertLessEqual(session.frames,paused+1)
                session.suspend(False);self.wait(lambda:session.frames>paused+1)
                scene={'version':1,'layers':[layer('layer-1','media',path=str(path)),layer('layer-2','media',path=str(path))]}
                config=replace(config,layout_mode='editor',scene_json=scene_json(scene))
                session.configure(config,False);self.wait(lambda:session.config_revision==7)
                self.assertEqual(decoder.refs,2)
                bad={'version':1,'layers':[layer('layer-1','media',path=str(path)),layer('layer-2','text',font_path=str(Path(folder)/'missing.ttf'))]}
                session.configure(replace(config,scene_json=scene_json(bad)),False)
                self.wait(lambda:bool(session.config_error))
                self.assertEqual(decoder.refs,2);self.assertEqual(session.config_revision,7)
            finally:session.stop();session.thread.join(4)
            self.assertFalse(session.thread.is_alive());self.assertFalse(decoder.thread.is_alive())
            self.assertEqual(gifstream.statistics(session.thread)['streams'],0)

    def test_legacy_opt_in_is_ignored_and_not_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            prefs=Preferences(Path(folder)/'settings.json')
            prefs.save(Settings(),'es','dark')
            data=json.loads(prefs.path.read_text());self.assertNotIn('gif_buffering',data['display'])
            data['display']['gif_buffering']=True;prefs.path.write_text(json.dumps(data))
            settings,_=prefs.load();self.assertNotIn('gif_buffering',settings.__dict__)

    def test_distinct_assets_release_when_background_is_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            first=Path(folder)/'first.gif';second=Path(folder)/'second.gif'
            generate(first,121);generate(second,122)
            scene={'version':1,'layers':[layer('layer-1','media',path=str(first)),layer('layer-2','media',path=str(second))]}
            session=Session(Settings(layout_mode='editor',scene_json=scene_json(scene)),provider=lambda:[])
            session.start()
            try:
                self.wait(lambda:session.frames>=2)
                self.assertEqual(gifstream.statistics(session.thread)['streams'],2)
                self.assertLessEqual(gifstream.statistics(session.thread)['queued_frames'],24)
                session.configure(Settings(),False)
                self.wait(lambda:session.config_revision==1)
                self.assertEqual(gifstream.statistics(session.thread)['streams'],0)
            finally:session.stop();session.thread.join(4)
            self.assertFalse(session.thread.is_alive())

    def test_transport_close_error_does_not_leak_decoder(self):
        class Synthetic:
            def __init__(self,path):pass
            def __enter__(self):return self
            def send(self,*args):return (0,0)
            def __exit__(self,*args):raise OSError('synthetic close failure')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.gif';generate(path,121)
            config=Settings(background_path=str(path),device='/dev/hidraw999')
            session=Session(config,send=True,provider=lambda:[],transport_factory=Synthetic)
            session.start()
            try:self.wait(lambda:session.frames>=2)
            finally:session.stop();session.thread.join(4)
            self.assertFalse(session.thread.is_alive())
            self.assertEqual(gifstream.statistics(session.thread)['streams'],0)
            self.assertEqual(session.events.get_nowait()['kind'],'stopped')

    def test_saved_long_background_validation_releases_lease(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.gif';generate(path,121)
            prefs=Preferences(Path(folder)/'settings.json')
            prefs.save(Settings(background_path=str(path)),'es','dark')
            restored,_=prefs.load()
            self.assertEqual(restored.background_path,str(path))
            self.assertFalse(prefs.warning)
            self.assertEqual(gifstream.statistics()['streams'],0)

    def test_streaming_budgets_and_metadata_remain_bounded(self):
        from unittest.mock import patch
        import io
        from fx240.media import encode
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.gif';generate(path,121)
            payload=path.read_bytes()
            for name,value in (('MAX_FRAMES',120),('MAX_PIXELS',1),('MAX_WORK',1)):
                with patch('fx240.gifstream.'+name,value):
                    with self.assertRaises(ValueError):gifstream.inspect_gif(payload)
            background=Background(path)
            try:
                jpeg=encode(background.frame(0))
                self.assertNotIn(str(path).encode(),jpeg)
                with Image.open(io.BytesIO(jpeg)) as decoded:self.assertFalse(decoded.getexif())
            finally:background.close()
            self.assertEqual(gifstream.statistics()['streams'],0)
