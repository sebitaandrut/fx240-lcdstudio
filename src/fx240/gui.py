# SPDX-License-Identifier: GPL-3.0-or-later
"""Qt Quick desktop controller. The renderer and transport remain independent."""
from dataclasses import replace
from pathlib import Path
import queue
import sys
import threading
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer, QUrl, QCoreApplication, QEvent
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from .dashboard import default_metrics
from .focus import temperature
from .session import Session, Settings, find_devices
from .i18n import translate, runtime_text
from .branding import APP_NAME, application_icon
from .preview import FrameProvider


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
    fontsChanged = Signal()
    fontDiscoveryFinished = Signal(object,str)
    profilesChanged = Signal()

    def __init__(self, settings, provider=None, session_factory=Session, image_provider=None, preferences=None, application=None, autostart=None, start_minimized=False, standby_guard=None):
        super().__init__()
        from .profiles import ProfileStore
        path=getattr(preferences,'path',None)
        self._profiles=ProfileStore(Path(path).parent/'profiles.json') if isinstance(path,(str,Path)) else ProfileStore(memory=True)
        if not settings.draft_scene_json and settings.scene_json and not settings.profile_id:
            settings=replace(settings,draft_scene_json=settings.scene_json)
        self._profile_notice=''
        profile=self._profiles.get(settings.profile_id)
        if profile:
            try:
                from .scene import SceneRenderer
                validated=SceneRenderer(scene_json=profile['scene'],font_path=settings.font_path,provider=lambda:[])
                validated.close()
                settings=replace(settings,layout_mode='editor',scene_json=profile['scene'])
            except (OSError,ValueError):
                settings=replace(settings,layout_mode='focus',scene_json='',profile_id='')
                self._profile_notice='Active profile could not be loaded; using Focus'
        else:
            if settings.profile_id:self._profile_notice='Active profile no longer exists; using Focus'
            settings=replace(settings,layout_mode='focus',scene_json='',profile_id='')
        self.settings = settings
        self.standby_guard = standby_guard
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
        self._system_fonts = []
        self._font_notice = ''
        self._font_busy = False
        self.fontDiscoveryFinished.connect(self._acceptFonts)
        self._latest_metrics=[]
        from .workspace import EditorWorkspace
        self._workspace=EditorWorkspace(settings,self._profiles,lambda:self.settings,lambda:self._latest_metrics,
                                        lambda:self._system_fonts,lambda:self._language)
        from .livepreview import LiveDraftPreview
        self._live_preview=LiveDraftPreview(self)
        self._workspace.validated.connect(self._live_preview.validated)
        self._workspace.draftChanged.connect(self.save_timer.start)
        self._workspace.libraryChanged.connect(self.profilesChanged)
        self._workspace.libraryChanged.connect(self.changed)
        self._workspace.profileSaved.connect(self._profileSaved)
        self._workspace.profileDeleted.connect(self._profileDeleted)
        self._workspace.activationRequested.connect(self.activateProfile)
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
        self._shutdown_status = 'Shutdown integration not initialized'
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
            self.fontsChanged.emit()
            self._workspace.changed.emit()
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
            self.preferences.save(self._workspace.preferences(self.settings),self._language,self._ui_theme)
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
               'animation':'Animation','background_path':'Background','background_dim':'Dimming',
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
    @Property(str, notify=changed)
    def shutdownStatus(self): return runtime_text(self._shutdown_status,self._language)
    @Property(str, notify=changed)
    def standbyFallbackStatus(self):
        text="Standby fallback: independent process started" if self.standby_guard is not None and self.standby_guard.writer is not None else "Standby fallback: independent process unavailable"
        return runtime_text(text,self._language)
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
    @Property(QObject,constant=True)
    def workspace(self):return self._workspace
    @Property(QObject,constant=True)
    def livePreview(self):return self._live_preview
    @Property(str,notify=changed)
    def layoutMode(self):return self.settings.layout_mode
    @Property('QStringList',notify=profilesChanged)
    def contentLabels(self):return ['Focus']+[item['name'] for item in self._profiles.profiles]
    @Property(int,notify=changed)
    def activeContentIndex(self):
        return next((index+1 for index,item in enumerate(self._profiles.profiles) if item['id']==self.settings.profile_id),0)
    @Property(str,notify=changed)
    def activeContentName(self):
        item=self._profiles.get(self.settings.profile_id)
        return item['name'] if item else 'Focus'
    @Property(str,notify=changed)
    def activeProfileId(self):return self.settings.profile_id
    @Property(str,notify=changed)
    def profileNotice(self):return runtime_text(self._profile_notice or self._profiles.error,self._language)

    @Slot(int)
    def selectContent(self,index):
        if index==0:self.useFocus()
        elif 1<=index<=len(self._profiles.profiles):self.activateProfile(self._profiles.profiles[index-1]['id'])
    @Slot(str)
    def activateProfile(self,identifier):
        item=self._profiles.get(identifier)
        if item:
            self._profile_notice=''
            self.reconfigure({'layoutMode':'editor','scene':item['scene'],'profileId':identifier},None)
    @Slot()
    def useFocus(self):self.reconfigure({'layoutMode':'focus','profileId':'','scene':''},None)
    @Slot()
    def editActive(self):
        if self.settings.profile_id:self._workspace.request_profile(self.settings.profile_id)
        else:self._workspace.requestNew()
    def _profileSaved(self,identifier):
        if identifier==self.settings.profile_id and not self._live_preview.active:self.activateProfile(identifier)
    def _profileDeleted(self,identifier):
        if identifier==self.settings.profile_id:self.useFocus()
        self.changed.emit()

    @Property(str, constant=True)
    def initialAnimation(self): return self.settings.animation
    @Property(str, constant=True)
    def initialBackground(self): return self.settings.background_path or ''
    @Property(float, constant=True)
    def initialBackgroundDim(self): return self.settings.background_dim
    @Property('QStringList', notify=fontsChanged)
    def systemFontLabels(self): return ['Bundled Outfit (default)']+[label for label,_ in self._system_fonts]
    @Property(str, notify=fontsChanged)
    def fontNotice(self): return translate(self._font_notice,self._language)
    @Property(bool, notify=fontsChanged)
    def fontDiscoveryBusy(self): return self._font_busy
    @Property('QVariantMap',notify=changed)
    def globalFontInfo(self):
        from .typography import capabilities
        try:return capabilities(self.settings.font_path)
        except (OSError,ValueError):return {'variable':False,'minimum':100,'maximum':900}
    @Slot()
    def refreshSystemFonts(self):
        if self._font_busy:return
        self._font_busy=True
        self._font_notice='Discovering local fonts…'
        self.fontsChanged.emit()
        threading.Thread(target=self._discoverFonts,name='fx240-fonts',daemon=True).start()

    def _discoverFonts(self):
        from .systemfonts import catalog
        try:
            fonts=catalog()
            notice='' if fonts else 'No supported system fonts found'
        except ValueError as error:
            fonts=[];notice=str(error)
        try:self.fontDiscoveryFinished.emit(fonts,notice)
        except RuntimeError:pass # The window may have been destroyed during discovery.

    @Slot(object,str)
    def _acceptFonts(self,fonts,notice):
        self._system_fonts=fonts
        self._font_notice=notice
        self._font_busy=False
        self.fontsChanged.emit()
        self._workspace.fonts_changed()
    @Slot(str,result=str)
    def fontLabel(self,path):
        return next((label for label,source in self._system_fonts if source==path),Path(path).stem[:128])
    @Slot(int,result=str)
    def systemFontPath(self,index):
        if index==0:return ''
        if 1<=index<=len(self._system_fonts):return self._system_fonts[index-1][1]
        return self.settings.font_path or ''
    @Slot(QUrl,result=str)
    def localPath(self,url):
        return url.toLocalFile() if url.isLocalFile() else ''
    @Property(float, constant=True)
    def initialCometSpeed(self): return self.settings.comet_speed
    @Property(int, constant=True)
    def initialWeight(self): return self.settings.font_weight
    @Property(str, constant=True)
    def applicationVersion(self):
        from . import __version__
        return __version__
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
                animation=str(options.get('animation',self.settings.animation)),
                background_path=str(options.get('background',self.settings.background_path or '')) or None,
                background_dim=float(options.get('backgroundDim',self.settings.background_dim)),
                layout_mode=str(options.get('layoutMode',self.settings.layout_mode)),
                scene_json=str(options.get('scene',self.settings.scene_json)),
                profile_id=str(options.get('profileId',self.settings.profile_id)),
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
            self.session = self.session_factory(config,send=send,provider=self.provider,**({"standby_guard":self.standby_guard} if self.standby_guard is not None else {}))
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
        if self._live_preview.active:
            self._live_preview.pause_output();return
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
        if self._live_preview.active:
            self._workspace.reject('Finish LCD preview before changing output settings');return
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
        if self._live_preview.active:
            if self._tray:self._tray.restore()
            self._live_preview.request_close();return False
        self._workspace.stop()
        self.flushPreferences()
        if not self._running:
            QCoreApplication.quit()
            return True
        self._closing = True
        self.stop()
        return False

    def poll(self):
        self._workspace.poll()
        if self.session is None:
            return
        try:
            event = self.session.events.get_nowait()
        except queue.Empty:
            return
        if event['kind'] == 'stopped':
            if event.get('last_frame'):
                self.apply_frame(event['last_frame'])
            self._live_preview.reset()
            self._running = self._sending = False
            self._error = event['error'] or ''
            self._status = 'Stopped' if not self._error else 'Stopped — check the error below'
            self.changed.emit()
            if self._closing:
                QCoreApplication.quit()
            return
        self.apply_frame(event)

    @Property('QVariantMap',notify=changed)
    def gifBufferStatistics(self):
        from .gifstream import statistics,BUFFER_FRAMES
        stats=statistics(self.session.thread) if self.session else {}
        streams=stats.get('streams',0)
        return {'streams':streams,'queued':stats.get('queued_frames',0),
                'capacity':streams*BUFFER_FRAMES,'waits':stats.get('underruns',0)}

    def apply_frame(self, event):
        self._latest_metrics=event['metrics']
        self._sending = event['sent']
        self._error = event.get('config_error') or event.get('output_error') or ''
        committed=self._live_preview.frame(event)
        if self.session and committed and not event.get('config_error'):
            accepted=event.get('configuration',self.session.settings)
            if self.settings != accepted:
                self.settings = accepted
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


def create_engine(app, settings, provider=None, preferences=None, application=None, session_factory=Session, autostart=None, start_minimized=False, standby_guard=None):
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setDesktopFileName('org.fx240lcdstudio')
    app.setWindowIcon(application_icon())
    QQuickStyle.setStyle("Basic")
    from .filebrowser import register_qml_type
    register_qml_type()
    bridge = Bridge(settings,provider=provider,preferences=preferences,application=application,session_factory=session_factory,autostart=autostart,start_minimized=start_minimized,standby_guard=standby_guard)
    engine = QQmlApplicationEngine()
    engine.addImageProvider('frames',bridge.images)
    engine.addImageProvider('draft',bridge.workspace.images)
    engine.rootContext().setContextProperty('bridge',bridge)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent/'qml/Main.qml')))
    if not engine.rootObjects():
        raise RuntimeError('The QML interface could not be loaded')
    # Keep the QObject and image-provider references alive for the engine's lifetime.
    engine.bridge = bridge
    return engine,bridge


def dispose_engine(engine):
    bridge=engine.bridge
    bridge.timer.stop();bridge.workspace.close()
    # Destroy bound QML objects before their Python controller is released.
    for window in engine.rootObjects():
        window.deleteLater()
    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    engine.deleteLater()
    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)


def desktop_storage(custom_home=None):
    """Isolate Studio files without hiding the desktop's XDG user directories."""
    from .preferences import Preferences
    from .autostart import Autostart
    if custom_home is not None:
        custom_home=Path(custom_home)
        if not custom_home.is_absolute() or len(str(custom_home))>4096 or any(ord(c)<32 for c in str(custom_home)):
            raise ValueError('Configuration directory must be an absolute path without control characters')
    preferences=Preferences(custom_home/'fx240-linux/settings.json' if custom_home else None)
    startup=Autostart(config_home=custom_home)
    if custom_home:
        startup=Autostart(config_home=custom_home,command=(*startup.command,'--config-home',str(custom_home)))
    return preferences,startup


def launch(args,standby_guard=None,trace=None):
    from PySide6.QtWidgets import QApplication
    from .tray import TrayController
    app = QApplication.instance() or QApplication(['fx240'])
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(APP_NAME)
    preferences,startup=desktop_storage(getattr(args,'config_home',None))
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
    minimized = getattr(args,"start_minimized",False)
    engine,bridge = create_engine(app,settings,preferences=preferences,application=application,autostart=startup,start_minimized=minimized,standby_guard=standby_guard)
    tray = TrayController(engine.rootObjects()[0],bridge)
    if minimized:tray.start_minimized()
    from .sleep import SleepMonitor
    sleep_monitor = SleepMonitor(bridge)
    from .shutdown import ShutdownMonitor
    shutdown_monitor = ShutdownMonitor(app,bridge,trace=trace)
    QTimer.singleShot(0,bridge.startup)
    try:
        return app.exec()
    finally:
        if trace:trace.emit("gui-loop-returned")
        shutdown_monitor.finish()
        shutdown_monitor.dispose()
        sleep_monitor.release()
        tray.dispose()
        dispose_engine(engine)
