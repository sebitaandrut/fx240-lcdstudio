# SPDX-License-Identifier: GPL-3.0-or-later
"""Reproduce compositor loss on an owned virtual KWin with fake USB, never the desktop.

Optional development dependencies: kwin_wayland and dbus-run-session.
Private logs can contain native library/environment paths; publish only reviewed result.json.
Each invocation keeps its files in a new private subdirectory of --output-dir.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from wayland_trial_files import new_run_directory, open_trial_file, private_run_directory, read_trial_file


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--guard',action='store_true',help='Enable independent standby fallback')
    args=parser.parse_args()
    if not all(shutil.which(name) for name in ('kwin_wayland','dbus-run-session')):
        parser.error('This optional instrument requires kwin_wayland and dbus-run-session')
    if os.environ.get('FX240_OWNED_TEST_BUS')!='1':
        # Always create a private bus rather than claiming any desktop's KWin service.
        root=new_run_directory(args.output_dir,args.guard)
        print(f'Private run directory: {root.name}',file=sys.stderr)
        env={**os.environ,'FX240_OWNED_TEST_BUS':'1','FX240_TRIAL_ROOT':str(root)}
        with open_trial_file(root/'private-bus.log','x') as log:
            result=subprocess.run(['dbus-run-session','--',sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]],
                                  env=env,stderr=log)
        return result.returncode
    root=private_run_directory(os.environ['FX240_TRIAL_ROOT'])
    repository=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='fx240-wayland-runtime-') as runtime:
        env={**os.environ,'XDG_RUNTIME_DIR':runtime,'XDG_CONFIG_HOME':runtime+'/config','XDG_STATE_HOME':runtime+'/state',
             'QT_QPA_PLATFORM':'offscreen','LIBGL_ALWAYS_SOFTWARE':'1','QT_QUICK_BACKEND':'software',
             'PYTHONPATH':str(repository/'src')}
        env.pop('DISPLAY',None);env.pop('WAYLAND_DISPLAY',None);env.pop('XAUTHORITY',None)
        compositor=client=None
        try:
            with open_trial_file(root/'compositor.log','x') as log:
                compositor=subprocess.Popen(['kwin_wayland','--virtual','--socket','fx240-isolated','--width','1000','--height','700','--no-lockscreen','--no-global-shortcuts'],env=env,stdout=log,stderr=subprocess.STDOUT)
            socket=Path(runtime)/'fx240-isolated';deadline=time.monotonic()+12
            while not socket.exists() and compositor.poll() is None and time.monotonic()<deadline:time.sleep(.05)
            if not socket.exists():raise RuntimeError('Owned virtual compositor did not become ready; inspect private logs')
            client_env={**env,'QT_QPA_PLATFORM':'wayland','WAYLAND_DISPLAY':'fx240-isolated','FX240_TRIAL_ROOT':str(root),'FX240_USE_GUARD':'1' if args.guard else '0'}
            with open_trial_file(root/'client.log','x') as log:
                client=subprocess.Popen([sys.executable,str(repository/'tools/wayland_loss_client.py')],env=client_env,stdout=log,stderr=subprocess.STDOUT)
            deadline=time.monotonic()+10
            marker=root/'ready'
            while read_trial_file(marker,missing_ok=True)!='ready' and client.poll() is None and time.monotonic()<deadline:time.sleep(.05)
            if read_trial_file(marker,missing_ok=True)!='ready':raise RuntimeError('Synthetic Wayland client did not become ready; inspect private logs')
            compositor.terminate();compositor.wait(timeout=8)
            timed_out=False
            try:code=client.wait(timeout=5)
            except subprocess.TimeoutExpired:
                timed_out=True;client.terminate();code=client.wait(timeout=5)
            trace=''
            if args.guard:
                deadline=time.monotonic()+2
                while time.monotonic()<deadline:
                    trace=read_trial_file(root/'lifecycle.jsonl',missing_ok=True)
                    if 'guard-standby-sent' in trace:break
                    time.sleep(.02)
            events=[json.loads(line) for line in read_trial_file(root/'client-events.jsonl').splitlines()]
            result={'isolated_wayland_test':True,'real_usb':False,'independent_standby_fallback':args.guard,
                    'compositor_was_owned_test_instance':True,'client_exit_code':code,
                    'client_timed_out_after_display_loss':timed_out,
                    'live_sends':sum(e.get('event')=='send' and not e.get('standby') for e in events),
                    'standby_sends':sum(e.get('event')=='send' and e.get('standby') for e in events),
                    'about_to_quit_observed':any(e['event']=='about-to-quit' for e in events),
                    'python_finally_observed':any(e['event']=='finally' for e in events),
                    'guard_standby_confirmed':'guard-standby-sent' in trace}
            with open_trial_file(root/'result.json','x') as stream:
                stream.write(json.dumps(result,indent=2)+'\n')
            print(json.dumps(result),flush=True)
            return 0
        finally:
            for process in (client,compositor):
                if process is not None and process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=3)
                    except subprocess.TimeoutExpired:process.kill();process.wait()


if __name__=='__main__':raise SystemExit(main())
