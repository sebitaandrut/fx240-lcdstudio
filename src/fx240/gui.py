# SPDX-License-Identifier: GPL-3.0-or-later
"""Qt Quick desktop controller. The renderer and transport remain independent."""
from dataclasses import replace
from pathlib import Path
import queue
import sys
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer, QUrl, QSize, QCoreApplication, QEvent, QRectF
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QPainterPath
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtQuickControls2 import QQuickStyle
from .dashboard import default_metrics
from .focus import temperature
from .session import Session, Settings, find_devices
from .i18n import translate, runtime_text
from .branding import APP_NAME, application_icon


class FrameProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self.image = QImage(240,240,QImage.Format.Format_RGB888)
        self.image.fill('#080b0e')

    def update(self, image):
        rgb = image.convert('RGB')
        frame = QImage(rgb.tobytes(),rgb.width,rgb.height,rgb.width*3,QImage.Format.Format_RGB888).copy()
        self.image = QImage(rgb.width,rgb.height,QImage.Format.Format_ARGB32_Premultiplied)
        self.image.fill(0)
        painter = QPainter(self.image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addEllipse(QRectF(3,3,234,234))
        painter.setClipPath(clip)
        painter.drawImage(0,0,frame)
        painter.end()

    def requestImage(self, identifier, size, requested_size):
        size.setWidth(self.image.width())
        size.setHeight(self.image.height())
        return self.image.copy()


def diagnostic_rows(event):
    """Use the frame's own snapshot, never a second sensor query."""
    rows = []
    selected = default_metrics(event['metrics'])
    for group,unit,label in (('CPU','C','CPU temperature'),('CPU','MHz','CPU frequency'),
                             ('GPU','C','GPU temperature'),('GPU','MHz','GPU frequency')):
        metric = next((m for m in selected if m.label.startswith(group+' ') and m.unit == unit),None)
        if metric is None:
            rows.append({'label':label,'raw':'N/A','target':'N/A','source':'No compatible sensor in this sample'})
            continue
        raw = 'N/A' if metric.value is None else f'{metric.value:.3f} {metric.unit}'
        if metric.value is None:
            target = 'N/A'
        elif metric.unit == 'C':
            display_unit=event.get('temperature_unit','C')
            target = temperature(metric.value,event['temperature_decimals'],display_unit)+'°'+display_unit
        else:
            target = f'{metric.value/1000:.2f} GHz'
        rows.append({'label':metric.label,'raw':raw,'target':target,'source':metric.source})
    return rows


class Bridge(QObject):
    languageChanged = Signal()
    applicationChanged = Signal()
    changed = Signal()
    frameChanged = Signal()
    sensorsChanged = Signal()
    devicesChanged = Signal()

    def __init__(self, settings, provider=None, session_factory=Session, image_provider=None, preferences=None, application=None, autostart=None, start_minimized=False):
        super().__init__()
        self.settings = settings
        self.autostart = autostart
        self._start_minimized = start_minimized
        self._startup_error = ""
        self._autostart_enabled = False
        if autostart:
            try:self._autostart_enabled = autostart.enabled
            except (OSError, ValueError) as error:self._startup_error = str(error)
        self.preferences = preferences
        application = application or {}
        self._language = application.get('language','en')
        self._ui_theme = application.get('theme','dark')
        self._preference_notice = preferences.warning if preferences else ''
        issues=getattr(preferences,'issues',[])
        self._preference_issues=issues if isinstance(issues,list) else []
        detail=getattr(preferences,'load_error','')
        self._preference_detail=detail if isinstance(detail,str) else ''
        self._preference_kind='load' if self._preference_notice else ''
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(600)
        self.save_timer.timeout.connect(self.flushPreferences)
        self.provider = provider
        self.session_factory = session_factory
        self.images = image_provider if image_provider is not None else FrameProvider()
        self.session = None
        self._devices = find_devices()
        self._status = 'Ready — preview only'
        self._error = ''
        self._rows = []
        self._sample = 'No sample yet'
        self._statistics = 'No frames rendered'
        self._frame = 0
        self._sequence = -1
        self._running = False
        self._sending = False
        self._closing = False
        self._sleep_status = 'Suspend integration not initialized'
        self._tray = None
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.poll)
        self.timer.start()

    @Property(bool, constant=True)
    def startMinimized(self): return self._start_minimized
    @Property(bool, constant=True)
    def autostartSupported(self): return self.autostart is not None
    @Property(bool, notify=changed)
    def autostartEnabled(self): return self._autostart_enabled
    @Slot(bool)
    def setAutostart(self, enabled):
        if self.autostart is None:return
        try:
            self.autostart.set_enabled(enabled)
            self._autostart_enabled = self.autostart.enabled
            self._startup_error = ''
        except (OSError, ValueError) as error:
            self._startup_error = str(error)
        self.changed.emit()

    @Property(str, notify=languageChanged)
    def language(self): return self._language
    @Property(str, notify=applicationChanged)
    def uiTheme(self): return self._ui_theme
    @Property(str, constant=True)
    def initialTemperatureUnit(self): return self.settings.temperature_unit

    @Slot(str,str,result=str)
    def translate(self, text, language): return translate(text,language)

    @Slot(str)
    def setLanguage(self, language):
        if language in ('en','es') and language != self._language:
            self._language = language
            self.languageChanged.emit()
            self.changed.emit()
            self.sensorsChanged.emit()
            self.save_timer.start()

    @Slot(str)
    def setUiTheme(self, theme):
        if theme in ('dark','light') and theme != self._ui_theme:
            self._ui_theme = theme
            self.applicationChanged.emit()
            self.save_timer.start()

    @Slot()
    def flushPreferences(self):
        self.save_timer.stop()
        if self.preferences is None:
            return
        try:
            self.preferences.save(self.settings,self._language,self._ui_theme)
            self._preference_notice = ''
            self._preference_issues=[]
            self._preference_detail=''
            self._preference_kind=''
        except (OSError,ValueError,TypeError) as error:
            self._preference_notice = 'Preferences could not be saved'
            self._preference_kind='save'
            self._preference_detail=str(error)
        self.changed.emit()

    @Property(bool, notify=changed)
    def trayAvailable(self): return self._tray is not None and self._tray.available

    @Slot()
    def minimizeToTray(self):
        if self._tray:
            self._tray.minimize()

    @Property(bool, notify=changed)
    def running(self): return self._running
    @Property(bool, notify=changed)
    def sending(self): return self._sending
    @Property(str, notify=changed)
    def status(self): return runtime_text(self._status,self._language)
    @Property(str, notify=changed)
    def runtimeError(self):
        if self._startup_error:
            return self.translate('Login startup could not be updated:',self._language)+' '+self._startup_error
        return runtime_text(self._error,self._language)
    @Property(str, notify=changed)
    def preferenceNotice(self): return runtime_text(self._preference_notice,self._language)
    @Property(bool, notify=changed)
    def preferenceCanRetry(self): return self._preference_kind=='save'
    @Property(str, notify=changed)
    def preferenceDetails(self):
        tr=lambda text:translate(text,self._language)
        if not self._preference_notice:return ''
        intro='The display keeps running, but your changes may be lost after closing. Check the configuration folder permissions and available disk space, then retry saving.' if self._preference_kind=='save' else 'Some settings could not be restored. The app is using fallback values for the affected settings; other valid preferences were kept. Review the settings below. Valid changes will be saved automatically.'
        if self._preference_kind=='load' and self._preference_detail:
            intro='The configuration file could not be loaded. The app started with default preferences. Review the technical details below.'
        lines=[tr(intro)]
        if self.preferences:
            lines.extend(['',tr('Configuration file')+': '+str(self.preferences.path)])
        names={'fps':'Frame rate','quality':'JPEG quality','delay_ms':'Inter-report delay (ms)',
               'font_path':'Typeface file','font_weight':'Variable font weight','accent':'LCD accent',
               'comet_style':'Comet','comet_speed':'Comet speed','temperature_unit':'Units',
               'temperature_decimals':'Temperature','rotation':'Rotation','language':'Language','theme':'Application theme'}
        for issue in self._preference_issues:
            value=issue['fallback']
            if value is None:value=tr('Bundled Outfit (default)')
            elif isinstance(value,str):value=tr({'en':'English','es':'Español','dark':'Dark','light':'Light','C':'°C','F':'°F','accent':'Accent','rainbow':'Rainbow'}.get(value,value))
            lines.extend(['',tr(names.get(issue['field'],issue['field']))+': '+tr(issue['reason']),
                          tr('Fallback value')+': '+str(value)])
        if self._preference_detail:
            lines.extend(['',tr('Technical details')+': '+tr(self._preference_detail)])
        return '\n'.join(lines)
    @Property(str, notify=changed)
    def errorMessage(self): return runtime_text(self._error or self._preference_notice,self._language)
    @Property(str, notify=changed)
    def sleepStatus(self): return runtime_text(self._sleep_status,self._language)
    @Property(str, constant=True)
    def initialDevice(self): return self.settings.device or ''
    @Property(str, notify=changed)
    def statistics(self): return runtime_text(self._statistics,self._language)
    @Property(str, notify=sensorsChanged)
    def sampleLabel(self): return runtime_text(self._sample,self._language)
    @Property('QVariantList', notify=sensorsChanged)
    def sensorRows(self): return self._rows
    @Property('QStringList', notify=devicesChanged)
    def devices(self): return self._devices
    @Property(str, notify=frameChanged)
    def previewUrl(self): return f'image://frames/{self._frame}'
    @Property(str, constant=True)
    def applicationName(self): return APP_NAME
    @Property(QUrl, constant=True)
    def brandIconBase(self): return QUrl.fromLocalFile(str(Path(__file__).parent/'assets/branding')+'/')
    @Property(QUrl, constant=True)
    def uiFontUrl(self): return QUrl.fromLocalFile(str(Path(__file__).parent/'assets/fonts/Outfit.ttf'))
    @Property(str, constant=True)
    def initialFont(self): return self.settings.font_path or ''
    @Property(int, constant=True)
    def initialFps(self): return int(self.settings.fps)
    @Property(int, constant=True)
    def initialQuality(self): return self.settings.quality
    @Property(str, constant=True)
    def initialDelay(self): return str(self.settings.delay_ms)
    @Property(str, constant=True)
    def initialAccent(self): return self.settings.accent
    @Property(str, constant=True)
    def initialCometStyle(self): return self.settings.comet_style
    @Property(float, constant=True)
    def initialCometSpeed(self): return self.settings.comet_speed
    @Property(int, constant=True)
    def initialWeight(self): return self.settings.font_weight
    @Property(bool, constant=True)
    def initialDecimals(self): return self.settings.temperature_decimals == 1

    @Slot()
    def refreshDevices(self):
        self._devices = find_devices()
        self.devicesChanged.emit()

    def configuration(self, options):
        return replace(self.settings,
                fps=float(options.get('fps',self.settings.fps)),
                quality=int(options.get('quality',self.settings.quality)),
                delay_ms=float(options.get('delay',self.settings.delay_ms)),
                font_path=str(options.get('font',self.settings.font_path or '')) or None,
                font_weight=int(options.get('weight',self.settings.font_weight)),
                comet_speed=float(options.get('cometSpeed',self.settings.comet_speed)),
                accent=str(options.get('accent',self.settings.accent)),
                comet_style=str(options.get('cometStyle',self.settings.comet_style)),
                temperature_decimals=1 if options.get('decimals',self.settings.temperature_decimals == 1) else 0,
                temperature_unit=str(options.get('temperatureUnit',self.settings.temperature_unit)),
                device=str(options.get('device',self.settings.device or '')) or None)

    @Slot('QVariantMap', bool)
    def start(self, options, send):
        if self._running:
            return
        try:
            config = self.configuration(options)
            config.validate()
            self.settings = config
            self.session = self.session_factory(config,send=send,provider=self.provider)
            self._error = ''
            self._sequence = -1
            self._running = True
            self._sending = send
            self._status = 'Sending to LCD' if send else 'Preview only — LCD untouched'
            self.session.start()
        except Exception as error:
            self._running = self._sending = False
            self._error = str(error)
            self._status = 'Could not start'
        self.changed.emit()

    @Slot()
    def startup(self):
        devices = self._devices
        device = self.settings.device or (devices[0] if len(devices) == 1 else None)
        self.start({'device':device or ''},bool(device))

    @Slot()
    def stopOutput(self):
        if self.session:
            self.session.set_output(False)
            self._status = 'Returning LCD to standby…'
            self.changed.emit()

    @Slot('QVariantMap')
    def startOutput(self, options):
        self.reconfigure(options,True)

    @Slot('QVariantMap')
    def applySettings(self, options):
        self.reconfigure(options,None)

    def reconfigure(self, options, send):
        try:
            config = self.configuration(options)
            config.validate()
            if self._running:
                self.session.configure(config,send)
            else:
                self.start(options,bool(send))
        except Exception as error:
            self._error = str(error)
            self.changed.emit()

    @Slot()
    def stop(self):
        if self.session and self._running:
            self._status = 'Stopping after the current frame…'
            self.session.stop()
            self.changed.emit()

    @Slot(result=bool)
    def requestClose(self):
        self.flushPreferences()
        if not self._running:
            QCoreApplication.quit()
            return True
        self._closing = True
        self.stop()
        return False

    def poll(self):
        if self.session is None:
            return
        try:
            event = self.session.events.get_nowait()
        except queue.Empty:
            return
        if event['kind'] == 'stopped':
            if event.get('last_frame'):
                self.apply_frame(event['last_frame'])
            self._running = self._sending = False
            self._error = event['error'] or ''
            self._status = 'Stopped' if not self._error else 'Stopped — check the error below'
            self.changed.emit()
            if self._closing:
                QCoreApplication.quit()
            return
        self.apply_frame(event)

    def apply_frame(self, event):
        self._sending = event['sent']
        self._error = event.get('config_error') or event.get('output_error') or ''
        if self.session and not event.get('config_error'):
            if self.settings != self.session.settings:
                self.settings = self.session.settings
                self.save_timer.start()
        self._status = 'Sending to LCD' if self._sending else 'LCD paused'
        self.images.update(event['image'])
        self._frame += 1
        self.frameChanged.emit()
        if event['sequence'] != self._sequence:
            self._sequence = event['sequence']
            self._rows = diagnostic_rows(event)
            self._sample = f"Sample #{event['sequence']} · {event['timestamp']}"
            self.sensorsChanged.emit()
        tx = f"{event['transmission_ms']:.1f} ms USB" if event['sent'] else 'USB not opened'
        self._statistics = f"{event['frames']} frames · {event['reports']} reports/frame · {tx} · {event['pipeline_ms']:.1f} ms pipeline"
        self.changed.emit()


def create_engine(app, settings, provider=None, preferences=None, application=None, session_factory=Session, autostart=None, start_minimized=False):
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setWindowIcon(application_icon())
    QQuickStyle.setStyle("Basic")
    bridge = Bridge(settings,provider=provider,preferences=preferences,application=application,session_factory=session_factory,autostart=autostart,start_minimized=start_minimized)
    engine = QQmlApplicationEngine()
    engine.addImageProvider('frames',bridge.images)
    engine.rootContext().setContextProperty('bridge',bridge)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent/'qml/Main.qml')))
    if not engine.rootObjects():
        raise RuntimeError('The QML interface could not be loaded')
    # Keep the QObject and image-provider references alive for the engine's lifetime.
    engine.bridge = bridge
    return engine,bridge


def dispose_engine(engine):
    # Destroy bound QML objects before their Python controller is released.
    for window in engine.rootObjects():
        window.deleteLater()
    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    engine.deleteLater()
    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)


def launch(args):
    from PySide6.QtWidgets import QApplication
    from .tray import TrayController
    app = QApplication.instance() or QApplication(['fx240'])
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(APP_NAME)
    from .preferences import Preferences
    preferences = Preferences()
    settings,application = preferences.load()
    explicit = getattr(args,'explicit_options',set())
    mapping = {'--fps':'fps','--quality':'quality','--delay-ms':'delay_ms',
               '--rotation':'rotation','--font':'font_path','--font-weight':'font_weight',
               '--comet-speed':'comet_speed','--accent':'accent','--comet-style':'comet_style',
               '--temperature-decimals':'temperature_decimals','--temperature-unit':'temperature_unit',
               '--device':'device'}
    overrides = {}
    for option,field in mapping.items():
        if option in explicit:
            value = getattr(args,'font' if field=='font_path' else field)
            overrides[field] = str(value) if field=='font_path' and value else value
    settings = replace(settings,**overrides)
    settings.validate()
    from .autostart import Autostart
    minimized = getattr(args,"start_minimized",False)
    engine,bridge = create_engine(app,settings,preferences=preferences,application=application,autostart=Autostart(),start_minimized=minimized)
    tray = TrayController(engine.rootObjects()[0],bridge)
    if minimized:tray.start_minimized()
    from .sleep import SleepMonitor
    sleep_monitor = SleepMonitor(bridge)
    QTimer.singleShot(0,bridge.startup)
    result = app.exec()
    bridge.stop()
    if bridge.session and bridge.session.thread:
        bridge.session.thread.join(timeout=2)
    bridge.flushPreferences()
    sleep_monitor.release()
    tray.dispose()
    dispose_engine(engine)
    return result
