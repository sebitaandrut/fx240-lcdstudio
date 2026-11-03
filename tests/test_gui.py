# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
import unittest

HAS_QT=importlib.util.find_spec('PySide6') is not None


@unittest.skipUnless(HAS_QT,'Optional PySide6 desktop dependency is not installed')
class DiagnosticTests(unittest.TestCase):
    def test_rows_show_same_snapshot_in_raw_and_lcd_formats(self):
        from fx240.gui import diagnostic_rows
        from fx240.telemetry import Metric
        event={'temperature_decimals':1,'metrics':[Metric('ct','CPU Tctl',45.125,'C','sensor-source')]}
        rows=diagnostic_rows(event)
        self.assertEqual(rows[0]['raw'],'45.125 C')
        self.assertEqual(rows[0]['target'],'45.1°C')
        self.assertEqual(rows[0]['source'],'sensor-source')
        self.assertEqual(rows[1]['target'],'N/A')
        self.assertEqual(len(rows),4)

    def test_fahrenheit_target_keeps_raw_celsius(self):
        from fx240.gui import diagnostic_rows
        from fx240.telemetry import Metric
        rows=diagnostic_rows({'temperature_decimals':1,'temperature_unit':'F',
                              'metrics':[Metric('ct','CPU Tctl',50,'C','synthetic')]})
        self.assertEqual(rows[0]['raw'],'50.000 C')
        self.assertEqual(rows[0]['target'],'122.0°F')

    def test_save_failure_is_visible_without_changing_valid_settings(self):
        from PySide6.QtCore import QCoreApplication
        from fx240.gui import Bridge
        from fx240.session import Settings
        from unittest.mock import Mock
        app=QCoreApplication.instance() or QCoreApplication([])
        store=Mock();store.warning='';store.save.side_effect=OSError('disk full')
        bridge=Bridge(Settings(),image_provider=Mock(),preferences=store)
        bridge.timer.stop()
        bridge.flushPreferences()
        self.assertIn('Preferences could not be saved',bridge.errorMessage)
        self.assertEqual(bridge.runtimeError,'')
        self.assertTrue(bridge.preferenceCanRetry)
        self.assertIn('disk full',bridge.preferenceDetails)
        self.assertEqual(bridge.settings,Settings())
        bridge.setLanguage('es')
        bridge.save_timer.stop()
        bridge.flushPreferences()
        self.assertIn('No se pudieron guardar',bridge.errorMessage)
        self.assertIn('Archivo de configuración',bridge.preferenceDetails)
        store.save.side_effect=None
        bridge.flushPreferences()
        self.assertEqual(bridge.preferenceNotice,'')
        self.assertEqual(bridge.preferenceDetails,'')

    def test_worker_error_reaches_desktop_state(self):
        from PySide6.QtCore import QCoreApplication
        from fx240.gui import Bridge
        from fx240.session import Session,Settings
        from unittest.mock import Mock
        app=QCoreApplication.instance() or QCoreApplication([])
        bridge=Bridge(Settings(),image_provider=Mock())
        bridge.timer.stop()
        bridge.session=Session(Settings())
        bridge._running=True
        bridge.session.publish({'kind':'stopped','error':'device disconnected','frames':0})
        bridge.poll()
        self.assertFalse(bridge.running)
        self.assertEqual(bridge.errorMessage,'device disconnected')

    def test_startup_automatically_selects_one_device_and_sends(self):
        from PySide6.QtCore import QCoreApplication
        from fx240.gui import Bridge
        from fx240.session import Settings
        from unittest.mock import Mock,patch
        app=QCoreApplication.instance() or QCoreApplication([])
        factory=Mock()
        with patch('fx240.gui.find_devices',return_value=['/dev/fake']):
            bridge=Bridge(Settings(),session_factory=factory,image_provider=Mock())
        bridge.timer.stop()
        bridge.startup()
        self.assertTrue(bridge.sending)
        self.assertEqual(factory.call_args.args[0].device,'/dev/fake')
        self.assertTrue(factory.call_args.kwargs['send'])
        bridge.stopOutput()
        factory.return_value.set_output.assert_called_once_with(False)
        factory.return_value.stop.assert_not_called()
        self.assertTrue(bridge.running)

    def test_edit_during_transmission_configures_same_worker(self):
        from PySide6.QtCore import QCoreApplication
        from fx240.gui import Bridge
        from fx240.session import Settings
        from unittest.mock import Mock
        app=QCoreApplication.instance() or QCoreApplication([])
        factory=Mock()
        bridge=Bridge(Settings(device='/dev/fake'),session_factory=factory,image_provider=Mock())
        bridge.timer.stop()
        bridge.start({},True)
        bridge.applySettings({'weight':500,'device':'/dev/fake'})
        config,send=factory.return_value.configure.call_args.args
        self.assertEqual(config.font_weight,500)
        self.assertIsNone(send)
        factory.return_value.stop.assert_not_called()
        self.assertTrue(bridge.sending)

    def test_ambiguous_device_startup_keeps_preview_without_output(self):
        from PySide6.QtCore import QCoreApplication
        from fx240.gui import Bridge
        from fx240.session import Settings
        from unittest.mock import Mock,patch
        app=QCoreApplication.instance() or QCoreApplication([])
        factory=Mock()
        with patch('fx240.gui.find_devices',return_value=['/dev/a','/dev/b']):
            bridge=Bridge(Settings(),session_factory=factory,image_provider=Mock())
        bridge.timer.stop()
        bridge.startup()
        self.assertFalse(bridge.sending)
        self.assertTrue(bridge.running)
        self.assertFalse(factory.call_args.kwargs['send'])

    def test_lucide_svg_assets_and_notices(self):
        from pathlib import Path
        import hashlib,json
        from PySide6.QtSvg import QSvgRenderer
        import fx240.gui
        root=Path(fx240.gui.__file__).parent/'assets/icons'
        sources=json.loads((root/'sources.json').read_text())
        for name,record in sources.items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),record['sha256'])
            if name.endswith('.svg'):
                self.assertTrue(QSvgRenderer(str(root/name)).isValid(),name)
        notice=(root/'LICENSE.txt').read_text()
        self.assertIn('ISC License',notice)
        self.assertIn('The MIT License',notice)
        for theme in ('dark','light'):
            variants=list((root/theme).glob('*.svg'))
            self.assertTrue(variants)
            for path in variants:
                self.assertTrue(QSvgRenderer(str(path)).isValid(),str(path))

    def test_stop_preserves_last_jpeg_and_its_sensor_sample(self):
        from PySide6.QtCore import QCoreApplication
        from fx240.gui import Bridge,FrameProvider
        from fx240.session import Session,Settings
        from fx240.telemetry import Metric
        from PIL import Image
        app=QCoreApplication.instance() or QCoreApplication([])
        bridge=Bridge(Settings(),image_provider=FrameProvider())
        bridge.timer.stop()
        bridge.session=Session(Settings())
        frame={'kind':'frame','image':Image.new('RGB',(240,240),(12,34,56)),
               'metrics':[Metric('ct','CPU Tctl',45.125,'C','synthetic')],
               'sequence':7,'timestamp':'synthetic timestamp','temperature_decimals':1,
               'sent':True,'frames':24,'transmission_ms':12,'reports':7,'pipeline_ms':16}
        bridge.session.publish(frame)
        bridge.session.publish({'kind':'stopped','error':None,'frames':24,'last_frame':frame})
        bridge.poll()
        self.assertEqual(bridge.images.image.pixelColor(120,120).getRgb()[:3],(12,34,56))
        self.assertEqual(bridge.sensorRows[0]['raw'],'45.125 C')
        self.assertEqual(bridge.sensorRows[0]['target'],'45.1°C')
        self.assertIn('Sample #7',bridge.sampleLabel)
        self.assertEqual(bridge.status,'Stopped')


@unittest.skipUnless(HAS_QT,'Optional PySide6 desktop dependency is not installed')
class QmlSmokeTests(unittest.TestCase):
    def test_theme_switch_and_dropdown_keyboard_selection(self):
        import os,subprocess,sys
        script=r"""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QT_QUICK_BACKEND']='software'
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QObject,QPointF,Qt
from PySide6.QtTest import QTest
from fx240.gui import create_engine,dispose_engine
from fx240.session import Settings
app=QGuiApplication([])
engine,bridge=create_engine(app,Settings(),provider=lambda:[])
window=engine.rootObjects()[0]
assert window.title()=='FX240 LCD STUDIO'
assert app.applicationName()=='FX240 LCD STUDIO'
assert app.desktopFileName()=='org.fx240lcdstudio'
assert not app.windowIcon().isNull()
assert window.findChild(QObject,'brandIcon')
choice=window.findChild(QObject,'cometStyleControl')
for theme in (0,1):
    window.findChild(QObject,'appThemeControl').setProperty('currentIndex',theme)
    app.processEvents()
    assert window.property('lightTheme')==bool(theme)
    assert window.title()=='FX240 LCD STUDIO'
    assert window.findChild(QObject,'brandIcon').property('implicitWidth')>0
    assert bridge.session is None # application theme alone must not start/reconfigure output
    for page in (0,1,2,3):
        window.setProperty('page',page)
        app.processEvents()
        assert not window.grabWindow().isNull()
    window.setProperty('page',0)
    app.processEvents()
    scroll=window.findChild(QObject,'pageScroll').property('contentItem')
    scroll.setProperty('contentY',max(0,scroll.property('contentY')+choice.mapToScene(QPointF(0,0)).y()-220))
    app.processEvents()
    point=choice.mapToScene(QPointF(choice.width()/2,choice.height()/2)).toPoint()
    QTest.mouseClick(window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
    assert choice.property('down')
    assert not window.grabWindow().isNull()
    QTest.keyClick(window,Qt.Key.Key_Escape)
    assert not choice.property('down')
assert not bridge.trayAvailable
window.findChild(QObject,'appThemeControl').setProperty('currentIndex',0)
# Popup selection remains keyboard operable after custom styling.
QTest.mouseClick(window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
QTest.keyClick(window,Qt.Key.Key_Down)
QTest.keyClick(window,Qt.Key.Key_Return)
assert choice.property('currentIndex')==1
# Output controls and labels share a vertical center.
status=window.findChild(QObject,'outputStatus')
button=window.findChild(QObject,'sendButton')
a=status.mapToScene(QPointF(0,status.height()/2))
b=button.mapToScene(QPointF(0,button.height()/2))
assert abs(a.y()-b.y())<1,(a,b)
dispose_engine(engine)
"""
        result=subprocess.run([sys.executable,'-c',script],env=os.environ.copy(),
                              text=True,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        for error in ('TypeError:','ReferenceError:','Cannot open'):
            self.assertNotIn(error,result.stderr)

    def test_qml_loads_preview_and_stops_without_hardware(self):
        import os
        from pathlib import Path
        import subprocess
        import sys
        script = r"""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QT_QUICK_BACKEND']='software'
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QObject,QPointF,QTimer
from fx240.gui import create_engine,dispose_engine
from fx240.session import Settings
from fx240.telemetry import Metric
app=QGuiApplication([])
engine,bridge=create_engine(app,Settings(),provider=lambda:[Metric('ct','CPU Tctl',45.125,'C','synthetic')])
bridge.start({},False)
errors=[]
def verify():
    try:
        assert bridge.running and not bridge.sending
        assert bridge.sensorRows[0]['raw']=='45.125 C'
        assert bridge.sensorRows[0]['target']=='45.1°C'
        window=engine.rootObjects()[0]
        button=window.findChild(QObject,'stopButton')
        assert button.property('text')=='Stop display'
        assert not button.property('visible')
        for page in (0,1,2,3):
            window.setProperty('page',page)
            app.processEvents()
            assert not window.grabWindow().isNull()
            assert not button.property('visible')
        window.setProperty('page',0)
        button=window.findChild(QObject,'stopButton')
        card=window.findChild(QObject,'outputCard')
        p=button.mapToItem(card,QPointF(0,0))
        assert p.y() >= 0 and p.y()+button.height() <= card.height()
        assert not button.property('enabled')
        window.findChild(QObject,'weightControl').setProperty('value',500)
        window.findChild(QObject,'cometSpeedControl').setProperty('value',2.0)
        window.setProperty('lcdAccent','#ac8aff')
        window.findChild(QObject,'cometStyleControl').setProperty('currentIndex',1)
        window.findChild(QObject,'decimalControl').setProperty('currentIndex',0)
        assert window.findChild(QObject,'outputStatus')
        assert not window.findChild(QObject,'outputError').property('visible')
    except Exception as error:
        errors.append(str(error))
    QTimer.singleShot(400,verify_edit)
def verify_edit():
    if bridge.session.settings.font_weight!=500:errors.append('Live QML edit did not apply')
    if bridge.session.settings.comet_speed!=2:errors.append('Live comet speed did not apply')
    if bridge.session.settings.accent!='#ac8aff':errors.append('Accent not applied')
    if bridge.session.settings.comet_style!='rainbow':errors.append('Rainbow style not applied')
    if bridge.session.settings.temperature_decimals!=0:errors.append('Precision selector not applied')
    if bridge.session.config_revision<1:errors.append('Missing live revision')
    bridge.stop()
    QTimer.singleShot(150,finish)
def finish():
    if bridge.running:errors.append('Session did not stop')
    else:
        window=engine.rootObjects()[0]
        if window.findChild(QObject,'stopButton').property('visible'):errors.append('Stop should hide after stopping')
        if window.findChild(QObject,'previewButton'):errors.append('Preview controls should not exist')
        if not window.findChild(QObject,'sendButton').property('visible'):errors.append('Start display missing after stopping')
    app.quit()
QTimer.singleShot(700,verify)
app.exec()
if bridge.session.thread:bridge.session.thread.join(2)
dispose_engine(engine)
assert not errors, errors
"""
        env=os.environ.copy()
        result=subprocess.run([sys.executable,'-c',script],env=env,text=True,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertNotIn('TypeError:',result.stderr)
        self.assertNotIn('ReferenceError:',result.stderr)
        self.assertNotIn('Cannot open',result.stderr)
        self.assertNotIn('failed to load',result.stderr.lower())
