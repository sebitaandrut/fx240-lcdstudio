# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
import os
import subprocess
import sys
import unittest


@unittest.skipUnless(importlib.util.find_spec('PySide6'),'Optional Qt dependency missing')
class EditorTests(unittest.TestCase):
    def test_layer_model_undo_order_and_validation(self):
        from fx240.editor import EditorModel
        model=EditorModel();original=model.payload()
        model.select(1);model.beginGesture()
        model.moveLayer('layer-2',28,78);model.moveLayer('layer-2',32,80);model.endGesture()
        self.assertEqual(model.selected['x'],32)
        self.assertEqual(len(model.history),1)
        model.undo();self.assertEqual(model.payload(),original)
        model.add('text');identifier=model.selected['id'];count=model.rowCount()
        model.updateSelected({'color':'invalid'})
        self.assertEqual(model.selected['color'],'#edf4f5')
        model.updateSelected({'id':'not permitted'})
        self.assertEqual(model.selected['id'],identifier)
        model.reorder(-1);self.assertEqual(model.selected['id'],identifier)
        model.removeSelected();self.assertEqual(model.rowCount(),count-1)
        model.undo();self.assertEqual(model.rowCount(),count)

    def test_real_qml_drag_draft_activation_and_cleanup_without_usb(self):
        script=r'''
from pathlib import Path
import tempfile,time
from unittest.mock import Mock,patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QPoint,QPointF,QObject,QUrl
from PySide6.QtTest import QTest
from PIL import Image
from fx240.gui import create_engine,dispose_engine
from fx240.session import Settings,Session
from fx240.preferences import Preferences
from fx240.telemetry import Metric
app=QApplication([]);transport=Mock(side_effect=AssertionError('No real USB'))
def factory(*args,**kwargs):return Session(*args,transport_factory=transport,**kwargs)
def wait_until(condition):
    deadline=time.monotonic()+4
    while not condition() and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
    assert condition()
with tempfile.TemporaryDirectory() as folder:
    prefs=Preferences(Path(folder)/'settings.json')
    with patch('fx240.gui.find_devices',return_value=[]):
        engine,bridge=create_engine(app,Settings(),provider=lambda:[Metric('ct','CPU synthetic',45,'C','synthetic')],session_factory=factory,preferences=prefs)
    bridge.start({},False);wait_until(lambda:bridge.session.frames>0)
    window=engine.rootObjects()[0];window.setProperty('page',4)
    wait_until(lambda:bridge.workspace.session is not None and bridge.workspace.session.frames>0)
    QTest.qWait(200)
    def find_item(item,name):
        if item.objectName()==name:return item
        for child in item.childItems():
            found=find_item(child,name)
            if found is not None:return found
        return None
    box=find_item(window.contentItem(),'editorLayer-layer-2');assert box is not None
    point=box.mapToScene(QPointF(25,25)).toPoint()
    QTest.mousePress(window,Qt.LeftButton,Qt.NoModifier,point)
    for step in range(1,13):
        QTest.mouseMove(window,point+QPoint(step,step*8),20)
        app.processEvents()
        assert bridge.workspace.model.gesture
    QTest.mouseRelease(window,Qt.LeftButton,Qt.NoModifier,point+QPoint(12,96))
    assert bridge.workspace.model.selected['x']>20
    assert bridge.workspace.model.selected['y']>110
    assert find_item(window.contentItem(),'editorLayer-layer-2') is box
    assert bridge.session.settings.layout_mode=='focus'
    label=window.findChild(QObject,'layerLabelControl');label.forceActiveFocus()
    QTest.keyClick(window,Qt.Key_A,Qt.ControlModifier)
    for key in (Qt.Key_C,Qt.Key_P,Qt.Key_U):QTest.keyClick(window,key)
    assert bridge.workspace.model.selected['label']=='cpu',(bridge.workspace.model.selected['label'],label.property('text'),label.property('activeFocus'))
    bridge.workspace.model.select(2)
    assert bridge.workspace.model.selected['label']==''
    bridge.workspace.model.select(1)
    assert bridge.workspace.model.selected['label']=='cpu',(bridge.workspace.model.selected['label'],label.property('text'),label.property('activeFocus'))
    wait_until(lambda:bridge.workspace._valid_payload==bridge.workspace.model.payload())
    bridge.flushPreferences();loaded,_=prefs.load()
    assert loaded.layout_mode=='focus' and loaded.draft_scene_json==bridge.workspace.model.payload()
    bridge.workspace.setProfileName('Example')
    assert bridge.workspace.save(False,False)
    assert bridge.contentLabels==['Focus','Example']
    assert bridge.layoutMode=='focus'
    profile_id=bridge.workspace.loadedId
    bridge.selectContent(1);wait_until(lambda:bridge.layoutMode=='editor')
    saved_payload=bridge.session.settings.scene_json
    assert bridge.activeContentIndex==1
    bridge.workspace.model.updateSelected({'color':'#68b5ff'})
    wait_until(lambda:bridge.workspace.ready)
    assert bridge.session.settings.scene_json==saved_payload # drafts do not change output
    assert bridge.workspace.save(False,False)
    wait_until(lambda:bridge.session.settings.scene_json==bridge.workspace.model.payload())
    assert not bridge.workspace.deleteLoaded() # never remove the active profile first
    bridge.selectContent(0);wait_until(lambda:bridge.layoutMode=='focus')
    assert bridge.activeContentIndex==0 and bridge.activeContentName=='Focus'
    assert bridge.previewUrl.startswith('image://frames/')
    assert bridge.workspace.previewUrl.startswith('image://draft/')
    assert bridge.workspace.save(False,True)
    assert len(bridge.contentLabels)==3
    bridge.selectContent(2);wait_until(lambda:bridge.activeContentIndex==2)
    bridge.flushPreferences();loaded,ui=prefs.load()
    assert loaded.profile_id==bridge.workspace.loadedId
    assert loaded.scene_json=='' # active scenes are loaded from the library
    window.setProperty('page',0);QTest.qWait(60)
    assert not window.findChild(QObject,'focusInspector').property('visible')
    assert window.findChild(QObject,'appearanceWorkspace').property('columns')==2
    entry=window.findChild(QObject,'openEditorButton')
    point=entry.mapToScene(QPointF(entry.width()/2,entry.height()/2)).toPoint()
    QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point)
    assert window.property('page')==4
    assert bridge.workspace.loadedId==bridge.activeProfileId
    assert len(bridge.contentLabels)==3
    window.setProperty('page',0);QTest.qWait(60)
    library=window.findChild(QObject,'designLibrary')
    focus=next(item for item in library.property('contentItem').childItems() if item.property('index')==0)
    point=focus.mapToScene(QPointF(focus.width()/2,focus.height()/2)).toPoint()
    QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point)
    wait_until(lambda:bridge.layoutMode=='focus')
    assert window.findChild(QObject,'framePreview').property('source').toString()==bridge.previewUrl
    bridge.selectContent(2);wait_until(lambda:bridge.activeContentIndex==2)
    bridge.flushPreferences();loaded,ui=prefs.load()
    bridge.workspace.addMedia(QUrl('https://example.invalid/private.gif'),False)
    assert 'local' in bridge.workspace.notice
    bridge.stop();wait_until(lambda:not bridge.running)
    transport.assert_not_called()
    preview=bridge.workspace.session
    dispose_engine(engine)
    assert preview is None or not preview.thread.is_alive()
    with patch('fx240.gui.find_devices',return_value=[]):
        restored,other=create_engine(app,loaded,provider=lambda:[],session_factory=factory,preferences=prefs)
    assert other.activeContentIndex==2 and other.settings.scene_json
    assert other.workspace.model.payload()==bridge.workspace.model.payload()
    dispose_engine(restored)
'''
        result=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True,timeout=20,
                              env={**os.environ,'QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software'})
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_legacy_draft_is_kept_and_missing_active_profile_falls_back(self):
        from dataclasses import replace
        from pathlib import Path
        import tempfile
        from PySide6.QtCore import QCoreApplication
        from fx240.gui import Bridge
        from fx240.session import Settings
        from fx240.scene import scene_json,default_scene,layer,parse_scene
        from fx240.profiles import ProfileStore
        from fx240.preferences import Preferences
        from unittest.mock import patch
        app=QCoreApplication.instance() or QCoreApplication([])
        payload=scene_json(default_scene())
        with patch('fx240.gui.find_devices',return_value=[]):
            legacy=Bridge(replace(Settings(),layout_mode='editor',scene_json=payload))
        self.assertEqual(legacy.layoutMode,'focus')
        self.assertEqual(legacy.workspace.model.payload(),scene_json(parse_scene(payload)))
        legacy.timer.stop();legacy.workspace.close()
        with tempfile.TemporaryDirectory() as folder:
            prefs=Preferences(Path(folder)/'settings.json');profiles=ProfileStore(Path(folder)/'profiles.json')
            missing=scene_json({'version':1,'layers':[layer('a','media',x=0,y=0,width=240,height=240,path=str(Path(folder)/'missing.png'))]})
            identifier=profiles.save('Missing asset',missing)
            with patch('fx240.gui.find_devices',return_value=[]):
                bridge=Bridge(replace(Settings(),layout_mode='editor',profile_id=identifier),preferences=prefs)
            self.assertEqual(bridge.layoutMode,'focus');self.assertIn('using Focus',bridge.profileNotice)
            self.assertEqual(bridge.contentLabels,['Focus','Missing asset'])
            bridge.timer.stop();bridge.workspace.close()
