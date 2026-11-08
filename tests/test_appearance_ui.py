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
from PySide6.QtCore import QObject,QPointF,Qt,QMetaObject,Q_ARG
from PySide6.QtTest import QTest
from fx240.gui import create_engine,dispose_engine
from fx240.session import Settings
app=QApplication([])
with patch('fx240.gui.find_devices',return_value=[]):
    engine,bridge=create_engine(app,Settings())
window=engine.rootObjects()[0]
assert window.minimumWidth()==1200
assert window.minimumHeight()==760
window.setProperty('page',4);QTest.qWait(80)
picker=window.findChild(QObject,'systemFontControl')
picker.setProperty('model',['Bundled Outfit (default)','Example Regular','Example Bold'])
for theme in (0,1):
    bridge.setUiTheme('light' if theme else 'dark')
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
from fx240.typography import resolve_font
model=bridge.workspace.model
model.select(1)
model.updateSelected({'weight':500})
model.toggleSelection(0)
font_path=str(resolve_font())
bridge._system_fonts=[('Synthetic Outfit',font_path)]
assert picker.isVisible()
assert QMetaObject.invokeMethod(picker,'activated',Q_ARG(int,1))
assert all(item['font_path']==font_path for item in model.selected_text_layers().values())
weight=window.findChild(QObject,'mixedWeightControl')
assert weight.isVisible()
weight.setProperty('text','350')
assert QMetaObject.invokeMethod(weight,'accepted')
assert all(item['weight']==350 for item in model.selected_text_layers().values())
model.undo()
assert sorted(item['weight'] for item in model.selected_text_layers().values())==[350,500]
model.undo()
assert all(item['font_path'] is None for item in model.selected_text_layers().values())
model.select(0)
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
def check_draft_actions():
    new=window.findChild(QObject,'newDesignButton')
    resume=window.findChild(QObject,'continueDraftButton')
    assert resume.isVisible()
    assert abs(new.mapToScene(QPointF()).y()-resume.mapToScene(QPointF()).y())<=1
    gap=resume.mapToScene(QPointF()).x()-new.mapToScene(QPointF(new.width(),0)).x()
    assert 8<=gap<=12
    assert not window.findChild(QObject,'savedDesignGrid').isVisible()
# Long translations, a long font label, scrollbars and window resizing must not
# push inspector controls past the viewport's right edge.
window.setProperty('page',0)
for language in ('en','es'):
    bridge.setLanguage(language)
    for theme in (0,1):
        bridge.setUiTheme('light' if theme else 'dark')
        for width in (1200,1280,1440,1600):
            window.setWidth(width);window.setHeight(760);QTest.qWait(50)
            gallery=window.findChild(QObject,'designGallery')
            assert gallery.property('visible')
            assert window.findChild(QObject,'focusInspector') is None
            preview=window.findChild(QObject,'framePreview')
            assert preview.width()>=280 and preview.height()>=280
            assert window.findChild(QObject,'applyDesignButton') is None
            grid=window.findChild(QObject,'builtinDesignGrid')
            assert grid.property('columns')==(4 if grid.width()>=720 else 2)
            assert grid.width()<gallery.width()
            check_draft_actions()

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
for width,height in ((2548,967),(2474,1345),(2560,1440)):
    window.resize(width,height)
    QTest.qWait(100)
    gallery=window.findChild(QObject,'designGallery')
    grid=window.findChild(QObject,'builtinDesignGrid')
    preview=window.findChild(QObject,'framePreview')
    edit=window.findChild(QObject,'openEditorButton')
    left_gap=gallery.mapToScene(QPointF()).x()-180
    right_gap=width-gallery.mapToScene(QPointF(gallery.width(),0)).x()
    assert 20<=left_gap<=48 and abs(left_gap-right_gap)<=1
    assert grid.property('columns')==4 and gallery.property('thumbnailSize')>=155
    assert window.findChild(QObject,'designPreviewPanel').width()<=720
    assert 490<=preview.width()<=560 and preview.width()==preview.height()
    gap=edit.mapToScene(QPointF()).y()-preview.mapToScene(QPointF(0,preview.height())).y()
    assert 10<=gap<=14
    check_draft_actions()
    window.setProperty('page',4);QTest.qWait(100)
    canvas=window.findChild(QObject,'editorCanvas')
    assert 510<=canvas.width()<=660 and canvas.width()==canvas.height()
    layers=window.findChild(QObject,'editorLayersPanel')
    properties=window.findChild(QObject,'editorPropertiesPanel')
    assert 300<=layers.width()<=320 and 330<=properties.width()<=380
    assert abs(layers.mapToScene(QPointF()).x()-180-left_gap)<=1
    assert abs(width-properties.mapToScene(QPointF(properties.width(),0)).x()-right_gap)<=1
    assert window.findChild(QObject,'profileNameControl').width()<=460
    assert bridge.workspace.model.payload()==payload
    window.setProperty('page',0);QTest.qWait(50)
window.resize(1200,760)
window.setWidth(1200);window.setProperty('page',4);QTest.qWait(100)
bridge.setLanguage('es')
dialog=window.findChild(QObject,'discardDraftDialog')
for theme in (0,1):
    bridge.setUiTheme('light' if theme else 'dark')
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
