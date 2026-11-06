# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch


@unittest.skipUnless(importlib.util.find_spec('PySide6'),'Optional Qt dependency missing')
class FileBrowserTests(unittest.TestCase):
    def test_scan_rejects_special_files_and_is_bounded(self):
        from fx240.filebrowser import scan_folder
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'Nested').mkdir();(root/'image.PNG').write_bytes(b'synthetic')
            (root/'font.ttf').write_bytes(b'synthetic');(root/'notes.txt').write_text('synthetic')
            (root/'.hidden.png').write_bytes(b'synthetic')
            (root/'link.png').symlink_to(root/'image.PNG');os.mkfifo(root/'pipe.png')
            entries,notice=scan_folder(root,'image')
            self.assertEqual([item['name'] for item in entries],['Nested','image.PNG'])
            self.assertFalse(notice)
            entries,_=scan_folder(root,'font')
            self.assertEqual([item['name'] for item in entries],['Nested','font.ttf'])
            with patch('fx240.filebrowser.MAX_ENTRIES',2):
                entries,notice=scan_folder(root,'image')
            self.assertLessEqual(len(entries),2);self.assertIn('large',notice)
            self.assertIn('could not be read',scan_folder(root/'missing','image')[1])

    def test_shortcuts_use_configured_existing_folders(self):
        from fx240.filebrowser import standard_locations
        from PySide6.QtCore import QStandardPaths
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder);downloads=home/'Descargas';downloads.mkdir()
            mapping={QStandardPaths.HomeLocation:str(home),QStandardPaths.DownloadLocation:str(downloads),
                     QStandardPaths.PicturesLocation:str(home/'missing'),QStandardPaths.DocumentsLocation:str(home),QStandardPaths.DesktopLocation:''}
            with patch('fx240.filebrowser.QStandardPaths.writableLocation',side_effect=mapping.get):
                self.assertEqual(standard_locations(),[{'label':'Home','path':str(home)},{'label':'Downloads','path':str(downloads)}])

    def test_slow_navigation_is_coalesced_and_cancelled(self):
        from fx240.filebrowser import LocalFileBrowser
        from PySide6.QtCore import QCoreApplication
        app=QCoreApplication.instance() or QCoreApplication([])
        gate=threading.Event();started=threading.Event();calls=[]
        def scan(path,kind):
            calls.append((path,kind));started.set();gate.wait(3)
            return [{'name':kind,'path':str(Path(path)/(kind+'.png')),'folder':False}],''
        with tempfile.TemporaryDirectory() as folder,patch('fx240.filebrowser.scan_folder',side_effect=scan),patch('fx240.filebrowser.standard_locations',return_value=[{'label':'Home','path':folder}]):
            browser=LocalFileBrowser();browser.open('image','');self.assertTrue(started.wait(1))
            browser.go(str(Path(folder)/'first'));browser.go(str(Path(folder)/'second'))
            browser.cancel();browser.open('font','');gate.set()
            deadline=time.monotonic()+4
            while browser.busy and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
            self.assertFalse(browser.busy);self.assertEqual(len(calls),2)
            self.assertEqual(browser.entries[0]['name'],'font')
            browser.cancel();self.assertFalse(browser.canChoose);self.assertEqual(browser.entries,[])
            browser.open('image','');browser.go('https://example.invalid/assets')
            self.assertIn('absolute local',browser.notice)
            browser.cancel()

    def test_studio_config_override_preserves_desktop_environment(self):
        from fx240.gui import desktop_storage
        from fx240.cli import main
        import contextlib,io
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'XDG_CONFIG_HOME':'/synthetic/system-config'}):
            prefs,startup=desktop_storage(Path(folder))
            self.assertEqual(prefs.path,Path(folder)/'fx240-linux/settings.json')
            self.assertEqual(startup.path,Path(folder)/'autostart/org.fx240lcdstudio.desktop')
            self.assertEqual(startup.command[-2:],('--config-home',folder))
            self.assertEqual(os.environ['XDG_CONFIG_HOME'],'/synthetic/system-config')
            with self.assertRaises(ValueError):desktop_storage('relative')
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):main(['gui','--config-home','relative'])
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):main(['sensors','--config-home',folder])
            with patch('fx240.gui.launch',return_value=0) as launch,patch('fx240.guard.StandbyGuard'),patch('fx240.lifecycle.LifecycleTrace'):
                self.assertEqual(main(['gui','--config-home',folder]),0)
                self.assertEqual(launch.call_args.args[0].config_home,Path(folder))

    def test_real_qml_shortcuts_double_click_and_selection_in_both_themes(self):
        script=r'''
from pathlib import Path
import tempfile,time,shutil
from unittest.mock import patch,Mock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject,QPointF,QMetaObject,Qt
from PySide6.QtTest import QTest
from PySide6.QtQuick import QQuickWindow
from PIL import Image
from fx240.gui import create_engine,dispose_engine
from fx240.session import Settings,Session
from fx240.preferences import Preferences
app=QApplication([]);app.setQuitOnLastWindowClosed(False)
transport=Mock(side_effect=AssertionError('No real USB'))
def wait(condition):
    deadline=time.monotonic()+4
    while not condition() and time.monotonic()<deadline:QTest.qWait(15)
    assert condition()
def find(item,name):
    if item.objectName()==name:return item
    for child in item.childItems():
        result=find(child,name)
        if result is not None:return result
    return None
def click(item,double=False):
    point=item.mapToScene(QPointF(item.width()/2,item.height()/2)).toPoint()
    (QTest.mouseDClick if double else QTest.mouseClick)(window,Qt.LeftButton,Qt.NoModifier,point)
with tempfile.TemporaryDirectory() as folder:
    root=Path(folder);downloads=root/'Descargas';downloads.mkdir();nested=downloads/'Samples';nested.mkdir()
    Image.new('RGB',(32,32),'#73dfc1').save(nested/'sample.png')
    locations=[{'label':'Home','path':str(root)},{'label':'Downloads','path':str(downloads)}]
    with patch('fx240.gui.find_devices',return_value=[]),patch('fx240.filebrowser.standard_locations',return_value=locations):
        engine,bridge=create_engine(app,Settings(),preferences=Preferences(root/'config/settings.json'),provider=lambda:[],session_factory=lambda *a,**k:Session(*a,transport_factory=transport,**k))
        window=engine.rootObjects()[0];window.setProperty('page',4);QTest.qWait(100)
        picker=window.findChild(QObject,'mediaAssetPicker');browser=picker.findChild(QObject,'assetBrowser')
        for theme in (0,1):
            bridge.setLanguage('es');bridge.setUiTheme('light' if theme else 'dark')
            count=len(app.topLevelWindows());before=bridge.workspace.model.rowCount()
            QMetaObject.invokeMethod(picker,'open');wait(lambda:not browser.busy)
            assert picker.property('visible')
            assert len(app.topLevelWindows())==count
            assert picker.property('background').property('color')==window.property('panel')
            shortcut=find(window.contentItem(),'assetShortcut-Downloads');assert shortcut is not None
            click(shortcut);wait(lambda:browser.folder==str(downloads) and not browser.busy)
            index=next(i for i,item in enumerate(browser.entries) if item['name']=='Samples')
            files=find(window.contentItem(),'assetFiles');QTest.qWait(40)
            row=next(item for item in files.property('contentItem').childItems() if item.property('index')==index)
            if theme==0:click(row,True)
            else:
                click(row);click(find(window.contentItem(),'assetOpen'))
            wait(lambda:browser.folder==str(nested) and not browser.busy)
            QTest.qWait(40)
            row=next(item for item in files.property('contentItem').childItems() if item.property('index')==0)
            click(row);assert browser.canChoose
            click(find(window.contentItem(),'assetOpen'))
            assert not picker.property('visible');assert bridge.workspace.model.rowCount()==before+1
            QMetaObject.invokeMethod(picker,'open');wait(lambda:not browser.busy)
            QTest.keyClick(window,Qt.Key_Escape)
            assert not picker.property('visible');assert bridge.workspace.model.rowCount()==before+1
        bridge.stop()
        if bridge.session:bridge.session.thread.join(2)
        transport.assert_not_called();dispose_engine(engine)
'''
        result=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True,timeout=25,
                              env={**os.environ,'QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software'})
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
