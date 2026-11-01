# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
import os
import subprocess
import sys
import unittest


@unittest.skipUnless(importlib.util.find_spec('PySide6'),'Optional Qt dependency missing')
class PreferenceNoticeTests(unittest.TestCase):
    def test_brand_alignment_and_recovery_details_inside_the_window(self):
        script=r'''
import os,json,tempfile
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QT_QUICK_BACKEND']='software'
from PySide6.QtCore import QObject,QPointF,Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from fx240.gui import create_engine,dispose_engine
from fx240.preferences import Preferences
app=QGuiApplication([])
with tempfile.TemporaryDirectory() as temp:
    path=Path(temp)/'settings.json'
    path.write_text(json.dumps({'version':1,'display':{'fps':17.5,'delay_ms':2.5,'quality':'bad','accent':'#ac8aff'},'application':{'language':'es','theme':'light'}}))
    store=Preferences(path);settings,ui=store.load()
    engine,bridge=create_engine(app,settings,provider=lambda:[],preferences=store,application=ui)
    window=engine.rootObjects()[0]
    app.processEvents()
    title=window.findChild(QObject,'brandTitle')
    subtitle=window.findChild(QObject,'brandSubtitle')
    assert abs(title.mapToScene(QPointF(0,0)).x()-subtitle.mapToScene(QPointF(0,0)).x())<1
    assert subtitle.mapToScene(QPointF(0,0)).y()>title.mapToScene(QPointF(0,0)).y()
    icon=window.findChild(QObject,'brandIcon')
    icon_center=icon.mapToScene(QPointF(0,icon.height()/2)).y()
    text_top=title.mapToScene(QPointF(0,0)).y()
    text_bottom=subtitle.mapToScene(QPointF(0,subtitle.height())).y()
    assert abs(icon_center-(text_top+text_bottom)/2)<1
    assert window.findChild(QObject,'preferenceBanner').property('visible')
    assert not window.findChild(QObject,'outputError').property('visible')
    assert 'Calidad JPEG' in bridge.preferenceDetails
    assert 'Se esperaba un número entero' in bridge.preferenceDetails
    assert 'Valor utilizado: 65' in bridge.preferenceDetails
    assert str(path) in bridge.preferenceDetails
    assert 'Fotogramas por segundo' not in bridge.preferenceDetails
    count=len(app.topLevelWindows())
    button=window.findChild(QObject,'preferenceDetailsButton')
    point=button.mapToScene(QPointF(button.width()/2,button.height()/2)).toPoint()
    QTest.mouseClick(window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
    app.processEvents()
    assert window.findChild(QObject,'preferenceDialog').property('visible')
    assert len(app.topLevelWindows())==count
    assert not window.grabWindow().isNull()
    bridge.flushPreferences()
    assert bridge.preferenceNotice==''
    restored,ui=Preferences(path).load()
    assert restored.fps==17.5 and restored.delay_ms==2.5
    dispose_engine(engine)
'''
        result=subprocess.run([sys.executable,'-c',script],env=os.environ.copy(),
                              capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        for error in ('TypeError:','ReferenceError:','Binding loop'):
            self.assertNotIn(error,result.stderr)
