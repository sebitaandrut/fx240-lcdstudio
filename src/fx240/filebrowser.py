# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded, asynchronous local asset navigation; no catalogs or paths are logged."""
import os
from pathlib import Path
import threading
from PySide6.QtCore import QObject,Property,Signal,Slot,QUrl,QStandardPaths

MAX_ENTRIES=4096
EXTENSIONS={'image':{'.png','.jpg','.jpeg','.gif','.webp','.bmp'},'font':{'.ttf','.otf'}}


def standard_locations():
    """Use configured XDG folders, omitting missing/duplicate shortcuts."""
    values=[('Home',QStandardPaths.HomeLocation),('Downloads',QStandardPaths.DownloadLocation),
            ('Pictures',QStandardPaths.PicturesLocation),('Documents',QStandardPaths.DocumentsLocation),
            ('Desktop',QStandardPaths.DesktopLocation)]
    result=[];seen=set()
    for label,kind in values:
        value=QStandardPaths.writableLocation(kind)
        if not value:continue
        path=Path(value)
        if not path.is_absolute() or not path.is_dir():continue
        text=str(path)
        if text not in seen:result.append({'label':label,'path':text});seen.add(text)
    return result


def scan_folder(path,kind):
    entries=[];limited=False
    try:
        with os.scandir(path) as listing:
            for index,entry in enumerate(listing):
                if index>=MAX_ENTRIES:limited=True;break
                if entry.name.startswith('.') or any(0xd800<=ord(c)<=0xdfff for c in entry.name):continue
                try:
                    folder=entry.is_dir()
                    if not folder and (Path(entry.name).suffix.lower() not in EXTENSIONS[kind] or not entry.is_file(follow_symlinks=False)):continue
                except OSError:continue
                label=''.join(c if ord(c)>=32 and ord(c)!=127 else '�' for c in entry.name)
                entries.append({'name':label,'path':entry.path,'folder':folder})
        entries.sort(key=lambda item:(not item['folder'],item['name'].casefold()))
        return entries,'Folder is large; only the first entries are listed' if limited else ''
    except OSError:return [],'This folder could not be read. Choose another folder.'


class LocalFileBrowser(QObject):
    changed=Signal()
    entriesChanged=Signal()
    locationsChanged=Signal()
    chosen=Signal(QUrl)
    listingReady=Signal(int,object,str)

    def __init__(self,parent=None):
        super().__init__(parent)
        self._entries=[];self._locations=[];self._folder='';self._selected=-1
        self._kind='image';self._notice='';self._busy=False;self._visible=False
        self._worker_busy=False;self._pending=None;self._generation=0;self._last={}
        self.listingReady.connect(self._accept)

    @Property('QVariantList',notify=entriesChanged)
    def entries(self):return self._entries
    @Property('QVariantList',notify=locationsChanged)
    def locations(self):return self._locations
    @Property(str,notify=changed)
    def folder(self):return self._folder
    @Property(str,notify=changed)
    def notice(self):return self._notice
    @Property(bool,notify=changed)
    def busy(self):return self._busy
    @Property(int,notify=changed)
    def selectedIndex(self):return self._selected
    @Property(str,notify=changed)
    def selectedName(self):
        return self._entries[self._selected]['name'] if self._selected>=0 else ''
    @Property(bool,notify=changed)
    def canOpen(self):return self._selected>=0 and not self._busy
    @Property(bool,notify=changed)
    def canChoose(self):return self._selected>=0 and not self._entries[self._selected]['folder'] and not self._busy
    @Property(str,notify=changed)
    def kind(self):return self._kind

    @Slot(str,str)
    def open(self,kind,initial):
        if kind not in EXTENSIONS:return
        self._kind=kind;self._visible=True;self._locations=standard_locations();self.locationsChanged.emit()
        path=Path(initial) if initial else None
        if path and path.is_absolute():path=path if path.is_dir() else path.parent
        else:path=Path(self._last[kind]) if kind in self._last else None
        if path is None or not path.is_dir():path=Path(self._locations[0]['path']) if self._locations else Path.home()
        self.go(str(path))

    @Slot(str)
    def go(self,path):
        if not self._visible:return
        try:
            if '://' in path or not path or len(path)>4096 or any(ord(c)<32 for c in path):raise ValueError()
            selected=Path(path).expanduser()
            if not selected.is_absolute():raise ValueError()
            selected=Path(os.path.abspath(selected))
        except (OSError,RuntimeError,ValueError):
            self._notice='Enter an absolute local folder path';self.changed.emit();return
        self._folder=str(selected);self._entries=[];self._selected=-1;self._notice=''
        self._busy=True;self._generation+=1
        self._pending=(self._generation,self._folder,self._kind)
        self.entriesChanged.emit();self.changed.emit();self._launch()

    def _launch(self):
        if self._worker_busy or self._pending is None:return
        generation,path,kind=self._pending;self._pending=None;self._worker_busy=True
        def run():
            entries,notice=scan_folder(path,kind)
            try:self.listingReady.emit(generation,entries,notice)
            except RuntimeError:pass # The owning dialog was destroyed.
        threading.Thread(target=run,name='fx240-file-picker',daemon=True).start()

    @Slot(int,object,str)
    def _accept(self,generation,entries,notice):
        self._worker_busy=False
        if self._visible and generation==self._generation:
            self._entries=entries;self._notice=notice;self._busy=False;self._last[self._kind]=self._folder
            self.entriesChanged.emit();self.changed.emit()
        self._launch()

    @Slot()
    def up(self):self.go(str(Path(self._folder).parent))
    @Slot()
    def clearSelection(self):self._selected=-1;self.changed.emit()
    @Slot(int)
    def select(self,index):
        self._selected=index if not self._busy and 0<=index<len(self._entries) else -1
        self.changed.emit()
    @Slot(int)
    def activate(self,index):
        self.select(index)
        if self._selected<0:return
        entry=self._entries[self._selected]
        if entry['folder']:self.go(entry['path'])
        else:self.choose()
    @Slot()
    def choose(self):
        if self.canChoose:
            url=QUrl.fromLocalFile(self._entries[self._selected]['path'])
            self.cancel();self.chosen.emit(url)
    @Slot()
    def cancel(self):
        self._visible=False;self._generation+=1;self._pending=None
        self._entries=[];self._selected=-1;self._busy=False;self.entriesChanged.emit();self.changed.emit()


_registered=False

def register_qml_type():
    global _registered
    if not _registered:
        from PySide6.QtQml import qmlRegisterType
        qmlRegisterType(LocalFileBrowser,'Fx240',1,0,'LocalFileBrowser')
        _registered=True
