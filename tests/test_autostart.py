# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
from pathlib import Path
import subprocess
import sys
import shutil
import tempfile
import unittest

from fx240.autostart import Autostart, exec_argument


class AutostartTests(unittest.TestCase):
    def test_entry_is_atomic_private_valid_and_removable(self):
        with tempfile.TemporaryDirectory() as directory:
            startup=Autostart(directory,(sys.executable,'-m','fx240','gui','--start-minimized'))
            self.assertFalse(startup.enabled)
            startup.set_enabled(True)
            self.assertTrue(startup.enabled)
            self.assertEqual(startup.path.stat().st_mode & 0o777,0o600)
            self.assertIn('TryExec='+sys.executable,startup.path.read_text())
            if shutil.which('desktop-file-validate'):
                result=subprocess.run(['desktop-file-validate',str(startup.path)],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            startup.set_enabled(False)
            self.assertFalse(startup.path.exists())
            startup.set_enabled(False)

    def test_foreign_entry_and_symlink_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            startup=Autostart(directory,(sys.executable,'gui'))
            startup.path.parent.mkdir()
            startup.path.write_text('[Desktop Entry]\nName=Other\n')
            for enabled in (True,False):
                with self.assertRaises(OSError):startup.set_enabled(enabled)
            self.assertIn('Other',startup.path.read_text())
            startup.path.unlink()
            target=Path(directory)/'target';target.write_text('personal')
            startup.path.symlink_to(target)
            with self.assertRaises(OSError):startup.set_enabled(True)
            self.assertEqual(target.read_text(),'personal')

    def test_exec_escaping_and_invalid_paths(self):
        self.assertEqual(exec_argument('/tmp/a b%file'), '"/tmp/a b%%file"')
        self.assertEqual(exec_argument('a"$`\\b'), '"a\\\\"\\\\$\\\\`\\\\\\\\b"')
        for executable in ('relative/python','/tmp/bad=path','/tmp/new\nline'):
            with self.assertRaises(ValueError):Autostart('/tmp',(executable,'gui'))


@unittest.skipUnless(importlib.util.find_spec('PySide6'),'Optional Qt dependency missing')
class AutostartBridgeTests(unittest.TestCase):
    def test_minimized_initial_state_and_startup_preferences_are_isolated(self):
        script=r'''
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QT_QUICK_BACKEND']='software'
from pathlib import Path
import sys,tempfile
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject
from fx240.autostart import Autostart
from fx240.gui import create_engine,dispose_engine
from fx240.session import Settings
app=QApplication([])
with tempfile.TemporaryDirectory() as home:
    manager=Autostart(home,(sys.executable,'-m','fx240','gui','--start-minimized'))
    engine,bridge=create_engine(app,Settings(),autostart=manager,start_minimized=True)
    window=engine.rootObjects()[0]
    assert not window.isVisible()
    assert bridge.startMinimized and bridge.autostartSupported
    assert window.findChild(QObject,'autostartControl') is not None
    bridge.setAutostart(True)
    assert bridge.autostartEnabled and manager.enabled
    bridge.setAutostart(False)
    assert not bridge.autostartEnabled and not manager.path.exists()
    manager.path.write_text('[Desktop Entry]\nName=Someone else\n')
    bridge.setAutostart(True)
    assert not bridge.autostartEnabled
    assert 'Login startup could not be updated:' in bridge.runtimeError
    bridge.setLanguage('es')
    assert 'No se pudo actualizar el inicio automático:' in bridge.runtimeError
    assert bridge.session is None and bridge.preferences is None
    dispose_engine(engine)
'''
        result=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
