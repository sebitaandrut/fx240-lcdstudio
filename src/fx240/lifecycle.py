# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded private event codes only: no paths, identities, readings, or OS messages."""
import json
import os
from pathlib import Path
import stat
import time

EVENTS=frozenset('session-start gui-start gui-loop-returned guard-started guard-start-failed guard-armed guard-disarmed guard-control-failed guard-eof guard-term guard-standby-sent guard-standby-failed guard-lock-timeout guard-invalid-input qt-save-state qt-commit qt-about-to-quit logind-shutdown logind-shutdown-canceled sigterm-dispatched sigint-dispatched cleanup-start worker-drained worker-timeout'.split())


class LifecycleTrace:
    def __init__(self,path=None):
        base=Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')
        if not base.is_absolute():base=Path.home()/'.local/state'
        self.path=Path(path) if path is not None else base/'fx240-linux/shutdown.jsonl'
        self.started=time.monotonic()

    def emit(self,event):
        if event not in EVENTS:raise ValueError('Unknown lifecycle event')
        fd=None
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            fd=os.open(self.path,os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK,0o600)
            if not stat.S_ISREG(os.fstat(fd).st_mode):return
            os.fchmod(fd,0o600)
            if os.fstat(fd).st_size>=65536:return
            data=json.dumps({'event':event,'seconds':round(time.monotonic()-self.started,3)},separators=(',',':')).encode()+b'\n'
            os.write(fd,data)
        except OSError:
            pass # Diagnostics must never prevent display or cleanup.
        finally:
            if fd is not None:os.close(fd)
