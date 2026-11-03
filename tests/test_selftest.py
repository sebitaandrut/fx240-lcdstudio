# SPDX-License-Identifier: GPL-3.0-or-later
"""The user-facing self-test must detect failures even under python -O."""
import importlib.util
import json
import os
import subprocess
import sys
import unittest


@unittest.skipUnless(importlib.util.find_spec('PySide6'), 'Optional Qt dependency missing')
class SelfTestChecks(unittest.TestCase):
    def test_optimized_python_still_rejects_broken_ui(self):
        script = '''
from fx240 import gui, selftest
original = gui.create_engine
def broken_title(*args, **kwargs):
    engine, bridge = original(*args, **kwargs)
    engine.rootObjects()[0].setTitle('Unexpected test title')
    return engine, bridge
gui.create_engine = broken_title
raise SystemExit(selftest.run())
'''
        result = subprocess.run([sys.executable, '-O', '-c', script], capture_output=True,
                                text=True, timeout=12, env={**os.environ,
                                'QT_QPA_PLATFORM':'offscreen', 'QT_QUICK_BACKEND':'software'})
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stdout.splitlines()[-1])
        self.assertIn('Unexpected application title', report['errors'])
        self.assertEqual(report['hid_open_attempts'], 0)
        self.assertFalse(report['preferences_store_enabled'])

    def test_default_and_legacy_commands_check_long_gif_without_hid(self):
        for options in ([],['--experimental-gif-buffering']):
            with self.subTest(options=options):
                result=subprocess.run([sys.executable,'-m','fx240','self-test',*options],
                                      capture_output=True,text=True,timeout=12,
                                      env={**os.environ,'QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software'})
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                report=json.loads(result.stdout.splitlines()[-1])
                self.assertTrue(report['gif_buffering'])
                self.assertEqual(report['errors'],[])
                self.assertEqual(report['hid_open_attempts'],0)
                self.assertFalse(report['preferences_store_enabled'])
