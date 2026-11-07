# SPDX-License-Identifier: GPL-3.0-or-later
"""Rotation, profile-specific units, and reversible clearing; synthetic inputs only."""
from dataclasses import replace
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
from PIL import Image
from fx240.scene import parse_scene,scene_json,default_scene,layer,SceneRenderer
from fx240.profiles import ProfileStore
from fx240.session import Settings,Session
from fx240.telemetry import Metric
from fx240.media import encode


def metrics():return [Metric('ct','CPU synthetic',45.25,'C','synthetic')]


class SceneControlTests(unittest.TestCase):
    def test_legacy_defaults_and_strict_transform_metadata(self):
        legacy=default_scene()
        for item in legacy['layers']:item.pop('rotation')
        parsed=parse_scene(scene_json(legacy))
        self.assertTrue(all(item['rotation']==0 for item in parsed['layers']))
        self.assertNotIn('temperature_unit',parsed)
        for angle in (-1,360,True,90.5,'90',float('nan')):
            with self.subTest(angle=angle),self.assertRaises(ValueError):
                parse_scene(scene_json({'version':1,'layers':[layer('a','text',rotation=angle)]}))
        for unit in (False,[],{},'kelvin','https://example.invalid'):
            with self.subTest(unit=unit),self.assertRaises(ValueError):
                parse_scene(scene_json({'version':1,'temperature_unit':unit,'layers':[]}))
        with patch('fx240.localfiles.os.open') as opened:
            result=parse_scene(scene_json({'version':1,'temperature_unit':'F','layers':[layer('a','text',rotation=359)]}))
            self.assertEqual(result['temperature_unit'],'F');opened.assert_not_called()

    def test_static_and_gif_rotation_preserves_center_timing_and_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);static=root/'sprite.png';animated=root/'sprite.gif';back=root/'back.png'
            first=Image.new('RGB',(240,240),'red');first.paste('blue',(120,0,240,240))
            second=Image.new('RGB',(240,240),'yellow');second.paste('cyan',(120,0,240,240))
            first.save(static);first.save(animated,save_all=True,append_images=[second],duration=100,loop=0)
            Image.new('RGB',(240,240),'lime').save(back)
            for path in (static,animated):
                scene={'version':1,'layers':[layer('back','media',x=0,y=0,width=240,height=240,path=str(back)),
                       layer('sprite','media',x=80,y=100,width=80,height=40,path=str(path),rotation=90)]}
                renderer=SceneRenderer(scene_json=scene_json(scene),provider=metrics)
                try:
                    image,_=renderer(0)
                    self.assertEqual(image.getpixel((120,90)),(255,0,0))
                    self.assertEqual(image.getpixel((120,150)),(0,0,255))
                    self.assertEqual(image.getpixel((80,120)),(0,255,0))
                    if path==animated:
                        frame,_=renderer(.11)
                        self.assertEqual(frame.getpixel((120,90)),(255,255,0))
                        self.assertEqual(frame.getpixel((120,150)),(0,255,255))
                    jpeg=encode(image)
                    self.assertNotIn(str(path).encode(),jpeg)
                    with Image.open(io.BytesIO(jpeg)) as decoded:self.assertFalse(decoded.getexif())
                finally:renderer.close()
            for kind in ('text','metric','arc'):
                scene={'version':1,'layers':[layer('element',kind,x=60,y=60,width=120,height=120)]}
                original=SceneRenderer(scene_json=scene_json(scene),provider=metrics)
                scene['layers'][0]['rotation']=90
                rotated=SceneRenderer(scene_json=scene_json(scene),provider=metrics)
                try:self.assertNotEqual(original(0)[0].tobytes(),rotated(0)[0].tobytes(),kind)
                finally:original.close();rotated.close()

    def test_rotated_long_gif_keeps_streaming_and_closes_its_decoder(self):
        import time
        from fx240 import gifstream
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.gif';frames=[]
            for index in range(121):
                frame=Image.new('RGB',(32,32),(255,index,0))
                frame.paste((0,index,255),(16,0,32,32));frames.append(frame)
            frames[0].save(path,save_all=True,append_images=frames[1:],duration=40,loop=0)
            scene={'version':1,'layers':[layer('a','media',x=80,y=100,width=80,height=40,path=str(path),rotation=90)]}
            renderer=SceneRenderer(scene_json=scene_json(scene),provider=metrics)
            try:
                self.assertEqual(gifstream.statistics()['streams'],1)
                deadline=time.monotonic()+3
                while True:
                    image,_=renderer(.081)
                    if image.getpixel((120,90))==(255,2,0):break
                    if time.monotonic()>deadline:self.fail('Rotated GIF did not reach the requested frame')
                    time.sleep(.01)
                self.assertEqual(image.getpixel((120,150)),(0,2,255))
                self.assertLessEqual(gifstream.statistics()['queued_frames'],12)
            finally:renderer.close()
            self.assertEqual(gifstream.statistics()['streams'],0)

    def test_profile_roundtrip_stores_units_and_rotation_without_changing_focus(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profiles.json';store=ProfileStore(path)
            scene=default_scene();scene['temperature_unit']='F';scene['layers'][1]['rotation']=270
            identifier=store.save('Example',scene_json(scene))
            loaded=parse_scene(ProfileStore(path).get(identifier)['scene'])
            self.assertEqual(loaded['temperature_unit'],'F');self.assertEqual(loaded['layers'][1]['rotation'],270)
            renderer=SceneRenderer(scene_json=scene_json(loaded),temperature_unit='C',provider=metrics)
            try:
                renderer(0);self.assertEqual(renderer.text_value(layer('a','metric')),'113.5°F')
            finally:renderer.close()
            self.assertEqual(Settings().temperature_unit,'C')
            self.assertEqual(path.stat().st_mode & 0o777,0o600)

    def test_frame_diagnostics_follow_scene_unit_and_restore_focus(self):
        scene=default_scene();scene['temperature_unit']='F'
        config=Settings(layout_mode='editor',scene_json=scene_json(scene),temperature_unit='C')
        forbid=Mock(side_effect=AssertionError('No physical USB in this test'))
        session=Session(config,provider=metrics,transport_factory=forbid)
        events=[];publish=session.publish
        def capture(event):
            publish(event)
            if event['kind']=='frame':
                events.append(event)
                if len(events)==1:session.configure(replace(config,layout_mode='focus'),False)
                else:session.stop()
        session.publish=capture;session.run()
        self.assertIsNone(session.error)
        self.assertEqual([event['temperature_unit'] for event in events],['F','C'])
        self.assertEqual([event['configuration'].temperature_unit for event in events],['C','C'])
        forbid.assert_not_called()


@unittest.skipUnless(importlib.util.find_spec('PySide6'),'Optional Qt dependency missing')
class EditorControlTests(unittest.TestCase):
    def test_model_units_rotation_clear_and_undo_preserve_composition_metadata(self):
        from fx240.editor import EditorModel
        model=EditorModel();model.setTemperatureUnit('F');model.select(1)
        model.updateSelected({'rotation':90.0});self.assertEqual(model.selected['rotation'],90)
        baseline=model.payload();model.add('text');model.reorder(-1);model.removeSelected()
        self.assertEqual(model.temperatureUnit,'F')
        model.resetComposition(True)
        self.assertEqual(model.rowCount(),0);self.assertEqual(model.temperatureUnit,'F')
        model.undo();self.assertEqual(model.payload(),baseline)
        for value in ('bad',):model.setTemperatureUnit(value)
        self.assertEqual(model.temperatureUnit,'F')
        model.setTemperatureUnit('inherit');self.assertNotIn('temperature_unit',model.scene)
        model.undo();self.assertEqual(model.temperatureUnit,'F')

    def test_qml_controls_rotated_drag_resize_clear_confirmation_and_saved_units(self):
        script=r'''
from pathlib import Path
import tempfile,time
from unittest.mock import Mock,patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject,QPointF,QPoint,Qt,QMetaObject
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from fx240.gui import create_engine,dispose_engine
from fx240.session import Settings,Session
from fx240.preferences import Preferences
from fx240.scene import parse_scene
from fx240.telemetry import Metric
app=QApplication([])
def wait(condition):
    deadline=time.monotonic()+4
    while not condition() and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
    assert condition()
def click(window,item):
    QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,item.mapToScene(QPointF(item.width()/2,item.height()/2)).toPoint())
def find(item,name):
    if item.objectName()==name:return item
    for child in item.childItems():
        result=find(child,name)
        if result is not None:return result
    return None
forbid=Mock(side_effect=AssertionError('No physical USB'))
def factory(*args,**kwargs):return Session(*args,transport_factory=forbid,**kwargs)
with tempfile.TemporaryDirectory() as folder:
    preferences=Preferences(Path(folder)/'settings.json')
    with patch('fx240.gui.find_devices',return_value=[]):
        engine,bridge=create_engine(app,Settings(),provider=lambda:[Metric('ct','CPU synthetic',45.25,'C','synthetic')],session_factory=factory,preferences=preferences)
    window=engine.rootObjects()[0];bridge.start({},False)
    wait(lambda:bridge.session.frames>0)
    window.setProperty('page',4);wait(lambda:bridge.workspace.ready)
    model=bridge.workspace.model
    model.resetComposition(True);model.add('metric')
    model.updateSelected({'x':70,'y':80,'width':80,'height':40})
    QTest.qWait(80)
    rotation=window.findChild(QObject,'rotateLayerRight')
    assert QMetaObject.invokeMethod(rotation,'clicked')
    assert model.selected['rotation']==90
    QTest.qWait(60)
    box=find(window.contentItem(),'editorLayer-'+model.selected['id'])
    assert box.rotation()==90
    before=(model.selected['x'],model.selected['y'])
    point=box.mapToScene(QPointF(20,10)).toPoint()
    QTest.mousePress(window,Qt.LeftButton,Qt.NoModifier,point)
    for step in range(1,6):QTest.mouseMove(window,point+QPoint(step*3,step*2),20)
    QTest.mouseRelease(window,Qt.LeftButton,Qt.NoModifier,point+QPoint(15,10))
    assert model.selected['x']>before[0] and model.selected['y']>before[1]
    handle=find(window.contentItem(),'editorResize-'+model.selected['id'])
    point=handle.mapToScene(QPointF(6,6)).toPoint()
    old_width=model.selected['width']
    QTest.mousePress(window,Qt.LeftButton,Qt.NoModifier,point)
    for step in range(1,5):QTest.mouseMove(window,point+QPoint(0,step*4),20)
    QTest.mouseRelease(window,Qt.LeftButton,Qt.NoModifier,point+QPoint(0,16))
    assert model.selected['width']>old_width,(model.selected,old_width)
    unit=window.findChild(QObject,'editorFahrenheitSwitch')
    assert unit.isVisible()
    model.updateSelected({'metric':'cpu_clock'});QTest.qWait(30);assert not unit.isVisible()
    model.updateSelected({'metric':'gpu_temp'});QTest.qWait(30);assert unit.isVisible()
    model.add('text');QTest.qWait(30);assert not unit.isVisible()
    model.removeSelected();model.select(0);model.updateSelected({'metric':'cpu_temp'});QTest.qWait(30)
    scroll=window.findChild(QObject,'editorPropertiesScroll').property('contentItem')
    position=unit.mapToItem(scroll,QPointF(0,0)).y()
    scroll.setProperty('contentY',max(0,float(scroll.property('contentY'))+position-20))
    QTest.qWait(30)
    click(window,unit);wait(lambda:bridge.workspace.temperatureUnit=='F' and bridge.workspace.ready)
    assert bridge.settings.temperature_unit=='C'
    bridge.workspace.setProfileName('Example');assert bridge.workspace.save(False,False)
    saved=bridge.workspace.store.get(bridge.workspace.loadedId)
    assert parse_scene(saved['scene'])['temperature_unit']=='F'
    bridge.selectContent(4);wait(lambda:bridge.layoutMode=='editor' and bridge.sensorRows[0]['target']=='113.5°F')
    baseline=model.payload()
    for language in ('en','es'):
        bridge.setLanguage(language)
        for theme in ('dark','light'):
            bridge.setUiTheme(theme)
            QTest.qWait(60)
            clear=window.findChild(QObject,'clearCompositionButton');dialog=window.findChild(QObject,'clearCompositionDialog')
            click(window,clear);assert dialog.property('visible')
            assert model.payload()==baseline
            QMetaObject.invokeMethod(dialog,'reject');assert model.payload()==baseline
            click(window,clear);QMetaObject.invokeMethod(dialog,'accept')
            assert model.rowCount()==0 and model.temperatureUnit=='F'
            assert bridge.workspace.store.get(bridge.workspace.loadedId)['scene']==saved['scene']
            click(window,window.findChild(QObject,'editorUndoButton'));assert model.payload()==baseline
    model.addEffect('halo')
    halo_index=next(i for i,item in enumerate(model.scene['layers']) if item['kind']=='effect' and item['effect']=='halo')
    model.select(halo_index);wait(lambda:bridge.workspace.ready)
    layer_zoom=window.findChild(QObject,'editorLayerZoom');assert layer_zoom.isVisible()
    bounds=model.selectionBounds
    for value in (125,75):
        layer_zoom.setProperty('value',value)
        assert QMetaObject.invokeMethod(layer_zoom,'moved')
        wait(lambda:bridge.workspace.ready and model.selected['media_zoom']==value/100)
        assert model.selectionBounds==bounds
    model.undo()
    assert model.selected['media_zoom']==1.25
    assert QMetaObject.invokeMethod(window.findChild(QObject,'resetLayerZoom'),'clicked')
    wait(lambda:bridge.workspace.ready and model.selected['media_zoom']==1)
    model.removeSelected();wait(lambda:bridge.workspace.ready)
    from PIL import Image
    source=Path(folder)/'synthetic.png';Image.new('RGB',(8,8),'navy').save(source)
    model.add_layer('media',str(source));wait(lambda:bridge.workspace.ready)
    assert not unit.isVisible()
    zoom=window.findChild(QObject,'editorMediaZoom');assert zoom.isVisible()
    zoom.setProperty('value',225)
    assert QMetaObject.invokeMethod(zoom,'moved')
    wait(lambda:bridge.workspace.ready and model.selected['media_zoom']==2.25)
    assert QMetaObject.invokeMethod(window.findChild(QObject,'resetMediaZoom'),'clicked')
    wait(lambda:bridge.workspace.ready and model.selected['media_zoom']==1)
    replace_button=window.findChild(QObject,'replaceLayerMediaButton')
    for language,text in (('en','Replace image / GIF…'),('es','Reemplazar imagen / GIF…')):
        bridge.setLanguage(language);QTest.qWait(30)
        assert replace_button.property('text')==text
    gif=Path(folder)/'synthetic.gif'
    frames=[Image.new('RGB',(8,8),(index,40,80)) for index in range(3)]
    frames[0].save(gif,save_all=True,append_images=frames[1:],duration=40,loop=0)
    model.updateSelected({'path':str(gif)});wait(lambda:bridge.workspace.ready)
    timing=window.findChild(QObject,'editorGifTimingSwitch');assert timing.isVisible()
    position=timing.mapToItem(scroll,QPointF(0,0)).y()
    scroll.setProperty('contentY',max(0,float(scroll.property('contentY'))+position-20))
    QTest.qWait(30);click(window,timing)
    wait(lambda:bridge.workspace.ready and model.selected['gif_pacing']=='smooth')
    bridge._startup_error='An unmanaged startup entry already exists; it was not modified'
    assert 'se conservó sin cambios' in bridge.runtimeError
    bridge._startup_error=''
    bridge.stop();wait(lambda:not bridge.running);dispose_engine(engine)
    forbid.assert_not_called()
'''
        result=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True,timeout=25,
                              env={**os.environ,'QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software'})
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertNotIn('ReferenceError:',result.stderr)
        self.assertNotIn('TypeError:',result.stderr)
