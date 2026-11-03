# SPDX-License-Identifier: GPL-3.0-or-later
"""Isolated editor workspace: drafts, named local profiles, and preview lifecycle."""
from dataclasses import replace
from PySide6.QtCore import QObject,Property,Signal,Slot,QTimer,QUrl
import queue
from .editor import EditorModel
from .preview import FrameProvider
from .scene import parse_scene,scene_json
from .session import Session
from .typography import capabilities
from .i18n import runtime_text


class EditorWorkspace(QObject):
    changed=Signal()
    frameChanged=Signal()
    libraryChanged=Signal()
    draftChanged=Signal()
    profileSaved=Signal(str)
    profileDeleted=Signal(str)
    activationRequested=Signal(str)
    discardRequested=Signal()
    validated=Signal(str)

    def __init__(self,settings,store,settings_provider,metrics_provider,fonts_provider,language_provider):
        super().__init__()
        self.store=store;self.settings_provider=settings_provider;self.metrics_provider=metrics_provider
        self.fonts_provider=fonts_provider;self.language_provider=language_provider
        self._model=EditorModel(settings.draft_scene_json)
        self._model.sceneChanged.connect(self._queue)
        self._model.changed.connect(self.changed)
        self._model.rejected.connect(self.reject)
        self.images=FrameProvider();self.session=None;self.visible=False
        self._frame=0;self._notice=store.error;self._failed=False;self._validated=False
        self._valid_payload=self._model.payload()
        self._loaded_id=settings.draft_profile_id if store.get(settings.draft_profile_id) else ''
        self._name=settings.draft_name
        saved=store.get(self._loaded_id)
        self._baseline=saved['scene'] if saved else self._model.payload()
        self._baseline_name=saved['name'] if saved else ''
        self._pending=None;self._font_key=None;self._font_info={};self._styles=[]
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(40)
        self.timer.timeout.connect(self._configure)

    @Property(QObject,constant=True)
    def model(self):return self._model
    @Property(str,notify=frameChanged)
    def previewUrl(self):return f'image://draft/{self._frame}'
    @Property(str,notify=changed)
    def notice(self):return runtime_text(self._notice,self.language_provider())
    @Property(bool,notify=changed)
    def ready(self):return self._validated and self._valid_payload==self._model.payload()
    @Property(str,notify=changed)
    def validatedScene(self):return self._valid_payload if self.ready else ''
    @Property(str,notify=changed)
    def profileName(self):return self._name
    @Property(str,notify=changed)
    def loadedId(self):return self._loaded_id
    @Property(bool,notify=changed)
    def dirty(self):return self._model.payload()!=self._baseline or self._name!=self._baseline_name

    @Slot(str)
    def reject(self,message):self._notice=message;self.changed.emit()
    @Slot(str)
    def setProfileName(self,name):
        if self._name==name:return
        self._name=name;self.changed.emit();self.draftChanged.emit()

    def _queue(self):
        self._failed=False
        if not self.timer.isActive():self.timer.start()
        self.changed.emit();self.draftChanged.emit()

    @Slot(bool)
    def setVisible(self,visible):
        self.visible=visible
        if visible:self._failed=False;self.ensure_preview()
        elif self.session:self.session.stop()

    def ensure_preview(self):
        if not self.visible or self._failed or self.session is not None:return
        config=replace(self.settings_provider(),layout_mode='editor',scene_json=self._model.payload(),device=None)
        def forbid(path):raise RuntimeError('Draft preview cannot access USB')
        self.session=Session(config,provider=lambda:list(self.metrics_provider()),transport_factory=forbid)
        self.session.start()

    def _configure(self):
        self._notice=''
        if self.session and not self.session.stop_event.is_set():
            self.session.configure(replace(self.settings_provider(),layout_mode='editor',scene_json=self._model.payload(),device=None),False)
        else:self.ensure_preview()
        self.changed.emit()

    def poll(self):
        if self.session:
            try:event=self.session.events.get_nowait()
            except queue.Empty:event=None
            if event:
                if event['kind']=='stopped':
                    self._notice=event.get('error') or '';self.session=None
                    if self._notice:self._failed=True;self._validated=False
                else:
                    self.images.update(event['image']);self._frame+=1;self.frameChanged.emit()
                    self._notice=event.get('config_error') or ''
                    if not self._notice:
                        previous=self._valid_payload;was_validated=self._validated
                        self._valid_payload=event.get('configuration',self.session.settings).scene_json;self._validated=True
                        if self.ready and (not was_validated or previous!=self._valid_payload):self.validated.emit(self._valid_payload)
                self.changed.emit()
        self.ensure_preview()

    def preferences(self,settings):
        return replace(settings,draft_scene_json=self._valid_payload,draft_name=self._name[:32],draft_profile_id=self._loaded_id)

    @Slot(QUrl,bool)
    def addMedia(self,url,replace_selected=False):
        if not url.isLocalFile():self.reject('Choose a local image or GIF');return
        if replace_selected and self._model.selected.get('kind')=='media':self._model.updateSelected({'path':url.toLocalFile()})
        else:self._model.add_layer('media',url.toLocalFile())

    def _request(self,target):
        if self.dirty:self._pending=target;self.discardRequested.emit()
        else:self._load(target)
    @Slot()
    def requestNew(self):self._request('')
    def request_profile(self,identifier):self._request(identifier)
    @Slot()
    def confirmDiscard(self):
        target=self._pending;self._pending=None
        if target is not None:self._load(target)
    @Slot()
    def cancelDiscard(self):self._pending=None

    def _load(self,identifier):
        item=self.store.get(identifier) if identifier else None
        if identifier and item is None:self.reject('Profile no longer exists');return
        self._model.replace(parse_scene(item['scene']) if item else parse_scene(),0)
        self._model.history.clear();self._model.gesture=False
        self._loaded_id=identifier;self._name=item['name'] if item else ''
        self._baseline=self._model.payload();self._baseline_name=self._name
        self._validated=False;self._failed=False;self._font_key=None
        self._queue();self.changed.emit()

    @Slot(bool,bool,result=bool)
    def save(self,show=False,copy=False):
        if not self.ready:self.reject('Wait for a valid preview before saving');return False
        name=self._name
        if copy:
            saved=self.store.get(self._loaded_id)
            if saved and name.strip()==saved['name']:
                names={item['name'].casefold() for item in self.store.profiles}
                base=name.strip()[:22];suffix=runtime_text('copy',self.language_provider());number=1
                name=base+' '+suffix
                while name.casefold() in names:
                    number+=1;name=base+' '+suffix+' '+str(number)
        try:
            identifier=self.store.save(name,self._valid_payload,None if copy else self._loaded_id or None)
        except ValueError as error:self.reject(str(error));return False
        except OSError:self.reject('Profile could not be saved; check folder permissions and available disk space');return False
        self._loaded_id=identifier;self._name=name.strip();self._baseline=self._valid_payload;self._baseline_name=self._name
        self._notice='Profile saved';self.libraryChanged.emit();self.profileSaved.emit(identifier)
        self.changed.emit();self.draftChanged.emit()
        if show:self.activationRequested.emit(identifier)
        return True

    @Slot(result=bool)
    def deleteLoaded(self):
        if not self._loaded_id:return False
        if self._loaded_id==self.settings_provider().profile_id:
            self.reject('Switch to Focus in Display before deleting this profile');return False
        identifier=self._loaded_id
        try:self.store.delete(identifier)
        except (ValueError,OSError):self.reject('Profile could not be deleted; the library was preserved');return False
        self._loaded_id='';self._baseline_name='';self._notice='Profile deleted; the draft is still available'
        self.libraryChanged.emit();self.profileDeleted.emit(identifier);self.changed.emit();self.draftChanged.emit()
        return True

    def _font_details(self):
        selected=self._model.selected;source=selected.get('font_path') or self.settings_provider().font_path
        key=(selected.get('kind'),source)
        if key==self._font_key:return
        self._font_key=key;self._styles=[]
        if selected.get('kind') not in ('text','metric'):
            self._font_info={'variable':False,'minimum':100,'maximum':900};return
        try:self._font_info=capabilities(source)
        except (OSError,ValueError):self._font_info={'variable':False,'minimum':100,'maximum':900,'style':'Unavailable'};return
        if self._font_info['variable']:return
        catalog=self.fonts_provider()
        match=next((label for label,path in catalog if path==source),None)
        family=match.rpartition(' · ')[0] if match else self._font_info['family']
        self._styles=[(label.rpartition(' · ')[2],path) for label,path in catalog if label.rpartition(' · ')[0]==family]
        if not self._styles:self._styles=[(self._font_info['style'],source)]

    @Property('QVariantMap',notify=changed)
    def fontInfo(self):self._font_details();return dict(self._font_info)
    @Property('QStringList',notify=changed)
    def fontStyles(self):self._font_details();return [label for label,_ in self._styles]
    @Property(int,notify=changed)
    def fontStyleIndex(self):
        self._font_details();source=self._model.selected.get('font_path') or self.settings_provider().font_path
        return next((index for index,(_,path) in enumerate(self._styles) if path==source),0)
    @Slot(int)
    def selectFontStyle(self,index):
        self._font_details()
        if 0<=index<len(self._styles):self._model.updateSelected({'font_path':self._styles[index][1]})
    def fonts_changed(self):self._font_key=None;self.changed.emit()

    def stop(self):
        self.timer.stop();self.visible=False
        if self.session:self.session.stop()

    def close(self):
        self.stop()
        if self.session and self.session.thread:self.session.thread.join(timeout=2)
