# SPDX-License-Identifier: GPL-3.0-or-later
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
from PySide6.QtCore import QObject,QPoint,QPointF,Qt,QTimer,QMetaObject
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
        window.setProperty('page',4);app.processEvents()
        model=bridge.workspace.model
        custom=window.findChild(QObject,'layerColorPickerButton')
        scroll=window.findChild(QObject,'editorPropertiesScroll').property('contentItem')
        scroll.setProperty('contentY',max(0,custom.mapToScene(QPointF(0,0)).y()-320))
        app.processEvents()
        for theme in (0,1):
            bridge.setUiTheme('light' if theme else 'dark')
            QTest.qWait(40)
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
            assert model.selected['color']=='#2468ab'
            before=model.selected['color']
            field.setProperty('text','#12')
            QMetaObject.invokeMethod(field,'textEdited')
            assert not field.property('acceptableInput')
            assert model.selected['color']==before
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
        QTest.mouseClick(window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(10,10))
        assert not picker.property('visible')
        previous_color=model.selected['color']
        click(window.findChild(QObject,'addGradientLayer'))
        model=bridge.workspace.model
        assert model.selected['kind']=='gradient' and model.scene['layers'][0]['kind']=='gradient'
        assert model.selected['path'] is None
        def find_item(item,name):
            if item.objectName()==name:return item
            for child in item.childItems():
                found=find_item(child,name)
                if found is not None:return found
            return None
        for name, field_name, color in [('gradient-color','color','#337788'),
                                       ('gradient-gradient_color','gradient_color','#8543a0')]:
            button=find_item(window.contentItem(),name)
            assert button is not None and button.property('visible')
            button.forceActiveFocus()
            QTest.keyClick(window,Qt.Key.Key_Space)
            assert picker.property('visible')
            field.setProperty('text',color)
            QMetaObject.invokeMethod(field,'textEdited')
            assert model.selected[field_name]==color
            QTest.keyClick(window,Qt.Key.Key_Escape)
            assert not picker.property('visible')
        assert model.scene['layers'][1]['color']==previous_color
        assert model.selected['color']=='#337788' and model.selected['gradient_color']=='#8543a0'
        style=window.findChild(QObject,'gradientStyleControl')
        direction=window.findChild(QObject,'gradientDirectionControl')
        style.forceActiveFocus()
        QTest.keyClick(window,Qt.Key.Key_Down)
        assert model.selected['gradient_style']=='linear'
        direction.forceActiveFocus()
        QTest.keyClick(window,Qt.Key.Key_Up)
        assert model.selected['gradient_angle']==15
        style.forceActiveFocus()
        QTest.keyClick(window,Qt.Key.Key_Down)
        assert model.selected['gradient_style']=='radial' and not direction.property('visible')
        click(window.findChild(QObject,'addGradientLayer'))
        assert sum(item['kind']=='gradient' for item in model.scene['layers'])==1
        effects_button=window.findChild(QObject,'addEffectsButton')
        menu=window.findChild(QObject,'effectsMenu')
        for key in ('dual_cpu','dual_gpu','radar'):
            click(effects_button)
            assert menu.property('visible')
            content=menu.property('contentItem')
            QTest.qWait(40)
            entry=find_item(content,'addEffect-'+key)
            assert entry is not None
            click(entry)
            QTest.qWait(20)
            assert not menu.property('visible') and model.selected['effect']==key, (key,model.selected,menu.property('visible'))
        assert [item['kind'] for item in model.scene['layers'][:5]]==['gradient','effect','effect','effect','text']
        model.undo()
        assert not any(item['effect']=='radar' for item in model.scene['layers'])
    except Exception:
        import traceback
        errors.append(traceback.format_exc())
    QTimer.singleShot(400,finish)
def finish():
    try:
        assert bridge.session is worker and not worker.stop_event.is_set()
        assert worker.settings.accent==Settings().accent
        assert not bridge.errorMessage
    except Exception:
        import traceback
        errors.append(traceback.format_exc())
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
