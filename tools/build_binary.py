"""Build a local Linux executable bundle. A build is not cross-distro validation."""
import argparse
import importlib.metadata
import json
import platform
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--onedir',action='store_true',help='Build a directory bundle instead of one file')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    env=os.environ.copy()
    env['PYINSTALLER_CONFIG_DIR']=str(root/'build/pyinstaller-cache')
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean',
             '--onedir' if args.onedir else '--onefile','--name','fx240-lcd-studio',
             '--distpath',str(root/'dist'),'--workpath',str(root/'build/pyinstaller'),
             '--specpath',str(root/'build'),'--paths',str(root/'src'),
             '--add-data',str(root/'src/fx240/qml')+':fx240/qml',
             '--add-data',str(root/'src/fx240/assets')+':fx240/assets',
             str(root/'packaging/entrypoint.py')]
    subprocess.run(command,cwd=root,env=env,check=True)
    names=('Pillow','PySide6-Essentials','shiboken6','PyInstaller','pyinstaller-hooks-contrib','altgraph','packaging','setuptools')
    manifest={'python':platform.python_version(),'platform':platform.platform(),
              'architecture':platform.machine(),'format':'onedir' if args.onedir else 'onefile',
              'dependencies':{name:importlib.metadata.version(name) for name in names}}
    (root/'build/build-environment.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':main()
