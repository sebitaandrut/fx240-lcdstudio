# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the embedded font picker in both Studio themes without HID access."""
import importlib.util
import os
import subprocess
import sys
import unittest


@unittest.skipUnless(importlib.util.find_spec('PySide6'), 'Optional Qt dependency missing')
class AppearanceTests(unittest.TestCase):
    def test_search_and_select_font_in_both_themes(self):
        script=r'''
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject,QPointF,Qt
from PySide6.QtTest import QTest
from fx240.gui import create_engine,dispose_engine
from fx240.session import Settings
app=QApplication([])
with patch('fx240.gui.find_devices',return_value=[]):
    engine,bridge=create_engine(app,Settings())
window=engine.rootObjects()[0]
assert window.minimumWidth()==1200
assert window.minimumHeight()==760
picker=window.findChild(QObject,'systemFontControl')
picker.setProperty('model',['Bundled Outfit (default)','Example Regular','Example Bold'])
for theme in (0,1):
    window.findChild(QObject,'appThemeControl').setProperty('currentIndex',theme)
    QTest.qWait(80)
    count=len(app.topLevelWindows())
    point=picker.mapToScene(QPointF(picker.width()/2,picker.height()/2)).toPoint()
    QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point)
    popup=picker.findChild(QObject,'fontSearchPopup')
    assert popup.property('visible')
    search=picker.findChild(QObject,'fontSearchField')
    search.setProperty('text','bold')
    QTest.keyClick(window,Qt.Key_Return)
    assert picker.property('currentIndex')==2
    assert not popup.property('visible')
    assert len(app.topLevelWindows())==count
    assert bridge.session is None
    picker.setProperty('currentIndex',0)
window.setProperty('page',4);QTest.qWait(120)
number=window.findChild(QObject,'editorX')
before=bridge.workspace.model.selected['x']
point=number.mapToScene(QPointF(number.width()-16,number.height()/2)).toPoint()
QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point)
assert bridge.workspace.model.selected['x']==before+1
number.forceActiveFocus()
QTest.keyClick(window,Qt.Key_Up)
assert bridge.workspace.model.selected['x']==before+2
payload=bridge.workspace.model.payload()
# Long translations, a long font label, scrollbars and window resizing must not
# push inspector controls past the viewport's right edge.
window.setProperty('page',0)
for language in ('en','es'):
    bridge.setLanguage(language)
    for theme in (0,1):
        window.findChild(QObject,'appThemeControl').setProperty('currentIndex',theme)
        for width in (1200,1280,1440,1600):
            window.setWidth(width);window.setHeight(760);QTest.qWait(50)
            content=window.findChild(QObject,'focusPropertiesContent')
            for child in content.childItems():
                if child.isVisible():
                    assert child.x()>=-1 and child.x()+child.width()<=content.width()+1,(width,child.x(),child.width(),content.width())
            assert window.findChild(QObject,'focusPropertiesScroll').height()>300
            preview=window.findChild(QObject,'framePreview')
            assert preview.width()>=280 and preview.height()>=280
            assert window.findChild(QObject,'appearanceWorkspace').property('columns')==3
            palette=window.findChild(QObject,'accentPalette')
            custom=window.findChild(QObject,'customAccentButton')
            center=custom.mapToScene(QPointF(0,custom.height()/2)).y()
            animation=window.findChild(QObject,'animationControl')
            assert abs(custom.width()-animation.width())<1
            assert abs(custom.mapToScene(QPointF(0,0)).x()-animation.mapToScene(QPointF(0,0)).x())<1
            swatches=[item for item in palette.childItems() if item.objectName().startswith('accentSwatch-')]
            assert len(swatches)==6
            for swatch in swatches:
                assert abs(swatch.mapToScene(QPointF(0,swatch.height()/2)).y()-center)<1

            window.setProperty('page',4);QTest.qWait(50)
            toolbar=window.findChild(QObject,'compositionToolbar')
            primary=window.findChild(QObject,'compositionPrimaryActions')
            secondary=window.findChild(QObject,'compositionSecondaryActions')
            assert toolbar.height()<=80
            assert primary.width()>=window.width()-240
            assert window.findChild(QObject,'profileNameControl').width()>=180
            for row in (primary,secondary):
                for child in row.childItems():
                    if child.isVisible():
                        assert child.x()>=-1 and child.x()+child.width()<=row.width()+1
            canvas=window.findChild(QObject,'editorCanvas')
            assert canvas.width()>=180 and canvas.height()>=180
            assert canvas.mapToScene(QPointF(0,0)).y()>toolbar.mapToScene(QPointF(0,toolbar.height())).y()
            window.setProperty('page',0);QTest.qWait(30)
window.setWidth(1200);window.setProperty('page',4);QTest.qWait(100)
bridge.setLanguage('es')
dialog=window.findChild(QObject,'discardDraftDialog')
for theme in (0,1):
    window.findChild(QObject,'appThemeControl').setProperty('currentIndex',theme)
    bridge.workspace.requestNew();QTest.qWait(50)
    assert dialog.property('visible')
    assert dialog.property('acceptText')=='Descartar borrador'
    assert dialog.findChild(QObject,'confirmationCancel').property('text')=='Cancelar'
    QTest.keyClick(window,Qt.Key_Escape)
    assert not dialog.property('visible')
    assert bridge.workspace.model.payload()==payload
bridge.workspace.requestNew();QTest.qWait(50)
button=dialog.findChild(QObject,'confirmationAccept')
point=button.mapToScene(QPointF(button.width()/2,button.height()/2)).toPoint()
QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point)
assert not dialog.property('visible')
assert bridge.workspace.model.payload()!=payload
dispose_engine(engine)
'''
        result=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True,timeout=20,
                              env={**os.environ,'QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software'})
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
