"""Checks for experimental instruments; no USB device is opened."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

TOOLS=Path(__file__).resolve().parents[1]/'tools'
sys.path.insert(0,str(TOOLS))
from benchmark_stream import diagnostic_frame,percentile
from fx240.session import Session,Settings
from fx240.focus import Focus


class BenchmarkTests(unittest.TestCase):
    def test_percentiles_and_diagnostic_complement(self):
        self.assertIsNone(percentile([],.95))
        self.assertEqual(percentile(list(range(1,101)),.95),95)
        for n in (0,1,17,255,359,360,854,1259,4095):
            image=diagnostic_frame(n,60,'gray').convert('L')
            top=bottom=0
            for bit in range(12):
                top=(top<<1)|int(image.getpixel((59+bit*11,156))>128)
                bottom=(bottom<<1)|int(image.getpixel((59+bit*11,174))>128)
            self.assertEqual(top,n^(n>>1))
            self.assertEqual(bottom,top^4095)

    def test_session_accepts_instrumented_theme_without_opening_usb(self):
        transport=Mock();theme=Mock(side_effect=Focus)
        session=Session(Settings(),provider=lambda:[],transport_factory=transport,theme_factory=theme)
        publish=session.publish
        def capture(event):
            publish(event)
            if event['kind']=='frame':session.stop()
        session.publish=capture
        session.run()
        self.assertIsNone(session.error)
        self.assertEqual(session.frames,1)
        theme.assert_called_once()
        transport.assert_not_called()

    @unittest.skipUnless(importlib.util.find_spec('PySide6'),'Optional Qt dependency missing')
    def test_experimental_rate_does_not_raise_production_limit(self):
        from benchmark_gui import BenchmarkSettings,Histogram
        BenchmarkSettings(fps=120).validate()
        with self.assertRaises(ValueError):Settings(fps=60).validate()
        with self.assertRaises(ValueError):BenchmarkSettings(fps=121).validate()
        histogram=Histogram()
        for value in range(100):histogram.add(value)
        self.assertEqual(histogram.summary()['p95'],94)
        for _ in range(10000):histogram.add(10)
        self.assertEqual(len(histogram.bins),100)


    @unittest.skipUnless(importlib.util.find_spec('PySide6'),'Optional Qt dependency missing')
    def test_high_rate_instrument_closes_with_queued_qt_callbacks(self):
        import json,os,subprocess,tempfile
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'result.json'
            env=os.environ.copy();env.update(QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software')
            run=subprocess.run([sys.executable,str(TOOLS/'benchmark_gui.py'),'--experimental','--fps','90',
                '--poll-ms','4','--seconds','1','--output',str(output)],env=env,
                capture_output=True,text=True,timeout=10)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            result=json.loads(output.read_text())
            self.assertIn('queued',result['qt_callback_method'])
            self.assertTrue(result['worker_stopped'])
            self.assertTrue(result['completed_requested_duration'])
            self.assertGreater(result['generated'],20)
            self.assertFalse(result['usb'])
