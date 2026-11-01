# SPDX-License-Identifier: GPL-3.0-or-later
"""logind suspend coordination using a delay inhibitor and PrepareForSleep."""
import os
from PySide6.QtCore import QObject, Slot, QTimer, SLOT
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusUnixFileDescriptor


class SleepMonitor(QObject):
    def __init__(self, bridge):
        super().__init__(bridge)
        self.bridge = bridge
        self.fd = None
        self.waiting = False
        self.bus = QDBusConnection.systemBus()
        self.manager = QDBusInterface('org.freedesktop.login1','/org/freedesktop/login1',
                                     'org.freedesktop.login1.Manager',self.bus)
        self.manager.setTimeout(1500)
        self.available = self.bus.connect('org.freedesktop.login1','/org/freedesktop/login1',
            'org.freedesktop.login1.Manager','PrepareForSleep',self,SLOT('prepare(bool)'))
        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self.check)
        self.acquire()

    def acquire(self):
        if not self.available or not self.manager.isValid():
            self.bridge._sleep_status = 'Suspend integration unavailable; standby before sleep is not guaranteed'
            self.bridge.changed.emit()
            return
        reply = self.manager.call('Inhibit','sleep','FX240 Linux','Send LCD standby frame','delay')
        args = reply.arguments()
        if args and isinstance(args[0],QDBusUnixFileDescriptor) and args[0].isValid():
            self.fd = os.dup(args[0].fileDescriptor())
            self.bridge._sleep_status = 'Suspend standby: logind delay inhibitor active'
            self.bridge.changed.emit()
        else:
            self.bridge._sleep_status = 'Suspend delay inhibitor unavailable; standby before sleep is best effort'
            self.bridge.changed.emit()

    def release(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    @Slot(bool)
    def prepare(self, sleeping):
        if self.bridge.session:
            self.bridge.session.suspend(sleeping)
        if sleeping:
            self.waiting = True
            self.timer.start()
            self.check()
        else:
            self.waiting = False
            self.timer.stop()
            self.release()
            self.acquire()

    def check(self):
        if not self.bridge.session or self.bridge.session.output_released.is_set():
            self.release()
            self.timer.stop()
