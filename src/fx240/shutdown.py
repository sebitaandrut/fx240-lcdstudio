# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded shutdown cleanup for logind, desktop session management, and Unix signals."""
import os
import signal
from PySide6.QtCore import QObject,QTimer,Qt,SLOT,Slot
from PySide6.QtGui import QSessionManager
from PySide6.QtDBus import QDBusConnection,QDBusInterface,QDBusUnixFileDescriptor


class ShutdownMonitor(QObject):
    def __init__(self,app,bridge,*,bus=None,manager=None,install_signals=True,join_timeout=2,trace=None):
        super().__init__(bridge)
        self.trace=trace
        self.app=app;self.bridge=bridge;self.join_timeout=join_timeout
        self.fd=None;self.preparing=False;self.finished=False;self.worker_drained=None
        self.termination_requested=False;self.previous_handlers={}
        self.bus=bus if bus is not None else QDBusConnection.systemBus()
        self.manager=manager if manager is not None else QDBusInterface(
            'org.freedesktop.login1','/org/freedesktop/login1','org.freedesktop.login1.Manager',self.bus)
        self.manager.setTimeout(1500)
        self.available=self.bus.connect('org.freedesktop.login1','/org/freedesktop/login1',
            'org.freedesktop.login1.Manager','PrepareForShutdown',self,SLOT('prepare(bool)'))
        app.aboutToQuit.connect(self.about_to_quit)
        app.commitDataRequest.connect(self.commit,Qt.ConnectionType.DirectConnection)
        app.saveStateRequest.connect(self.save_state,Qt.ConnectionType.DirectConnection)
        self.timer=QTimer(self);self.timer.setInterval(50);self.timer.timeout.connect(self.check)
        # A Python callback also lets CPython dispatch signals while Qt owns the loop.
        self.timer.start()
        if install_signals:
            for number in (signal.SIGTERM,signal.SIGINT):
                self.previous_handlers[number]=signal.getsignal(number)
                signal.signal(number,self.handle_signal)
        self.acquire()

    def note(self,event):
        if self.trace:self.trace.emit(event)

    def about_to_quit(self):
        self.note("qt-about-to-quit")
        self.finish()

    def status(self,text):
        self.bridge._shutdown_status=text
        self.bridge.changed.emit()

    def acquire(self):
        if not self.available or not self.manager.isValid():
            self.status('Shutdown standby: logind unavailable; desktop/signal cleanup is best effort')
            return
        reply=self.manager.call('Inhibit','shutdown','FX240 LCD STUDIO','Send LCD standby frame','delay')
        args=reply.arguments()
        if args and isinstance(args[0],QDBusUnixFileDescriptor) and args[0].isValid():
            self.fd=os.dup(args[0].fileDescriptor())
            self.status('Shutdown standby: logind delay inhibitor active')
        else:
            self.status('Shutdown standby: delay inhibitor unavailable; cleanup is best effort')

    def release(self):
        if self.fd is not None:
            os.close(self.fd);self.fd=None

    @Slot(bool)
    def prepare(self,active):
        self.note("logind-shutdown" if active else "logind-shutdown-canceled")
        self.preparing=active
        session=self.bridge.session
        if session:session.suspend(active,reason='shutdown')
        if active:
            self.bridge.flushPreferences()
            self.check()
        else:
            self.release()
            if not self.finished:self.acquire()

    def handle_signal(self,number,frame):
        # Never do USB, file, or Qt work inside the signal handler.
        self.termination_requested=number

    def check(self):
        if self.termination_requested:
            self.note("sigterm-dispatched" if self.termination_requested==signal.SIGTERM else "sigint-dispatched")
            self.termination_requested=False
            self.finish()
            self.app.quit()
            return
        if self.preparing and (not self.bridge.session or self.bridge.session.output_released.is_set()):
            self.release()

    def save_state(self,manager):
        # The opt-in desktop entry, not session restoration, owns next-login startup.
        self.note("qt-save-state")
        manager.setRestartHint(QSessionManager.RestartHint.RestartNever)
        self.bridge.flushPreferences()

    def commit(self,manager):
        self.note("qt-commit")
        self.save_state(manager)
        self.finish()

    def finish(self):
        if self.finished:return self.worker_drained
        self.finished=True
        self.note("cleanup-start")
        try:
            self.bridge.stop()
            session=self.bridge.session
            if session and session.thread:
                session.thread.join(timeout=self.join_timeout)
                self.worker_drained=not session.thread.is_alive()
            else:self.worker_drained=True
            self.bridge.flushPreferences()
            self.note("worker-drained" if self.worker_drained else "worker-timeout")
        finally:
            self.release()
        return self.worker_drained

    def dispose(self):
        self.timer.stop();self.release()
        self.bus.disconnect('org.freedesktop.login1','/org/freedesktop/login1',
            'org.freedesktop.login1.Manager','PrepareForShutdown',self,SLOT('prepare(bool)'))
        for number,handler in self.previous_handlers.items():signal.signal(number,handler)
        self.previous_handlers.clear()
        self.app.aboutToQuit.disconnect(self.about_to_quit)
        self.app.commitDataRequest.disconnect(self.commit)
        self.app.saveStateRequest.disconnect(self.save_state)
