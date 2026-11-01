import importlib.util
import os
import subprocess
import sys
import unittest


@unittest.skipUnless(importlib.util.find_spec('PySide6'),'Optional Qt dependency missing')
class DesktopPreferenceTests(unittest.TestCase):
    def test_live_units_language_save_and_restore_controls(self):
        script=r'''
import os,tempfile
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QT_QUICK_BACKEND']='software'
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QObject,QTimer
from fx240.gui import create_engine,dispose_engine
from fx240.preferences import Preferences
from fx240.session import Settings
from fx240.telemetry import Metric
app=QGuiApplication([])
folder=tempfile.TemporaryDirectory()
store=Preferences(Path(folder.name)/'settings.json')
engine,bridge=create_engine(app,Settings(),provider=lambda:[Metric('ct','CPU synthetic',45.125,'C','synthetic')],preferences=store)
bridge.start({},False)
worker=bridge.session
window=engine.rootObjects()[0]
errors=[]
def change():
    try:
        assert bridge.sensorRows[0]['target']=='45.1°C'
        window.setProperty('page',3);app.processEvents()
        buttons=[b for b in window.findChildren(QObject,'infoHelpButton') if b.property('visible')]
        assert buttons
        buttons[0].forceActiveFocus()
        for name,value in [('cometStyleControl',1),('temperatureUnitControl',1),('appThemeControl',1),('languageControl',1)]:
            window.findChild(QObject,name).setProperty('currentIndex',value)
        window.findChild(QObject,'cometSpeedControl').setProperty('value',2.0)
        window.findChild(QObject,'weightControl').setProperty('value',500)
        window.setProperty('lcdAccent','#ac8aff')
        assert bridge.language=='es'
        assert window.title()=='FX240 LCD STUDIO'
        assert window.property('lightTheme')
        assert not window.findChild(QObject,'advancedSettings').property('visible')
    except Exception as e:errors.append(repr(e))
    QTimer.singleShot(500,verify)
def verify():
    try:
        assert bridge.session is worker and not worker.stop_event.is_set()
        assert any(t.property('visible') for t in window.findChildren(QObject,'infoTooltip'))
        assert bridge.sensorRows[0]['raw']=='45.125 C'
        assert bridge.sensorRows[0]['target']=='113.2°F'
        assert bridge.status=='LCD en pausa'
        # Translating model labels must not change their selected semantic values.
        bridge.setLanguage('en');bridge.setLanguage('es')
        assert window.findChild(QObject,'cometStyleControl').property('currentIndex')==1
        assert window.findChild(QObject,'temperatureUnitControl').property('currentIndex')==1
        bridge.flushPreferences()
        loaded,ui=Preferences(store.path).load()
        assert loaded.comet_style=='rainbow' and loaded.temperature_unit=='F'
        assert loaded.accent=='#ac8aff' and loaded.comet_speed==2 and loaded.font_weight==500
        assert ui=={'language':'es','theme':'light'}
        restored,other=create_engine(app,loaded,provider=lambda:[],preferences=store,application=ui)
        w=restored.rootObjects()[0]
        assert w.property('lightTheme') and other.language=='es'
        assert w.findChild(QObject,'languageControl').property('currentIndex')==1
        assert w.findChild(QObject,'temperatureUnitControl').property('currentIndex')==1
        assert w.findChild(QObject,'cometStyleControl').property('currentIndex')==1
        assert w.findChild(QObject,'cometSpeedControl').property('value')==2
        assert w.findChild(QObject,'weightControl').property('value')==500
        dispose_engine(restored)
    except Exception as e:errors.append(repr(e))
    bridge.stop();QTimer.singleShot(200,app.quit)
QTimer.singleShot(400,change)
app.exec()
worker.stop();worker.thread.join(2)
dispose_engine(engine)
folder.cleanup()
assert not errors,errors
'''
        result=subprocess.run([sys.executable,'-c',script],env=os.environ.copy(),
                              capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        for error in ('TypeError:','ReferenceError:','Cannot open','Binding loop'):
            self.assertNotIn(error,result.stderr)
