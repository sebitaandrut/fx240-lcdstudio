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
        model.moveSelection(8,8);model.moveSelection(12,10);model.endGesture()
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

    def test_group_transforms_and_deletion_are_undoable(self):
        from fx240.editor import EditorModel
        from fx240.scene import layer, scene_json
        model = EditorModel(scene_json({'version': 1, 'layers': [
            layer('a', 'text', x=20, y=20, width=24, height=24, size=18),
            layer('b', 'media', x=60, y=20, width=24, height=24, path='/test/image.png'),
            layer('c', 'arc'),
        ]}))
        model.toggleSelection(1)
        original = model.payload()
        model.beginGesture()
        model.moveSelection(20, 30)
        model.moveSelection(500, 30)
        model.endGesture()
        self.assertEqual(model.selectionBounds, dict(x=176, y=50, width=64, height=24))
        self.assertEqual(len(model.history), 1)
        model.undo()
        self.assertEqual(model.payload(), original)
        model.beginGesture()
        model.scaleSelection(1.5)
        model.endGesture()
        self.assertEqual(model.selectionBounds, dict(x=20, y=20, width=96, height=36))
        self.assertEqual(model.scene['layers'][0]['size'], 27)
        model.rotateSelection(90)
        self.assertEqual(model.selectionBounds, dict(x=50, y=0, width=36, height=96))
        self.assertTrue(all(item['rotation'] == 90 for item in model.scene['layers'][:2]))
        model.updateSelectionStyle({'color': '#123456', 'opacity': .5})
        self.assertEqual([item['color'] for item in model.scene['layers']], ['#123456', '#edf4f5', '#edf4f5'])
        self.assertEqual([item['opacity'] for item in model.scene['layers']], [.5, .5, 1])
        before_delete = model.payload()
        model.removeSelected()
        self.assertEqual([item['id'] for item in model.scene['layers']], ['c'])
        model.undo()
        self.assertEqual(model.payload(), before_delete)
        self.assertEqual(model.selectionCount, 2)

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
    window=engine.rootObjects()[0]
    wait_until(lambda:len(bridge.thumbnails.urls)==4 and all(bridge.thumbnails.urls))
    thumbnails=list(bridge.thumbnails.provider.images.values())
    assert len(thumbnails)==4 and all(image.width()==192 and image.pixelColor(0,0).alpha()==0 for image in thumbnails)
    assert all(image!=other for index,image in enumerate(thumbnails) for other in thumbnails[:index])
    window.setProperty('page',4)
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
    model=bridge.workspace.model
    def click(item, modifiers=Qt.NoModifier):
        point=item.mapToScene(QPointF(item.width()/2,item.height()/2)).toPoint()
        QTest.mouseClick(window,Qt.LeftButton,modifiers,point)
    click(find_item(window.contentItem(),'editorLayerRow-0'), Qt.ShiftModifier)
    assert model.selectionCount==2
    click(find_item(window.contentItem(),'editorLayerCheck-2'))
    assert model.selectionCount==3
    click(find_item(window.contentItem(),'editorLayerCheck-2'))
    assert model.selectionCount==2
    before=model.payload()
    point=box.mapToScene(QPointF(25,25)).toPoint()
    QTest.mousePress(window,Qt.LeftButton,Qt.ShiftModifier,point)
    QTest.mouseMove(window,point+QPoint(8,-8),20)
    QTest.mouseRelease(window,Qt.LeftButton,Qt.ShiftModifier,point+QPoint(8,-8))
    assert model.selectionCount==2 and model.payload()!=before
    model.undo()
    assert model.payload()==before and model.selectionCount==2
    handle=find_item(window.contentItem(),'editorGroupResize')
    point=handle.mapToScene(QPointF(6,6)).toPoint()
    QTest.mousePress(window,Qt.LeftButton,Qt.NoModifier,point)
    QTest.mouseMove(window,point-QPoint(22,22),20)
    QTest.mouseRelease(window,Qt.LeftButton,Qt.NoModifier,point-QPoint(22,22))
    assert model.payload()!=before
    model.undo()
    click(window.findChild(QObject,'deleteSelectedLayers'))
    assert model.rowCount()==3
    model.undo()
    assert model.payload()==before and model.selectionCount==2
    model.select(1)
    theme=window.findChild(QObject,'appThemeControl')
    icon=window.findChild(QObject,'appThemeIcon')
    def check_theme_width():
        app.processEvents()
        width=theme.property('implicitContentWidth')+theme.property('leftPadding')+theme.property('rightPadding')
        assert 0<theme.width()<108 and abs(theme.width()-width)<=1
    check_theme_width()
    assert icon.property('source').toString().endswith('theme-moon-muted.svg')
    click(theme)
    assert bridge.uiTheme=='light' and theme.property('text')=='Light'
    assert icon.property('source').toString().endswith('theme-sun-muted.svg')
    check_theme_width()
    bridge.setLanguage('es')
    assert theme.property('text')=='Claro'
    check_theme_width()
    bridge.setLanguage('en')
    bridge.flushPreferences()
    assert prefs.load()[1]['theme']=='light'
    theme.forceActiveFocus()
    QTest.keyClick(window,Qt.Key_Space)
    assert bridge.uiTheme=='dark' and theme.property('text')=='Dark'
    assert icon.property('source').toString().endswith('theme-moon-muted.svg')
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
    for index, design in enumerate(('Dual','Trace','Halo'), 1):
        bridge.selectContent(index)
        wait_until(lambda:bridge.activeContentName==design and bridge.activeContentIndex==index)
    bridge.flushPreferences()
    saved_design, ui = prefs.load()
    assert saved_design.layout_mode == 'halo' and not saved_design.profile_id
    from fx240.gui import Bridge
    assert Bridge(saved_design, preferences=prefs, application=ui).activeContentName=='Halo'
    bridge.selectContent(0);wait_until(lambda:bridge.layoutMode=='focus')
    bridge.workspace.setProfileName('Example')
    assert bridge.workspace.save(False,False)
    assert bridge.contentLabels==['Focus','Dual','Trace','Halo','Example']
    assert bridge.layoutMode=='focus'
    profile_id=bridge.workspace.loadedId
    bridge.selectContent(4);wait_until(lambda:bridge.layoutMode=='editor')
    saved_payload=bridge.session.settings.scene_json
    assert bridge.activeContentIndex==4
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
    assert len(bridge.contentLabels)==6
    bridge.selectContent(5);wait_until(lambda:bridge.activeContentIndex==5)
    bridge.flushPreferences();loaded,ui=prefs.load()
    assert loaded.profile_id==bridge.workspace.loadedId
    assert loaded.scene_json=='' # active scenes are loaded from the library
    window.setProperty('page',0);QTest.qWait(60)
    assert window.findChild(QObject,'focusInspector') is None
    assert window.findChild(QObject,'designGallery').property('visible')
    wait_until(lambda:len(bridge.thumbnails.urls)==6 and all(bridge.thumbnails.urls))
    thumbnail=find_item(window.contentItem(),'designThumbnail-5')
    assert thumbnail.width()>=100 and thumbnail.property('source').toString()==bridge.thumbnails.urls[5]
    entry=window.findChild(QObject,'openEditorButton')
    point=entry.mapToScene(QPointF(entry.width()/2,entry.height()/2)).toPoint()
    QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point)
    assert window.property('page')==4
    assert bridge.workspace.loadedId==bridge.activeProfileId
    assert len(bridge.contentLabels)==6
    window.setProperty('page',0);QTest.qWait(60)
    focus=find_item(window.contentItem(),'designTile-0')
    click(focus)
    wait_until(lambda:bridge.layoutMode=='focus')
    assert not bridge.sending and not bridge.session.output_requested
    assert window.findChild(QObject,'framePreview').property('source').toString()==bridge.previewUrl
    click(find_item(window.contentItem(),'designTile-1'))
    wait_until(lambda:bridge.layoutMode=='dual')
    click(window.findChild(QObject,'openEditorButton'))
    wait_until(lambda:bridge.workspace.ready)
    assert bridge.layoutMode=='dual'
    assert bridge.workspace.profileName=='Dual copy'
    assert {'cpu-arc','gpu-arc'} <= {item['id'] for item in bridge.workspace.model.scene['layers']}
    model.setMotionSpeed(1.75)
    model.setTemperatureDecimals(0)
    assert bridge.workspace.motionSpeed==1.75 and bridge.workspace.temperatureDecimals==0
    wait_until(lambda:bridge.workspace.ready)
    assert bridge.workspace.save(True,False)
    wait_until(lambda:bridge.activeContentName=='Dual copy' and bridge.sensorRows[0]['target']=='45°C')
    assert bridge.session.settings.comet_speed==1.0
    window.setProperty('page',0);QTest.qWait(60)
    click(find_item(window.contentItem(),'designTile-5'))
    wait_until(lambda:bridge.activeContentIndex==5)
    assert not bridge.session.output_requested
    click(window.findChild(QObject,'openEditorButton'))
    wait_until(lambda:bridge.workspace.ready)
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
    assert other.activeContentIndex==5 and other.settings.scene_json
    assert other.workspace.model.payload()==bridge.workspace.model.payload()
    dispose_engine(restored)
'''
        result=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True,timeout=20,
                              env={**os.environ,'QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software'})
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_gallery_removes_selected_saved_profiles_after_confirmation(self):
        script=r'''
from pathlib import Path
import tempfile,time
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject,QPointF,Qt
from PySide6.QtTest import QTest
from fx240.gui import create_engine,dispose_engine
from fx240.preferences import Preferences
from fx240.profiles import ProfileStore
from fx240.scene import scene_json,default_scene
from fx240.session import Settings
app=QApplication([])
def wait(condition):
    deadline=time.monotonic()+4
    while not condition() and time.monotonic()<deadline:
        app.processEvents();time.sleep(.01)
    assert condition()
def item(parent,name):
    if parent.objectName()==name:return parent
    for child in parent.childItems():
        match=item(child,name)
        if match is not None:return match
def click(control):
    point=control.mapToScene(QPointF(control.width()/2,control.height()/2)).toPoint()
    QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point)
with tempfile.TemporaryDirectory() as folder:
    path=Path(folder)/'profiles.json'
    store=ProfileStore(path)
    payload=scene_json(default_scene())
    first,second,third=[store.save(name,payload) for name in ('First','Second','Third')]
    config=Settings(profile_id=second,layout_mode='editor',draft_profile_id=second,draft_scene_json=payload)
    with patch('fx240.gui.find_devices',return_value=[]):
        engine,bridge=create_engine(app,config,provider=lambda:[],preferences=Preferences(Path(folder)/'settings.json'))
    try:
        window=engine.rootObjects()[0]
        bridge.start({},False)
        wait(lambda:not bridge.previewUrl.endswith('/0'))
        draft=bridge.workspace.model.payload()
        click(window.findChild(QObject,'manageDesignsButton'))
        for index in (4,5):
            click(item(window.contentItem(),'designTile-'+str(index)))
        button=window.findChild(QObject,'deleteSelectedDesignsButton')
        assert bridge.activeProfileId==second and not button.property('enabled')
        click(item(window.contentItem(),'designTile-0'))
        wait(lambda:bridge.layoutMode=='focus' and button.property('enabled'))
        click(button)
        dialog=window.findChild(QObject,'deleteDesignsConfirmation')
        assert dialog.property('visible')
        click(dialog.findChild(QObject,'confirmationCancel'))
        assert bridge.profileIds==[first,second,third]
        click(button)
        click(dialog.findChild(QObject,'confirmationAccept'))
        assert bridge.profileIds==[third]
        assert [entry['id'] for entry in ProfileStore(path).profiles]==[third]
        assert not bridge.workspace.loadedId and bridge.workspace.model.payload()==draft
        bridge.selectContent(4)
        assert not bridge.workspace.deleteProfiles([third]) # activation is pending
        wait(lambda:bridge.activeProfileId==third)
    finally:
        bridge.stop()
        bridge.session.thread.join(2)
        dispose_engine(engine)
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
            self.assertEqual(bridge.contentLabels,['Focus','Dual','Trace','Halo','Missing asset'])
            bridge.timer.stop();bridge.workspace.close()
