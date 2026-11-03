# SPDX-License-Identifier: GPL-3.0-or-later
"""Experimental decoder tests; no device or system telemetry access."""
import io
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from PIL import Image,ImageDraw
from experiments.gif_buffering import Buffered,Eager,inspect,verify,generate


class GifBufferingTests(unittest.TestCase):
    def payload(self):
        frames=[]
        for index in range(9):
            frame=Image.new('RGBA',(48,48),(0,0,0,0))
            ImageDraw.Draw(frame).rectangle((index*3,5,index*3+10,20),fill=(255,index*20,100,255))
            frames.append(frame)
        output=io.BytesIO()
        frames[0].save(output,format='GIF',save_all=True,append_images=frames[1:],duration=[40,80,120]*3,disposal=[1,2,3]*3,loop=0,optimize=True)
        return output.getvalue()

    def test_disposal_timing_and_two_loops_match_reference(self):
        payload=self.payload();size,durations=inspect(payload)
        self.assertEqual(size,(48,48));self.assertEqual(len(durations),9)
        self.assertEqual(durations[:3],[.04,.08,.12])
        self.assertEqual(verify(payload,9),{'frames_checked':18,'loops_checked':2,'reference_matches':True})

    def test_queue_is_bounded_and_close_releases_worker(self):
        player=Buffered(self.payload(),9,capacity=2)
        time.sleep(.1)
        self.assertLessEqual(player.queue.qsize(),2)
        self.assertLessEqual(player.peak_queue,2)
        frame,index=player.frame(0)
        self.assertEqual(frame.size,(240,240));self.assertEqual(index,0)
        player.close();self.assertFalse(player.thread.is_alive());self.assertTrue(player.queue.empty())
        with self.assertRaises(ValueError):Buffered(self.payload(),9,capacity=0)
        with self.assertRaises(ValueError):Buffered(self.payload(),0)
        with self.assertRaises(ValueError):Eager(self.payload(),2000)

    def test_input_limits_and_generation_does_not_overwrite(self):
        payload=self.payload()
        with patch('experiments.gif_buffering.MAX_FRAMES',3):
            with self.assertRaises(ValueError):inspect(payload)
        with patch('experiments.gif_buffering.MAX_DECODE_WORK',100):
            with self.assertRaises(ValueError):inspect(payload)
        output=io.BytesIO();Image.new('RGB',(8,8)).save(output,format='PNG')
        with self.assertRaises(ValueError):inspect(output.getvalue())
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.gif';generate(path,121)
            self.assertEqual(len(inspect(path.read_bytes())[1]),121)
            with self.assertRaises(FileExistsError):generate(path,1)
