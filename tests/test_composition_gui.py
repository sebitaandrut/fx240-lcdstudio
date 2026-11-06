# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
import os
import subprocess
import sys
import unittest


@unittest.skipUnless(importlib.util.find_spec('PySide6'),'Optional Qt dependency missing')
class CompositionGuiTests(unittest.TestCase):
    def test_live_composition_and_async_font_catalog_never_open_usb(self):
        script=r'''
from pathlib import Path
import tempfile,time
from unittest.mock import Mock,patch
from PIL import Image
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication
from fx240.gui import create_engine,dispose_engine
from fx240.session import Settings,Session
from fx240.telemetry import Metric
app=QApplication([])
transport=Mock(side_effect=AssertionError('No USB allowed'))
def factory(*args,**kwargs):return Session(*args,transport_factory=transport,**kwargs)
def metrics():return [Metric('ct','CPU synthetic',45,'C','synthetic')]
def wait_until(condition):
    deadline=time.monotonic()+3
    while not condition() and time.monotonic()<deadline:
        app.processEvents();time.sleep(.01)
    assert condition()
with tempfile.TemporaryDirectory() as folder:
    path=Path(folder)/'synthetic.png';Image.new('RGB',(16,16),'navy').save(path)
    with patch('fx240.gui.find_devices',return_value=[]):
        engine,bridge=create_engine(app,Settings(),provider=metrics,session_factory=factory)
    window=engine.rootObjects()[0]
    for name in ('designGallery','editorMotionSpeed','editorFontBrowse','systemFontControl'):
        assert window.findChild(QObject,name) is not None
    bridge.start({},False)
    wait_until(lambda:bridge.session.frames>0)
    bridge.applySettings({'animation':'orbit','background':str(path),'backgroundDim':.4})
    wait_until(lambda:bridge.session.config_revision>0)
    assert bridge.session.settings.animation=='orbit'
    assert bridge.session.settings.background_path==str(path)
    assert not bridge.session.error and not bridge.session.config_error
    with patch('fx240.systemfonts.catalog',return_value=[('Synthetic Sans · Regular','/usr/share/fonts/synthetic.ttf')]):
        bridge.refreshSystemFonts()
        wait_until(lambda:not bridge.fontDiscoveryBusy)
    assert bridge.systemFontLabels==['Bundled Outfit (default)','Synthetic Sans · Regular']
    assert bridge.systemFontPath(1)=='/usr/share/fonts/synthetic.ttf'
    assert bridge.systemFontPath(0)=='' and bridge.systemFontPath(99)==''
    assert all('/' not in label for label in bridge.systemFontLabels)
    with patch('fx240.systemfonts.catalog',side_effect=ValueError('System font discovery failed')):
        bridge.refreshSystemFonts();wait_until(lambda:not bridge.fontDiscoveryBusy)
    assert bridge.fontNotice=='System font discovery failed'
    bridge.stop();wait_until(lambda:not bridge.running)
    transport.assert_not_called()
    assert bridge.preferences is None
    dispose_engine(engine)
'''
        result=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True,timeout=15,
                              env={**os.environ,'QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software'})
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_fontconfig_process_limits_and_cleanup(self):
        from unittest.mock import MagicMock,patch
        from fx240.systemfonts import fontconfig_output
        for failure in ('too_large','timeout','not_started'):
            process=MagicMock()
            process.waitForStarted.return_value=failure!='not_started'
            process.state.return_value=1
            process.read.return_value=b'01234567890' if failure=='too_large' else b''
            factory=MagicMock(return_value=process);factory.NotRunning=0;factory.NormalExit=0
            with patch('PySide6.QtCore.QProcess',factory),patch('fx240.systemfonts.shutil.which',return_value='/usr/bin/fc-list'),patch('fx240.systemfonts.MAX_OUTPUT',10),patch('fx240.systemfonts.time.monotonic',side_effect=[0,5]):
                with self.assertRaises(ValueError):fontconfig_output()
            process.kill.assert_called_once();process.waitForFinished.assert_called_once()
            self.assertEqual(process.setArguments.call_args.args[0][1],':scalable=true')
