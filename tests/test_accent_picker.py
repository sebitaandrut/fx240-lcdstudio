import importlib.util
import os
import subprocess
import sys
import unittest


@unittest.skipUnless(importlib.util.find_spec('PySide6'),'Optional Qt dependency missing')
class InlineAccentTests(unittest.TestCase):
    def test_same_window_picker_hex_hsv_and_live_apply_in_both_themes(self):
        script=r'''
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QT_QUICK_BACKEND']='software'
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QObject,QPointF,Qt,QTimer,QMetaObject
from PySide6.QtTest import QTest
from fx240.gui import create_engine,dispose_engine
from fx240.session import Settings
app=QGuiApplication([])
engine,bridge=create_engine(app,Settings(),provider=lambda:[])
bridge.start({},False)
worker=bridge.session
window=engine.rootObjects()[0]
errors=[]
def click(item,x=None,y=None):
    p=item.mapToScene(QPointF(item.width()/2 if x is None else x,item.height()/2 if y is None else y)).toPoint()
    QTest.mouseClick(window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,p)
def run():
    try:
        count=len(app.topLevelWindows())
        custom=window.findChild(QObject,'customAccentButton')
        for theme in (0,1):
            window.findChild(QObject,'appThemeControl').setProperty('currentIndex',theme)
            click(custom)
            app.processEvents()
            picker=window.findChild(QObject,'accentPicker')
            assert picker.property('visible')
            assert len(app.topLevelWindows())==count
            assert abs(picker.property('x')+picker.property('width')-custom.mapToScene(QPointF(custom.width(),0)).x())<1
            field=window.findChild(QObject,'accentHexControl')
            field.forceActiveFocus()
            QTest.keyClick(window,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier)
            for key in (Qt.Key.Key_NumberSign,Qt.Key.Key_2,Qt.Key.Key_4,Qt.Key.Key_6,Qt.Key.Key_8,Qt.Key.Key_A,Qt.Key.Key_B):QTest.keyClick(window,key)
            assert field.property('acceptableInput')
            assert window.property('lcdAccent').name()=='#2468ab'
            before=window.property('lcdAccent').name()
            field.setProperty('text','#12')
            QMetaObject.invokeMethod(field,'textEdited')
            assert not field.property('acceptableInput')
            assert window.property('lcdAccent').name()==before
            # Visual selection recovers a partial hex edit and stays a valid RGB color.
            sv=window.findChild(QObject,'accentSaturationValue')
            click(sv,sv.width()*.7,sv.height()*.3)
            assert field.property('acceptableInput')
            hue=window.findChild(QObject,'accentHueControl')
            click(hue,hue.width()*.8,hue.height()/2)
            assert field.property('acceptableInput')
            assert not window.grabWindow().isNull()
            QTest.keyClick(window,Qt.Key.Key_Escape)
            assert not picker.property('visible')
        # Outside click dismisses the same in-window popup.
        click(custom)
        QTest.mouseClick(window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,window.findChild(QObject,'framePreview').mapToScene(QPointF(100,100)).toPoint())
        assert not picker.property('visible')
    except Exception as e:errors.append(repr(e))
    QTimer.singleShot(400,finish)
def finish():
    try:
        assert bridge.session is worker and not worker.stop_event.is_set()
        assert worker.settings.accent==window.property('lcdAccent').name()
        assert not bridge.errorMessage
    except Exception as e:errors.append(repr(e))
    bridge.stop();QTimer.singleShot(150,app.quit)
QTimer.singleShot(300,run)
app.exec()
worker.stop();worker.thread.join(2)
dispose_engine(engine)
assert not errors,errors
'''
        result=subprocess.run([sys.executable,'-c',script],env=os.environ.copy(),
                              capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        for error in ('TypeError:','ReferenceError:','Binding loop'):
            self.assertNotIn(error,result.stderr)
