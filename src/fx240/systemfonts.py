# SPDX-License-Identifier: GPL-3.0-or-later
"""Local Fontconfig catalog, not exported or stored. No user text enters a command."""
from pathlib import Path
import shutil
import time

FORMAT = '%{family[0]}\t%{style[0]}\t%{file}\t%{index}\n'
MAX_OUTPUT = 2 * 1024 * 1024


def fontconfig_output():
    from PySide6.QtCore import QProcess
    executable=shutil.which('fc-list')
    if not executable:
        raise ValueError('Fontconfig is unavailable; bundled Outfit and custom font files still work')
    data=bytearray()
    process=QProcess()
    process.setProgram(executable)
    process.setArguments(['--format='+FORMAT,':scalable=true'])
    process.setStandardErrorFile(QProcess.nullDevice())
    # Fixed executable lookup/options; no family, path, or user text enters argv.
    deadline=time.monotonic()+3
    process.start()
    try:
        if not process.waitForStarted(1000):raise ValueError('System font discovery failed')
        while True:
            data.extend(bytes(process.read(MAX_OUTPUT-len(data)+1)))
            if len(data)>MAX_OUTPUT:raise ValueError('System font catalog exceeds the size limit')
            if process.state()==QProcess.NotRunning and not process.bytesAvailable():break
            remaining=deadline-time.monotonic()
            if remaining<=0:raise ValueError('System font discovery timed out')
            process.waitForReadyRead(min(100,max(1,int(remaining*1000))))
        if process.exitStatus()!=QProcess.NormalExit or process.exitCode()!=0:
            raise ValueError('System font discovery failed')
    finally:
        if process.state()!=QProcess.NotRunning:
            process.kill();process.waitForFinished(1000)
    return bytes(data)


def catalog():
    try:
        text=fontconfig_output().decode('utf-8',errors='replace')
    except OSError as error:
        raise ValueError('System font discovery failed') from error
    result={}
    for line in text.splitlines():
        values=line.split('\t')
        if len(values)!=4:continue
        family,style,path,index=values
        # Collections/named instances need a separate face-index implementation.
        if index!='0' or not family or len(family)>128 or len(style)>128:continue
        if any(ord(c)<32 for c in family+style+path):continue
        source=Path(path)
        if not source.is_absolute() or source.suffix.lower() not in ('.ttf','.otf'):continue
        label=family+(' · '+style if style else '')
        try:resolved=str(source.resolve())
        except (OSError,ValueError):continue
        result.setdefault(label,resolved)
        if len(result)>4096:raise ValueError('System font catalog exceeds the entry limit')
    return [(label,result[label]) for label in sorted(result,key=str.casefold)]
