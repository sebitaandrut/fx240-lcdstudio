import importlib.util
import os
import subprocess
import sys
import unittest


@unittest.skipUnless(importlib.util.find_spec('PySide6'),'Optional Qt dependency missing')
class TrayTests(unittest.TestCase):
    def test_hide_restore_unavailable_fallback_and_graceful_quit(self):
        script=r'''
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QT_QUICK_BACKEND']='software'
from PySide6.QtCore import QObject,QTimer,Signal,Qt
from PySide6.QtWidgets import QApplication,QSystemTrayIcon
from fx240.gui import create_engine,dispose_engine
from fx240.tray import TrayController,tray_icon
from fx240.session import Settings
from fx240.telemetry import Metric
class FakeTray(QObject):
    activated=Signal(object)
    available=True
    @staticmethod
    def isSystemTrayAvailable():return FakeTray.available
    def __init__(self,icon,parent):super().__init__(parent);assert not icon.isNull()
    def setIcon(self,icon):assert not icon.isNull()
    def setToolTip(self,text):pass
    def setContextMenu(self,menu):pass
    def show(self):pass
    def hide(self):pass
app=QApplication([])
app.setQuitOnLastWindowClosed(False)
for size in (16,22,32):
    dark=tray_icon(Qt.ColorScheme.Dark).pixmap(size,size).toImage()
    light=tray_icon(Qt.ColorScheme.Light).pixmap(size,size).toImage()
    fallback=tray_icon(Qt.ColorScheme.Unknown).pixmap(size,size).toImage()
    assert not dark.isNull() and not light.isNull() and not fallback.isNull()
    assert dark!=light
    assert any(dark.pixelColor(x,y).alpha()>0 for y in range(size) for x in range(size))
engine,bridge=create_engine(app,Settings(),provider=lambda:[Metric('ct','CPU synthetic',45,'C','synthetic')])
window=engine.rootObjects()[0]
tray=TrayController(window,bridge,tray_factory=FakeTray)
tray.update_icon(Qt.ColorScheme.Dark)
tray.update_icon(Qt.ColorScheme.Light)
bridge.start({},False)
worker=bridge.session
errors=[]
before=0
def begin():
    global before
    try:
        assert bridge.trayAvailable and bridge.running
        before=worker.frames
        window.showMinimized()
        assert tray.hidden and not window.isVisible()
    except Exception as e:errors.append(repr(e))
    QTimer.singleShot(250,finish)
def finish():
    try:
        assert worker.frames>before
        assert bridge.session is worker and not worker.stop_event.is_set()
        tray.activate(QSystemTrayIcon.ActivationReason.Trigger)
        assert window.isVisible() and not tray.hidden
        tray.minimize()
        assert not window.isVisible()
        FakeTray.available=False
        tray.check_availability()
        assert not bridge.trayAvailable
        assert window.isVisible() and not tray.hidden
        tray.minimize()
        assert window.isVisible() # no invisible, inaccessible window
        assert [a.text() for a in tray.menu.actions()]==['Show studio','','Quit']
        bridge.setLanguage('es')
        assert [a.text() for a in tray.menu.actions()]==['Mostrar estudio','','Salir']
    except Exception as e:errors.append(repr(e))
    tray.quit()
QTimer.singleShot(300,begin)
QTimer.singleShot(4000,app.quit)
app.exec()
worker.stop();worker.thread.join(2)
assert not worker.thread.is_alive()
assert bridge._closing and not bridge.running
assert not errors,errors
tray.dispose()
dispose_engine(engine)
'''
        result=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True,
                              env=os.environ.copy(),timeout=10)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertNotIn('Traceback',result.stderr)
