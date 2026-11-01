"""Shared application identity and original LCD icon."""
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication,QIcon

APP_NAME = 'FX240 LCD STUDIO'


def application_icon(scheme=None):
    """Use desktop appearance, since application and panel themes can differ."""
    if scheme is None:
        scheme = QGuiApplication.styleHints().colorScheme()
    variant = 'dark' if scheme == Qt.ColorScheme.Dark else 'light' if scheme == Qt.ColorScheme.Light else 'fallback'
    return QIcon(str(Path(__file__).parent/f'assets/branding/tray-lcd-{variant}.svg'))
