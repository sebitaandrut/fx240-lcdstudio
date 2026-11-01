"""Opt-in per-user graphical-session startup; never installs a system service."""
import os
from pathlib import Path
import sys
import tempfile

MARKER = 'X-FX240-LCD-STUDIO-Managed=true'


def desktop_string(value):
    if any(ord(c)<32 for c in value):
        raise ValueError('Startup paths must not contain control characters')
    return value.replace('\\', '\\\\')


def exec_argument(value):
    # Exec quoting is interpreted after desktop-string escaping.
    quoted=''.join('\\'+c if c in '\\"`$' else c for c in value.replace('%','%%'))
    return desktop_string('"'+quoted+'"')


class Autostart:
    def __init__(self, config_home=None, command=None):
        home=Path(config_home or os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')
        if not home.is_absolute():raise ValueError('Configuration directory must be absolute')
        self.path=home/'autostart/org.fx240lcdstudio.desktop'
        # Preserve the virtual environment path rather than resolving its symlink.
        self.command=tuple(command or ((sys.executable,'gui','--start-minimized') if getattr(sys,'frozen',False)
                           else (sys.executable,'-m','fx240','gui','--start-minimized')))
        if not Path(self.command[0]).is_absolute() or '=' in self.command[0]:
            raise ValueError('Startup executable must be an absolute path without =')
        for arg in self.command:desktop_string(arg)

    def _read(self):
        if self.path.is_symlink():raise OSError('Startup entry is a symbolic link; it was not modified')
        return self.path.read_text() if self.path.exists() else ''

    @property
    def enabled(self):
        content=self._read()
        return MARKER in content.splitlines() and 'Hidden=true' not in content.splitlines()

    def set_enabled(self, enabled):
        content=self._read()
        if content and MARKER not in content.splitlines():
            raise OSError('An unmanaged startup entry already exists; it was not modified')
        if not enabled:
            if content:self.path.unlink()
            return
        if not Path(self.command[0]).is_file():raise OSError('Startup executable no longer exists')
        text='\n'.join(('[Desktop Entry]','Type=Application','Name=FX240 LCD STUDIO',
                        'Comment=Start the LCD studio minimized after graphical login',
                        'Exec='+' '.join(exec_argument(arg) for arg in self.command),
                        'TryExec='+desktop_string(self.command[0]),'Terminal=false',MARKER,''))
        self.path.parent.mkdir(parents=True,exist_ok=True)
        name=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',dir=self.path.parent,delete=False) as stream:
                name=stream.name
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name,self.path)
        finally:
            if name and Path(name).exists():Path(name).unlink()
