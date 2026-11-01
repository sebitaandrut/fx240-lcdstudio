# SPDX-License-Identifier: GPL-3.0-or-later
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from PIL import Image, ImageDraw
from fx240 import cli, dashboard, overlay
from fx240.telemetry import Metric


class OverlayTests(unittest.TestCase):
    def test_sampling_independent_of_frame_rate_and_removed_sensor(self):
        metric = Metric('cpu', 'CPU Tctl', 42, 'C', 'fake')
        provider = Mock(side_effect=[[metric], []])
        source = lambda t: (Image.new('RGB', (240,240)), .2)
        wrapped = overlay.TelemetryOverlay(source, provider=provider)
        with patch.object(overlay, 'render', return_value=source(0)[0]) as render:
            for t in (0, .2, .4, .8, 1.01, 1.2):
                self.assertEqual(wrapped(t)[1], .2)
        self.assertEqual(provider.call_count, 2)
        self.assertEqual(render.call_args_list[3].args[1], [metric])
        self.assertEqual(render.call_args_list[4].args[1], [])

    def test_preserves_source_and_central_animation(self):
        original = Image.new('RGB', (240,240), 'red')
        before = original.tobytes()
        first = overlay.render(original, [])
        second = overlay.render(Image.new('RGB', (240,240), 'blue'), [])
        self.assertEqual(original.tobytes(), before)
        self.assertEqual(first.getpixel((120,120)), (255,0,0))
        self.assertEqual(second.getpixel((120,120)), (0,0,255))
        self.assertEqual(first.getpixel((0,0)), (0,0,0))

    def test_overlay_text_fits_circle_and_missing_key_is_na(self):
        boxes, texts = [], []
        original = ImageDraw.ImageDraw.text
        def record(draw, xy, text, *args, **kwargs):
            texts.append(text)
            boxes.append(draw.textbbox(xy, text, font=kwargs['font']))
            return original(draw, xy, text, *args, **kwargs)
        metrics = [Metric(str(i), 'CPU ' + 'long label '*20, 123456.7, 'MHz', 'fake') for i in range(3)]
        with patch.object(ImageDraw.ImageDraw, 'text', record):
            overlay.render(Image.new('RGB',(240,240)), metrics, ['0','1','2','missing'])
        self.assertIn('Sensor N/A', texts)
        self.assertEqual(len(texts),4)
        for left,top,right,bottom in boxes:
            for x in (left,right):
                for y in (top,bottom):
                    self.assertLessEqual((x-dashboard.CENTER)**2+(y-dashboard.CENTER)**2, dashboard.TEXT_RADIUS**2)

    def test_cli_gif_overlay_preserves_timing_and_motion(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'demo.gif'
            Image.new('RGB',(240,240),'red').save(path,save_all=True,
                append_images=[Image.new('RGB',(240,240),'blue')],duration=[80,120],loop=0)
            def play(frame_at, *args):
                first, a = frame_at(0)
                second, b = frame_at(.09)
                self.assertEqual((a,b),(.08,.12))
                self.assertEqual(first.getpixel((120,120)),(255,0,0))
                self.assertEqual(second.getpixel((120,120)),(0,0,255))
                return []
            with patch.object(cli,'play',side_effect=play), patch.object(overlay,'collect',return_value=[]) as collect, patch('sys.stdout',new_callable=io.StringIO):
                cli.main(['gif',str(path),'--overlay'])
            collect.assert_called_once()

    def test_overlay_rejects_non_media_modes(self):
        for mode in ('sensors','dashboard'):
            with patch('sys.stderr',new_callable=io.StringIO), self.assertRaises(SystemExit) as error:
                cli.main([mode,'--overlay'])
            self.assertEqual(error.exception.code,2)


if __name__ == '__main__':
    unittest.main()
