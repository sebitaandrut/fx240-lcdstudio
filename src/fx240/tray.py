"""System tray integration; hiding a window never changes the LCD session."""
from PySide6.QtCore import QObject,QTimer
from PySide6.QtGui import QWindow,QGuiApplication
from PySide6.QtWidgets import QSystemTrayIcon,QMenu

from .branding import APP_NAME, application_icon as tray_icon


class TrayController(QObject):
    def __init__(self, window, bridge, tray_factory=QSystemTrayIcon):
        super().__init__(bridge)
        self.window = window
        self.bridge = bridge
        self.tray_factory = tray_factory
        self.available = False
        self.hidden = False
        self.pending_startup = False
        icon = tray_icon()
        self.tray = tray_factory(icon,self)
        QGuiApplication.styleHints().colorSchemeChanged.connect(self.update_icon)
        self.tray.setToolTip(APP_NAME)
        self.menu = QMenu()
        self.show_action=self.menu.addAction('Show studio',self.restore)
        self.menu.addSeparator()
        self.quit_action=self.menu.addAction('Quit',self.quit)
        self.update_language()
        bridge.languageChanged.connect(self.update_language)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.activate)
        self.window.visibilityChanged.connect(self.visibility_changed)
        bridge._tray = self
        self.check_availability()
        self.timer = QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.check_availability)
        self.timer.start()

    def update_icon(self, scheme):
        icon = tray_icon(scheme)
        self.tray.setIcon(icon)
        QGuiApplication.setWindowIcon(icon)

    def update_language(self):
        self.show_action.setText(self.bridge.translate('Show studio',self.bridge.language))
        self.quit_action.setText(self.bridge.translate('Quit',self.bridge.language))

    def check_availability(self):
        available = self.tray_factory.isSystemTrayAvailable()
        if available == self.available:
            return
        self.available = available
        if available:
            self.tray.show()
            if self.pending_startup:self.minimize()
        else:
            self.tray.hide()
            if self.hidden:
                self.restore()
        self.bridge.changed.emit()

    def start_minimized(self):
        self.pending_startup = True
        self.check_availability()
        if self.available:self.minimize()
        else:self.window.showMinimized()

    def minimize(self):
        # Recheck before hiding: never make the only window inaccessible.
        self.check_availability()
        if self.available:
            self.hidden = True
            self.window.hide()

    def visibility_changed(self, visibility):
        if visibility == QWindow.Visibility.Minimized:
            self.minimize()
        elif visibility == QWindow.Visibility.Windowed:
            self.pending_startup = False

    def restore(self):
        self.pending_startup = False
        self.hidden = False
        self.window.showNormal()
        self.window.requestActivate()

    def activate(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,QSystemTrayIcon.ActivationReason.DoubleClick):
            self.restore()

    def quit(self):
        self.bridge.requestClose()

    def dispose(self):
        self.timer.stop()
        self.tray.hide()
        self.menu.deleteLater()
