# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

PRELUDE=r'''
import os,time,json,signal
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QT_QUICK_BACKEND']='software'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QSessionManager
from PySide6.QtDBus import QDBusUnixFileDescriptor
from fx240.gui import create_engine,dispose_engine
from fx240.shutdown import ShutdownMonitor
from fx240.session import Session,Settings
from fx240.telemetry import Metric
from fx240.media import encode
from fx240.protocol import build_reports
from fx240.idle import render_idle
class Bus:
    def __init__(self,available=True):self.available=available;self.signals=[]
    def connect(self,*args):self.signals.append(args[3]);return self.available
    def disconnect(self,*args):return True
class Manager:
    def __init__(self):
        self.r,self.w=os.pipe()
        self.descriptor=QDBusUnixFileDescriptor(self.r)
        self.calls=[]
    def setTimeout(self,value):pass
    def isValid(self):return True
    def call(self,*args):
        self.calls.append(args)
        outer=self
        class Reply:
            def arguments(self):return [outer.descriptor]
        return Reply()
    def close(self):os.close(self.r);os.close(self.w)
class Device:
    def __init__(self):self.last=None;self.closes=0;self.sends=0
    def __enter__(self):return self
    def send(self,reports,delay):self.last=reports;self.sends+=1;return 0,[]
    def __exit__(self,*args):self.closes+=1
app=QApplication([]);app.setQuitOnLastWindowClosed(False)
device=Device()
def factory(settings,**kwargs):return Session(settings,transport_factory=lambda path:device,**kwargs)
engine,bridge=create_engine(app,Settings(device='/dev/fake'),provider=lambda:[Metric('ct','CPU synthetic',45,'C','synthetic')],session_factory=factory)
manager=Manager();bus=Bus()
monitor=ShutdownMonitor(app,bridge,bus=bus,manager=manager,install_signals=False)
bridge.start({},True)
idle=build_reports(encode(render_idle(),65,180))
def until(predicate):
    deadline=time.monotonic()+3
    while not predicate() and time.monotonic()<deadline:
        app.processEvents();time.sleep(.005)
    assert predicate()
until(lambda:bridge.session.frames>=1)
'''


@unittest.skipUnless(importlib.util.find_spec('PySide6'),'Optional Qt dependency missing')
class ShutdownTests(unittest.TestCase):
    def run_script(self,body):
        result=subprocess.run([sys.executable,'-c',PRELUDE+body],capture_output=True,text=True,timeout=12)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_logind_keeps_delay_until_standby_then_cancellation_resumes(self):
        self.run_script(r'''
assert bus.signals==['PrepareForShutdown']
assert manager.calls[0][1]=='shutdown' and manager.calls[0][-1]=='delay'
fd=monitor.fd
os.fstat(fd)
monitor.prepare(True)
until(lambda:monitor.fd is None)
assert device.last==idle and device.closes==1
try:os.fstat(fd);raise AssertionError('Inhibitor descriptor still open')
except OSError:pass
assert bridge.session.output_requested
before=bridge.session.frames
monitor.prepare(False)
until(lambda:bridge.session.frames>before and bridge.session.send)
assert monitor.fd is not None
# A canceled shutdown must not clear a simultaneous suspend pause.
bridge.session.suspend(True)
until(lambda:bridge.session.output_released.is_set())
monitor.prepare(True);monitor.prepare(False)
assert bridge.session.suspended.is_set()
bridge.session.suspend(False)
until(lambda:bridge.session.send)
# A manually paused LCD stays paused after cancellation.
bridge.stopOutput()
until(lambda:not bridge.session.send)
monitor.prepare(True)
until(lambda:monitor.fd is None)
monitor.prepare(False)
assert not bridge.session.output_requested
assert monitor.finish() and not bridge.session.thread.is_alive()
monitor.dispose();manager.close();dispose_engine(engine)
''')

    def test_session_commit_and_about_to_quit_finish_only_once(self):
        self.run_script(r'''
class SessionManager:
    def setRestartHint(self,hint):self.hint=hint
sm=SessionManager()
monitor.save_state(sm)
assert not bridge.session.stop_event.is_set() # checkpoint alone is not shutdown
monitor.commit(sm)
assert sm.hint==QSessionManager.RestartHint.RestartNever
assert monitor.worker_drained and device.last==idle and device.closes==1
app.aboutToQuit.emit()
assert device.closes==1 and monitor.finish()
monitor.dispose();manager.close();dispose_engine(engine)
''')

    def test_about_to_quit_alone_drains_active_output(self):
        self.run_script(r'''
QTimer.singleShot(20,app.quit)
app.exec()
assert monitor.worker_drained and not bridge.session.thread.is_alive()
assert device.last==idle and device.closes==1
monitor.dispose();manager.close();dispose_engine(engine)
''')

    def test_drain_is_bounded_and_unavailable_logind_has_fallback(self):
        self.run_script(r'''
from unittest.mock import Mock
assert monitor.finish()
monitor.dispose();manager.close()
bridge.session=Mock();bridge.session.thread.is_alive.return_value=True
bridge._running=True
fallback=ShutdownMonitor(app,bridge,bus=Bus(False),manager=Manager(),install_signals=False,join_timeout=.02)
assert fallback.fd is None and 'best effort' in bridge.shutdownStatus
assert not fallback.finish()
bridge.session.thread.join.assert_called_once_with(timeout=.02)
fallback.finish()
bridge.session.thread.join.assert_called_once()
fallback.dispose();fallback.manager.close();dispose_engine(engine)
''')

    def test_real_sigterm_drains_worker_and_sends_final_standby(self):
        script=PRELUDE+r'''
from pathlib import Path
monitor.dispose()
previous=signal.getsignal(signal.SIGTERM)
monitor=ShutdownMonitor(app,bridge,bus=bus,manager=manager)
Path(os.environ['FX240_TEST_READY']).write_text('ready')
QTimer.singleShot(6000,app.quit)
app.exec()
assert monitor.worker_drained and not bridge.session.thread.is_alive()
assert device.last==idle and device.closes==1
monitor.dispose()
assert signal.getsignal(signal.SIGTERM)==previous
manager.close();dispose_engine(engine)
print('standby-drained',flush=True)
'''
        with tempfile.TemporaryDirectory() as home:
            ready=Path(home)/'ready'
            process=subprocess.Popen([sys.executable,'-c',script],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                     text=True,env={**os.environ,'FX240_TEST_READY':str(ready)})
            try:
                deadline=time.monotonic()+5
                while not ready.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.01)
                self.assertTrue(ready.exists(),'Child did not initialize')
                process.send_signal(signal.SIGTERM)
                out,err=process.communicate(timeout=5)
                self.assertEqual(process.returncode,0,out+err)
                self.assertIn('standby-drained',out)
            finally:
                if process.poll() is None:process.kill();process.communicate()
