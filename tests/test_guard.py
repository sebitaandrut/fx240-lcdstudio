# SPDX-License-Identifier: GPL-3.0-or-later
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from fx240.guard import StandbyGuard,configuration_valid
from fx240.lifecycle import LifecycleTrace

SCRIPT=r'''
import os,json,time,fcntl,signal
from pathlib import Path
from fx240.guard import StandbyGuard
from fx240.lifecycle import LifecycleTrace
from fx240.session import Settings,Session
from fx240.telemetry import Metric
from fx240.media import encode
from fx240.protocol import build_reports
from fx240.idle import render_idle
root=Path(os.environ['FX240_GUARD_TEST_ROOT'])
mode=os.environ['FX240_GUARD_TEST_MODE']
idle=build_reports(encode(render_idle(),65,180))
def record(event):
    fd=os.open(root/'transport.jsonl',os.O_WRONLY|os.O_APPEND|os.O_CREAT,0o600)
    try:os.write(fd,json.dumps(event).encode()+b'\n')
    finally:os.close(fd)
class Device:
    def __enter__(self):
        self.file=(root/'lock').open('ab')
        try:fcntl.flock(self.file,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BaseException:self.file.close();raise
        return self
    def send(self,reports,delay):
        if mode=='write-error':raise OSError('synthetic write failure')
        record({'event':'send','standby':reports==idle});return 0,[]
    def __exit__(self,*args):self.file.close();record({'event':'closed'})
trace=LifecycleTrace(root/'trace.jsonl');trace.emit('session-start')
if os.environ.get('FX240_GUARD_CLOSE_STDIO')=='1':
    os.close(0);os.close(1)
guard=StandbyGuard(trace=trace,transport_factory=lambda path:Device(),lock_timeout=.15).start()
config=Settings(device='/dev/fake')
if mode=='lock-held':
    guard.arm(config)
    os._exit(23)
session=Session(config,send=mode!='preview',standby_guard=guard,transport_factory=lambda path:Device(),
                provider=lambda:[Metric('ct','CPU synthetic',45,'C','synthetic')])
session.start()
deadline=time.monotonic()+3
while session.frames<2 and time.monotonic()<deadline:time.sleep(.005)
assert session.frames>=2
if mode=='paused':
    session.set_output(False)
    assert session.output_released.wait(2)
if mode=='scope-term':
    signal.signal(signal.SIGTERM,lambda number,frame:os._exit(23))
    (root/'ready').write_text('ready')
    while True:time.sleep(.1)
if mode in ('abrupt','paused','preview','write-error'):os._exit(23)
session.stop();session.thread.join(2)
assert not session.thread.is_alive()
guard.close()
'''


@unittest.skipUnless(hasattr(os,'fork'),'Linux/Unix fork required')
class GuardTests(unittest.TestCase):
    def trial(self,mode,closed_stdio=False):
        with tempfile.TemporaryDirectory() as home:
            result=subprocess.run([sys.executable,'-c',SCRIPT],capture_output=True,text=True,timeout=8,
                                  env={**os.environ,'FX240_GUARD_TEST_ROOT':home,'FX240_GUARD_TEST_MODE':mode,'FX240_GUARD_CLOSE_STDIO':'1' if closed_stdio else '0'})
            self.assertEqual(result.returncode,0 if mode=='graceful' else 23,result.stdout+result.stderr)
            root=Path(home);deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                try:trace=[json.loads(line)['event'] for line in (root/'trace.jsonl').read_text().splitlines()]
                except FileNotFoundError:trace=[]
                if 'guard-eof' in trace and (mode!='abrupt' or 'guard-standby-sent' in trace):break
                time.sleep(.01)
            events=[json.loads(line) for line in (root/'transport.jsonl').read_text().splitlines()] if (root/'transport.jsonl').exists() else []
            return events,trace

    def test_abrupt_native_style_exit_gets_standby_from_independent_child(self):
        events,trace=self.trial('abrupt')
        sends=[e for e in events if e['event']=='send']
        self.assertTrue(sends[-1]['standby'])
        self.assertEqual(sum(e['standby'] for e in sends),1)
        self.assertIn('guard-standby-sent',trace)

    def test_closed_standard_descriptors_do_not_overwrite_the_control_pipe(self):
        events,trace=self.trial('abrupt',closed_stdio=True)
        self.assertIn('guard-standby-sent',trace)
        self.assertTrue([e for e in events if e['event']=='send'][-1]['standby'])

    def test_graceful_close_does_not_duplicate_the_worker_standby(self):
        events,trace=self.trial('graceful')
        self.assertEqual(sum(e.get('standby',False) for e in events),1)
        self.assertNotIn('guard-standby-sent',trace)
        self.assertIn('guard-disarmed',trace)

    def test_paused_or_preview_output_is_not_reopened_after_exit(self):
        for mode in ('paused','preview'):
            with self.subTest(mode=mode):
                events,trace=self.trial(mode)
                self.assertNotIn('guard-standby-sent',trace)
                self.assertEqual(sum(e.get('standby',False) for e in events),1 if mode=='paused' else 0)

    def test_known_write_failure_is_not_retried_by_fallback(self):
        events,trace=self.trial('write-error')
        self.assertNotIn('guard-standby-sent',trace)
        self.assertIn('guard-disarmed',trace)

    def test_process_group_sigterm_does_not_kill_fallback_before_parent_exit(self):
        import signal
        with tempfile.TemporaryDirectory() as home:
            root=Path(home)
            process=subprocess.Popen([sys.executable,'-c',SCRIPT],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True,
                                     env={**os.environ,'FX240_GUARD_TEST_ROOT':home,'FX240_GUARD_TEST_MODE':'scope-term'})
            try:
                deadline=time.monotonic()+3
                while not (root/'ready').exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.01)
                self.assertTrue((root/'ready').exists())
                os.killpg(process.pid,signal.SIGTERM) # Only this owned isolated test group.
                out,err=process.communicate(timeout=5)
                self.assertEqual(process.returncode,23,out+err)
                deadline=time.monotonic()+3
                while time.monotonic()<deadline:
                    trace=(root/'trace.jsonl').read_text()
                    if 'guard-standby-sent' in trace:break
                    time.sleep(.01)
                self.assertIn('guard-standby-sent',trace)
            finally:
                if process.poll() is None:process.kill();process.communicate()

    def test_start_is_rejected_after_qt_import(self):
        with patch.dict(sys.modules,{'PySide6.QtGui':object()}):
            with self.assertRaises(RuntimeError):StandbyGuard().start()

    def test_control_configuration_is_strict(self):
        config={'device':'/dev/fake','quality':65,'rotation':180,'delay':2}
        self.assertTrue(configuration_valid(config))
        for change in ({'device':'/tmp/file'},{'device':'/dev/bad\npath'},{'quality':True},{'rotation':45},{'delay':float('nan')},{'extra':True}):
            self.assertFalse(configuration_valid({**config,**change}))

    def test_existing_owner_lock_is_not_taken_over(self):
        import fcntl
        with tempfile.TemporaryDirectory() as home:
            root=Path(home)
            with (root/'lock').open('ab') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                result=subprocess.run([sys.executable,'-c',SCRIPT],capture_output=True,text=True,timeout=5,
                                      env={**os.environ,'FX240_GUARD_TEST_ROOT':home,'FX240_GUARD_TEST_MODE':'lock-held'})
                self.assertEqual(result.returncode,23,result.stdout+result.stderr)
                deadline=time.monotonic()+2
                while time.monotonic()<deadline:
                    trace=(root/'trace.jsonl').read_text()
                    if 'guard-lock-timeout' in trace:break
                    time.sleep(.01)
                self.assertIn('guard-lock-timeout',trace)
                self.assertFalse((root/'transport.jsonl').exists())


class LifecycleTraceTests(unittest.TestCase):
    def test_private_bounded_schema_has_no_free_form_fields(self):
        with tempfile.TemporaryDirectory() as home:
            trace=LifecycleTrace(Path(home)/'events.jsonl');trace.emit('session-start')
            self.assertEqual(trace.path.stat().st_mode & 0o777,0o600)
            row=json.loads(trace.path.read_text())
            self.assertEqual(set(row),{'event','seconds'})
            with self.assertRaises(ValueError):trace.emit('unapproved free form data')
            with self.assertRaises(TypeError):trace.emit('gui-start',path='not allowed')
            trace.path.write_bytes(b'x'*65536)
            trace.emit('gui-start');self.assertEqual(trace.path.stat().st_size,65536)

    def test_unwritable_or_symlink_log_does_not_break_cleanup(self):
        with tempfile.TemporaryDirectory() as home:
            target=Path(home)/'target';target.write_text('unchanged')
            link=Path(home)/'link';link.symlink_to(target)
            LifecycleTrace(link).emit('gui-start')
            self.assertEqual(target.read_text(),'unchanged')
            LifecycleTrace(target/'invalid').emit('gui-start')
