# SPDX-License-Identifier: GPL-3.0-or-later
"""Built-in LCD compositions, sampled from synthetic readings."""
import unittest
from dataclasses import replace
from pathlib import Path
import tempfile

from PIL import Image, ImageChops, ImageDraw

from fx240.session import Session, Settings
from fx240.preset_scenes import builtin_scene
from fx240.scene import SceneRenderer, effect_layer, parse_scene, scene_json
from fx240.telemetry import Metric


class PresetTests(unittest.TestCase):
    def test_new_decorative_effects_render_static_and_animated_frames(self):
        for shape in ('segments', 'radar'):
            item = effect_layer('sample', shape)
            for motion in ('none', 'signature'):
                payload = scene_json({'version': 1, 'layers': [dict(item, animation=motion)]})
                renderer = SceneRenderer(provider=lambda: [], scene_json=payload)
                try:
                    first, _ = renderer(.2)
                    second, _ = renderer(1.2)
                    self.assertIsNotNone(first.getbbox())
                    self.assertEqual(ImageChops.difference(first, second).getbbox() is not None,
                                     motion == 'signature')
                finally:
                    renderer.close()

    def test_builtins_copy_current_components_and_render_as_scenes(self):
        for design, effects in (
            ('focus', {'disc'}), ('dual', {'disc', 'dual_cpu', 'dual_gpu', 'divider'}),
            ('trace', {'disc', 'trace'}), ('halo', {'disc', 'halo'}),
        ):
            settings = Settings(layout_mode=design, temperature_unit='F',
                                dual_gpu_accent='#ff83b5', dual_gpu_effect_style='rainbow')
            payload = scene_json(builtin_scene(settings))
            scene = parse_scene(payload)
            self.assertEqual({item['effect'] for item in scene['layers'] if item['kind']=='effect'}, effects)
            self.assertEqual(scene['temperature_unit'], 'F')
            if design == 'dual':
                gpu = next(item for item in scene['layers'] if item['id']=='gpu-arc')
                self.assertEqual((gpu['color'], gpu['effect_style']), ('#ff83b5', 'rainbow'))
            renderer = SceneRenderer(provider=lambda: [], scene_json=payload)
            try:
                frame, _ = renderer(0)
                self.assertEqual(frame.size, (240, 240))
                self.assertEqual(renderer.temperature_unit, 'F')
            finally:
                renderer.close()

    def test_halo_shows_only_a_fading_pulse_over_the_background(self):
        with tempfile.TemporaryDirectory() as directory:
            background = Path(directory) / 'synthetic.png'
            Image.new('RGB', (240, 240), '#36536d').save(background)
            settings = Settings(layout_mode='halo', halo_accent='#ee8aff',
                                background_path=str(background), background_dim=0)
            session = Session(settings, provider=lambda: [])
            animated = session.make_theme(settings)
            still = session.make_theme(replace(settings, preset_animation='none'))
            outer_margin = Image.new('RGB', (240, 240), 'white')
            ImageDraw.Draw(outer_margin).ellipse((12, 12, 228, 228), fill='black')
            try:
                reference, _ = still(0)
                # The sides are clear of any stationary ring.
                self.assertEqual(reference.crop((12, 45, 44, 195)).getcolors(), [(4800, (54, 83, 109))])
                changed = False
                for elapsed in (0, .4, .8, 1.2, 1.6, 1.95, 1.979, 2.2):
                    frame, _ = animated(elapsed)
                    difference = ImageChops.difference(reference, frame)
                    changed |= difference.getbbox() is not None
                    self.assertIsNone(ImageChops.multiply(difference, outer_margin).getbbox())
                self.assertTrue(changed)
                faded, _ = animated(1.97999)
                self.assertIsNone(ImageChops.difference(reference, faded).getbbox())
            finally:
                animated.close()
                still.close()

    def test_dual_gpu_accent_changes_only_its_side(self):
        original = Settings(layout_mode='dual')
        recolored = replace(original, dual_gpu_accent='#ff83b5')
        for animation in ('signature', 'none'):
            before = Session(original, provider=lambda: []).make_theme(replace(original, preset_animation=animation))
            after = Session(recolored, provider=lambda: []).make_theme(replace(recolored, preset_animation=animation))
            try:
                left, _ = before(.7)
                right, _ = after(.7)
                difference = ImageChops.difference(left, right)
                self.assertIsNone(difference.crop((0, 0, 120, 240)).getbbox())
                self.assertIsNotNone(difference.crop((120, 0, 240, 240)).getbbox())
            finally:
                before.close()
                after.close()

    def test_renderers_animate_between_sensor_samples(self):
        for design in ('dual', 'trace', 'halo'):
            with self.subTest(design=design):
                settings = Settings(layout_mode=design, fps=30, temperature_unit='F')
                session = Session(settings, provider=lambda: [
                    Metric('ct', 'CPU synthetic', 46.5, 'C', 'synthetic'),
                    Metric('gt', 'GPU synthetic', 40, 'C', 'synthetic'),
                ])
                renderer = session.make_theme(settings)
                try:
                    renderer(0)
                    first, delay = renderer(1)
                    sequence = session.snapshot.sequence
                    later, _ = renderer(1.5)
                    self.assertEqual(first.size, (240, 240))
                    self.assertEqual(delay, 1 / 30)
                    self.assertNotEqual(first.tobytes(), later.tobytes())
                    self.assertEqual(session.snapshot.sequence, sequence)
                finally:
                    renderer.close()

    def test_trace_history_is_bounded_and_does_not_join_suspension_gaps(self):
        settings = Settings(layout_mode='trace')
        session = Session(settings, provider=lambda: [Metric('ct', 'CPU synthetic', 46.5, 'C', 'synthetic')])
        renderer = session.make_theme(settings)
        try:
            for elapsed in range(75):
                renderer.sample(elapsed)
            self.assertEqual(len(renderer.history), 60)
            self.assertEqual(renderer.history[0][0], 15)
            renderer.sample(90)
            self.assertEqual(list(renderer.history), [(90, 46.5)])
        finally:
            renderer.close()
