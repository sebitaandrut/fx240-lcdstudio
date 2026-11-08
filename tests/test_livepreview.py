# SPDX-License-Identifier: GPL-3.0-or-later
"""Live drafts use one synthetic sender and never become committed implicitly."""
import importlib.util
import os
import subprocess
import sys
import unittest


@unittest.skipUnless(importlib.util.find_spec('PySide6'),'Optional Qt dependency missing')
class LivePreviewTests(unittest.TestCase):
    def test_live_edits_decisions_persistence_failure_and_stop(self):
        script=r'''
from dataclasses import replace
from pathlib import Path
import tempfile,time
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject,Qt,QPointF,QMetaObject
from PySide6.QtTest import QTest
from fx240.gui import create_engine,dispose_engine
from fx240.preferences import Preferences
from fx240.session import Settings,Session
from fx240.telemetry import Metric
app=QApplication([]);app.setQuitOnLastWindowClosed(False)
class Transport:
    active=0;maximum=0;opens=0
    brightness=[]
    def __init__(self,path):assert path=='/dev/hidraw999'
    def __enter__(self):
        Transport.active+=1;Transport.opens+=1
        Transport.maximum=max(Transport.maximum,Transport.active)
        return self
    def __exit__(self,*args):Transport.active-=1
    def send(self,reports,*args):
        if reports[0][5:8]==b'LIG':
            Transport.brightness.append(reports[0][10])
        return (0,0)

def wait(condition):
    deadline=time.monotonic()+6
    while not condition() and time.monotonic()<deadline:QTest.qWait(15)
    assert condition()
def click(item):
    point=item.mapToScene(QPointF(item.width()/2,item.height()/2)).toPoint()
    QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point)
def edit(x):
    workspace.model.select(1);workspace.model.updateSelected({'x':x})
    wait(lambda:workspace.ready and bridge.session.settings.scene_json==workspace.model.payload())
def finish(action):
    assert live.finish(action)
    wait(lambda:not live.active)
with tempfile.TemporaryDirectory() as folder:
    prefs=Preferences(Path(folder)/'settings.json')
    with patch('fx240.gui.find_devices',return_value=['/dev/hidraw999']):
        engine,bridge=create_engine(app,Settings(),preferences=prefs,provider=lambda:[Metric('ct','CPU synthetic',45,'C','synthetic')],session_factory=lambda *a,**k:Session(*a,transport_factory=Transport,**k))
    window=engine.rootObjects()[0];bridge.startup()
    wait(lambda:bridge.sending and bridge.session.frames>=2)
    window.setProperty('page',4)
    workspace=bridge.workspace;live=bridge.livePreview
    wait(lambda:workspace.ready)
    workspace.setProfileName('Live example')
    baseline=bridge.settings
    with patch.object(bridge.session,'configure',side_effect=ValueError('synthetic validation')):
        assert not live.start()
    assert not live.active and bridge.settings==baseline
    previous_frame=bridge.session.last_frame
    preview=window.findChild(QObject,'editorFramePreview')
    click(window.findChild(QObject,'draftPreviewButton'))
    assert live.active and not live.showOutput
    assert preview.property('source').toString().startswith('image://draft/')
    bridge.apply_frame(previous_frame)
    assert not live.showOutput
    assert preview.property('source').toString().startswith('image://draft/')
    wait(lambda:live.showOutput and bridge.sending)
    assert bridge.session.settings.layout_mode=='editor' and bridge.settings==baseline
    assert preview.property('source').toString()==bridge.previewUrl
    assert len(bridge.contentLabels)==4
    brightness=window.findChild(QObject,'designBrightnessControl')
    assert brightness.isVisible() and brightness.property('value')==100
    brightness.setProperty('value',37)
    assert QMetaObject.invokeMethod(brightness,'moved')
    wait(lambda:Transport.brightness==[37])
    assert workspace.model.lcdBrightness==37 and bridge.settings==baseline
    edit(22);assert bridge.settings==baseline
    workspace.model.updateSelected({'rotation':90})
    workspace.model.setTemperatureUnit('F')
    wait(lambda:workspace.ready and bridge.session.settings.scene_json==workspace.model.payload() and bridge.sensorRows[0]['target']=='113.0°F')
    rotated=workspace.model.payload()
    workspace.model.resetComposition(True)
    wait(lambda:workspace.ready and bridge.session.settings.scene_json==workspace.model.payload())
    wait(lambda:bridge.images.image.pixelColor(120,120).getRgb()[:3]==(0,0,0))
    assert not workspace.store.profiles and bridge.settings==baseline
    workspace.model.undo()
    wait(lambda:workspace.ready and bridge.session.settings.scene_json==rotated)
    bridge.flushPreferences();stored,_=prefs.load()
    assert stored.layout_mode=='focus' and not stored.profile_id and not stored.scene_json
    # Invalid media cannot replace the last accepted physical renderer.
    valid=bridge.session.settings.scene_json
    workspace.model.add_layer('media',str(Path(folder)/'missing.png'))
    wait(lambda:bool(workspace.notice))
    assert bridge.session.settings.scene_json==valid and bridge.settings==baseline
    workspace.model.undo();wait(lambda:workspace.ready)
    # The finish dialog can be cancelled without changing the trial or draft.
    live.requestEnd();QTest.qWait(50)
    dialog=window.findChild(QObject,'livePreviewDialog');assert dialog.property('visible')
    QTest.keyClick(window,Qt.Key_Escape);assert live.active
    # Leaving Editor also offers a decision instead of silently applying.
    window.setProperty('page',0);QTest.qWait(50)
    assert window.property('page')==4 and dialog.property('visible')
    click(window.findChild(QObject,'liveSaveOnly'))
    wait(lambda:not live.active)
    assert bridge.settings==baseline and bridge.sending
    assert window.findChild(QObject,'editorFramePreview').property('source').toString()==workspace.previewUrl
    assert len(bridge.contentLabels)==5
    assert workspace.model.payload()==valid
    assert Transport.opens==1 and Transport.maximum==1
    assert Transport.brightness==[37,100]
    assert '"lcd_brightness":37' in workspace.store.profiles[0]['scene']
    # Apply commits only after the main sender accepts the saved scene.
    assert live.start();edit(24)
    assert live.finish('apply')
    assert bridge.settings==baseline
    assert not live.frame({'config_request_id':live._finish_request-1,'config_error':'stale synthetic error'})
    assert live.finishing
    wait(lambda:not live.active and bridge.settings.profile_id==workspace.loadedId)
    applied=bridge.settings
    assert applied.scene_json==workspace.model.payload()
    # Saving an active profile during a trial must not auto-apply through profileSaved.
    assert live.start();edit(26);finish('save')
    assert bridge.settings==applied
    assert bridge.session.settings.scene_json==applied.scene_json
    assert workspace.store.get(workspace.loadedId)['scene']!=applied.scene_json
    # Stop must win over a pending live edit and remain paused after returning.
    assert live.start();edit(28)
    bridge.stopOutput();wait(lambda:not bridge.sending)
    finish('return');assert not bridge.session.output_requested
    assert not bridge.sending and bridge.settings==applied
    # Starting from paused output temporarily sends; returning restores paused.
    assert live.start();wait(lambda:bridge.sending)
    with patch.object(workspace.store,'save',side_effect=OSError('synthetic')):
        assert not live.finish('apply')
    assert live.active and bridge.settings==applied
    finish('return');wait(lambda:not bridge.sending)
    assert not bridge.session.output_requested
    # A rejected restore keeps the draft temporary and permits retry.
    assert live.start();edit(30)
    make_theme=bridge.session.make_theme
    def reject_restore(config):
        if config==applied:raise ValueError('synthetic renderer failure')
        return make_theme(config)
    with patch.object(bridge.session,'make_theme',side_effect=reject_restore):
        assert live.finish('return')
        wait(lambda:live.active and not live.finishing and 'Could not finish' in workspace.notice)
    assert bridge.settings==applied
    finish('return');assert bridge.settings==applied
    # Stop also wins over a queued Save and apply decision.
    assert live.start();edit(32)
    assert live.finish('apply')
    bridge.stopOutput()
    wait(lambda:not live.active and not bridge.sending)
    assert not bridge.session.output_requested
    applied=bridge.settings
    # Missing or ambiguous device selection never starts a sender.
    committed=bridge.settings;devices=bridge._devices;opens=Transport.opens
    bridge.settings=replace(committed,device=None);bridge._devices=[]
    assert not live.start()
    assert 'Select an LCD device' in workspace.notice
    assert Transport.opens==opens
    bridge.settings=committed;bridge._devices=devices
    # Close offers a decision, while cancelling preserves the running preview.
    assert live.start();wait(lambda:bridge.sending)
    assert not bridge.requestClose()
    QTest.qWait(30);assert dialog.property('visible')
    QTest.keyClick(window,Qt.Key_Escape);assert live.active
    with patch('fx240.gui.QCoreApplication.quit'):
        assert not bridge.requestClose()
        finish('return')
        wait(lambda:not bridge.running)
    bridge.flushPreferences();stored,_=prefs.load()
    assert stored.profile_id==applied.profile_id
    assert stored.scene_json==''
    assert Transport.active==0 and Transport.maximum==1
    opens=Transport.opens
    assert not live.start() # no new trial while the application is closing
    assert Transport.opens==opens
    dispose_engine(engine)
'''
        result=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True,timeout=45,
                              env={**os.environ,'QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software'})
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
