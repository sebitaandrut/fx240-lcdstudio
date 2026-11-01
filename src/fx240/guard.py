# SPDX-License-Identifier: GPL-3.0-or-later
"""Linux standby fallback, forked before Qt/threads and independent of the display server."""
import errno
import fcntl
import json
import math
import os
import select
import signal
import sys
import threading
import time
from .idle import render_idle
from .media import encode
from .protocol import build_reports
from .transport import Hidraw


def configuration_valid(data):
    return (isinstance(data,dict) and set(data)=={'device','quality','rotation','delay'}
            and isinstance(data['device'],str) and data['device'].startswith('/dev/')
            and len(data['device'])<=512 and not any(ord(c)<32 for c in data['device'])
            and type(data['quality']) is int and 1<=data['quality']<=95
            and type(data['rotation']) is int and data['rotation'] in (0,90,180,270)
            and type(data['delay']) in (int,float) and math.isfinite(data['delay']) and 0<=data['delay']<=100)


def run_guard(reader,idle,transport_factory,trace,lock_timeout):
    armed=None;buffer=b'';deadline=None
    def note(event):
        if trace:trace.emit(event)
    def termination(number,frame):
        nonlocal deadline
        if deadline is None:deadline=time.monotonic()+3
    for number in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(number,termination)
    # Do not retain the GUI's terminal/journal pipes after an abrupt native exit.
    null=os.open(os.devnull,os.O_RDWR)
    for number in (0,1,2):os.dup2(null,number)
    if null>2:os.close(null)
    while True:
        if deadline is not None and time.monotonic()>=deadline:
            note('guard-term');return
        readable,_,_=select.select([reader],[],[],.25)
        if not readable:continue
        data=os.read(reader,4096)
        if not data:break
        buffer+=data
        if len(buffer)>8192:note('guard-invalid-input');return
        while b'\n' in buffer:
            line,buffer=buffer.split(b'\n',1)
            try:message=json.loads(line)
            except (ValueError,UnicodeError):note('guard-invalid-input');return
            if message is None:armed=None
            elif configuration_valid(message):armed=message
            else:note('guard-invalid-input');return
    note('guard-eof')
    if armed is None:return
    reports=build_reports(encode(idle,armed['quality'],armed['rotation']))
    until=time.monotonic()+lock_timeout
    while True:
        try:
            with transport_factory(armed['device']) as device:
                device.send(reports,armed['delay'])
            note('guard-standby-sent');return
        except OSError as error:
            if error.errno in (errno.EWOULDBLOCK,errno.EAGAIN) and time.monotonic()<until:
                time.sleep(.025);continue
            note('guard-lock-timeout' if error.errno in (errno.EWOULDBLOCK,errno.EAGAIN) else 'guard-standby-failed');return
        except Exception:
            note('guard-standby-failed');return


class StandbyGuard:
    def __init__(self,*,trace=None,transport_factory=Hidraw,lock_timeout=2):
        self.trace=trace;self.transport_factory=transport_factory;self.lock_timeout=lock_timeout
        self.writer=None;self.pid=None;self._armed=None;self._lock=threading.Lock()

    def note(self,event):
        if self.trace:self.trace.emit(event)

    def start(self):
        if self.pid is not None:raise RuntimeError('Standby fallback already started')
        if threading.active_count()!=1 or 'PySide6.QtGui' in sys.modules:
            raise RuntimeError('Standby fallback must start before Qt and worker threads')
        # Materialize artwork and the JPEG plugin while the frozen runtime still exists.
        # The child needs no font, plugin, or runtime asset after its GUI parent exits.
        idle=render_idle();encode(idle,65,180)
        reader,writer=os.pipe2(os.O_CLOEXEC|os.O_NONBLOCK)
        # Desktop launchers may leave stdin/stdout closed; reserve the control FDs.
        if reader<3:
            duplicate=fcntl.fcntl(reader,fcntl.F_DUPFD_CLOEXEC,3);os.close(reader);reader=duplicate
        if writer<3:
            duplicate=fcntl.fcntl(writer,fcntl.F_DUPFD_CLOEXEC,3);os.close(writer);writer=duplicate
        os.set_blocking(reader,True)
        try:pid=os.fork()
        except BaseException:
            os.close(reader);os.close(writer);raise
        if pid==0:
            os.close(writer)
            code=0
            try:run_guard(reader,idle,self.transport_factory,self.trace,self.lock_timeout)
            except BaseException:
                self.note("guard-standby-failed");code=1
            finally:os._exit(code)
        os.close(reader);self.writer=writer;self.pid=pid
        self.note('guard-started');return self

    def _send(self,data):
        if self.writer is None:return
        try:
            encoded=json.dumps(data,separators=(',',':')).encode()+b'\n'
            if len(encoded)>4096:raise ValueError('Standby control packet too large')
            if os.write(self.writer,encoded)!=len(encoded):raise OSError('Incomplete control packet')
        except (OSError,ValueError):
            os.close(self.writer);self.writer=None;self.note('guard-control-failed')

    def arm(self,settings):
        data={'device':settings.device,'quality':settings.quality,'rotation':settings.rotation,'delay':settings.delay_ms}
        if not configuration_valid(data):return
        with self._lock:
            if data!=self._armed:
                self._armed=data;self._send(data);self.note('guard-armed')

    def disarm(self):
        with self._lock:
            if self._armed is not None:
                self._armed=None;self._send(None);self.note('guard-disarmed')

    def close(self):
        with self._lock:
            if self.writer is not None:os.close(self.writer);self.writer=None
        if self.pid is None:return
        deadline=time.monotonic()+.2
        while time.monotonic()<deadline:
            try:done,_=os.waitpid(self.pid,os.WNOHANG)
            except ChildProcessError:done=self.pid
            if done:self.pid=None;break
            time.sleep(.005)
