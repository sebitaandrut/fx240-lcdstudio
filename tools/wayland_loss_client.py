# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic client for reproduce_wayland_loss.py; never opens a real HID device."""
import os,json
from wayland_trial_files import open_trial_file, private_run_directory
from fx240.session import Settings,Session
from fx240.telemetry import Metric
from fx240.media import encode
from fx240.protocol import build_reports
from fx240.idle import render_idle
root=private_run_directory(os.environ['FX240_TRIAL_ROOT'])
def record(event):
    with open_trial_file(root/'client-events.jsonl','a') as stream:stream.write(json.dumps(event)+'\n')
idle=build_reports(encode(render_idle(),65,180))
class Device:
    def __enter__(self):return self
    def send(self,reports,delay):record({'event':'send','standby':reports==idle});return 0,[]
    def __exit__(self,*args):record({'event':'closed'})
class Bus:
    def connect(self,*args):return False
    def disconnect(self,*args):return True
class Manager:
    def setTimeout(self,*args):pass
    def isValid(self):return False
from fx240.guard import StandbyGuard
from fx240.lifecycle import LifecycleTrace
trace=LifecycleTrace(root/'lifecycle.jsonl')
trace.emit('session-start')
guard=StandbyGuard(trace=trace,transport_factory=lambda path:Device()).start() if os.environ.get('FX240_USE_GUARD')=='1' else None
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from fx240.gui import create_engine,dispose_engine
from fx240.shutdown import ShutdownMonitor
app=QApplication([]);app.setQuitOnLastWindowClosed(False)
if app.platformName()!='wayland':raise RuntimeError('Owned trial requires the Wayland platform')
def factory(settings,**kwargs):return Session(settings,transport_factory=lambda path:Device(),**kwargs)
engine,bridge=create_engine(app,Settings(device='/dev/fake'),session_factory=factory,standby_guard=guard,provider=lambda:[Metric('ct','CPU synthetic',45,'C','synthetic')])
monitor=ShutdownMonitor(app,bridge,bus=Bus(),manager=Manager(),install_signals=True,trace=trace)
app.aboutToQuit.connect(lambda:record({'event':'about-to-quit'}))
bridge.start({},True)
def ready():
    if bridge.session.frames>1:
        with open_trial_file(root/'ready','x') as stream:stream.write('ready')
        timer.stop()
timer=QTimer();timer.setInterval(30);timer.timeout.connect(ready);timer.start()
QTimer.singleShot(20000,app.quit)
try:app.exec()
finally:
    record({'event':'finally'})
    monitor.finish();monitor.dispose();dispose_engine(engine)
    if guard:guard.close()
