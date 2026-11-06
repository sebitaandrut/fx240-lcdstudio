# SPDX-License-Identifier: GPL-3.0-or-later
"""Deterministic frame-delivery scheduling and stop/pause/suspend safeguards."""
import unittest
from unittest.mock import patch
from PIL import Image
from fx240.session import Session,Settings


class DeliveryPacingTests(unittest.TestCase):
    def exercise(self,action=None,origin=0.0):
        now=[origin];starts=[];renders=[];frames=[];closed=[];opened=[]
        costs=(.001,.015,.002,.020)
        class Theme:
            def __init__(self,*args,**kwargs):pass
            def __call__(self,elapsed):
                renders.append(elapsed);now[0]+=costs[(len(renders)-1)%len(costs)]
                return Image.new('RGB',(240,240),'navy'),1/24
        class Device:
            def __init__(self,path):self.asserted=path=='/dev/hidraw999'
            def __enter__(self):
                assert self.asserted;opened.append(1);return self
            def __exit__(self,*args):closed.append(1)
            def send(self,*args):starts.append(now[0]);now[0]+=.008;return 8,[]
        session=Session(Settings(device='/dev/hidraw999'),send=True,provider=lambda:[],transport_factory=Device,theme_factory=Theme)
        class Control:
            stopped=False;triggered=False
            def is_set(self):return self.stopped
            def set(self):self.stopped=True
            def wait(self,delay):
                if action and delay>0 and not self.triggered:
                    self.triggered=True
                    if action=='stop':now[0]+=delay/2;self.set();return True
                    if action=='pause':session.set_output(False)
                    if action=='suspend':session.suspend(True)
                elif action=='suspend' and session.suspended.is_set():session.suspend(False)
                now[0]+=delay
                return self.stopped
        session.stop_event=Control();publish=session.publish
        def capture(event):
            publish(event)
            if event['kind']=='frame':
                frames.append(event)
                if len(frames)>=(2 if action else 4):session.stop()
        session.publish=capture
        with patch('fx240.session.time.monotonic',side_effect=lambda:now[0]):session.run()
        self.assertIsNone(session.error)
        return session,starts,renders,frames,opened,closed

    def test_variable_render_cost_does_not_shift_scheduled_usb_bursts(self):
        session,starts,renders,frames,opened,closed=self.exercise()
        self.assertEqual(len(frames),4)
        for index in range(1,4):
            self.assertAlmostEqual(starts[index],index/24)
            self.assertAlmostEqual(renders[index],index/24)
        for event,expected in zip(frames,(9,23,10,28)):
            # Intentional deadline waiting is excluded from processing time.
            self.assertAlmostEqual(event['pipeline_ms'],expected)
        self.assertEqual((len(opened),len(closed)),(1,1))

    def test_stop_during_alignment_discards_the_prepared_frame_and_sends_standby(self):
        session,starts,renders,frames,opened,closed=self.exercise('stop')
        self.assertEqual(len(renders),2);self.assertEqual(len(frames),1)
        self.assertEqual(len(starts),2) # displayed frame, then standby
        self.assertTrue(session.output_released.is_set())
        self.assertEqual((len(opened),len(closed)),(1,1))

    def test_pause_during_alignment_prevents_another_animation_upload(self):
        session,starts,renders,frames,opened,closed=self.exercise('pause')
        self.assertEqual([event['sent'] for event in frames],[True,False])
        self.assertEqual(len(starts),2) # displayed frame, then standby
        self.assertFalse(session.output_requested)
        self.assertTrue(session.output_released.is_set())
        self.assertEqual((len(opened),len(closed)),(1,1))

    def test_sleep_during_alignment_releases_before_resuming_output(self):
        session,starts,renders,frames,opened,closed=self.exercise('suspend')
        self.assertEqual([event['sent'] for event in frames],[True,True])
        self.assertEqual(len(renders),3) # sleeping discards one prepared frame
        self.assertEqual((len(opened),len(closed)),(2,2))
        self.assertTrue(session.output_released.is_set())

    def test_large_clock_origin_does_not_move_animation_ticks_below_frame_boundaries(self):
        origin=1000000.0
        session,starts,renders,frames,opened,closed=self.exercise(origin=origin)
        for index in range(1,4):
            self.assertEqual(renders[index],index/24)
            self.assertAlmostEqual(starts[index]-origin,index/24)
