# SPDX-License-Identifier: GPL-3.0-or-later
"""Qt scene model. Roles expose geometry/titles, never asset paths or scripts."""
from PySide6.QtCore import QAbstractListModel,QModelIndex,Qt,Property,Signal,Slot
import math
from .scene import parse_scene,scene_json,layer,default_scene

TITLES={'cpu_temp':'CPU temperature','cpu_clock':'CPU frequency','gpu_temp':'GPU temperature','gpu_clock':'GPU frequency'}
ROLE_FIELDS=('layerId','kind','px','py','pw','ph','shown','title')


class EditorModel(QAbstractListModel):
    changed=Signal()
    sceneChanged=Signal()
    rejected=Signal(str)

    def __init__(self,payload=''):
        super().__init__()
        self.scene=parse_scene(payload)
        self.selected_index=0 if self.scene['layers'] else -1
        self.history=[];self.gesture=False

    def roleNames(self):return {Qt.UserRole+index+1:name.encode() for index,name in enumerate(ROLE_FIELDS)}
    def rowCount(self,parent=QModelIndex()):return 0 if parent.isValid() else len(self.scene['layers'])
    def data(self,index,role):
        if not index.isValid() or not 0<=index.row()<self.rowCount():return None
        position=role-Qt.UserRole-1
        if not 0<=position<len(ROLE_FIELDS):return None
        item=self.scene['layers'][index.row()]
        name=ROLE_FIELDS[position]
        if name=='title':return TITLES[item['metric']] if item['kind']=='metric' else {'text':'Text','media':'Image / GIF','arc':'Arc'}[item['kind']]
        key={'layerId':'id','px':'x','py':'y','pw':'width','ph':'height','shown':'visible'}.get(name,name)
        return item[key]

    @Property('QVariantMap',notify=changed)
    def selected(self):return dict(self.scene['layers'][self.selected_index]) if self.selected_index>=0 else {}
    @Property(int,notify=changed)
    def selectedIndex(self):return self.selected_index
    @Property(bool,notify=changed)
    def canUndo(self):return bool(self.history)
    def payload(self):return scene_json(self.scene)

    def remember(self):
        self.history.append(self.payload());self.history=self.history[-20:]

    @Slot(int)
    def select(self,index):
        if -1<=index<self.rowCount():self.selected_index=index;self.changed.emit()

    @Slot()
    def beginGesture(self):
        if not self.gesture:self.remember();self.gesture=True;self.changed.emit()
    @Slot()
    def endGesture(self):self.gesture=False

    def replace(self,scene,selected=None):
        parsed=parse_scene(scene_json(scene))
        if not self.gesture:self.remember()
        self.beginResetModel();self.scene=parsed
        self.selected_index=min(self.selected_index if selected is None else selected,len(parsed['layers'])-1)
        self.endResetModel();self.changed.emit();self.sceneChanged.emit()

    @Slot('QVariantMap')
    def updateSelected(self,values):
        if self.selected_index<0:return
        if set(values)-({'x','y','width','height','visible','color','size','weight','align','text','metric','label','opacity','font_path','animation','path'}):
            self.rejected.emit('Unknown composition fields');return
        values=dict(values)
        for key in ('x','y','width','height','size','weight'):
            value=values.get(key)
            if type(value) is float and math.isfinite(value) and value.is_integer():values[key]=int(value)
        items=[dict(item) for item in self.scene['layers']]
        items[self.selected_index].update(values)
        try:parsed=parse_scene(scene_json({'version':1,'layers':items}))
        except ValueError as error:self.rejected.emit(str(error));return
        if parsed==self.scene:return
        if not self.gesture:self.remember()
        self.scene=parsed
        index=self.index(self.selected_index,0)
        self.dataChanged.emit(index,index,list(self.roleNames()))
        self.changed.emit();self.sceneChanged.emit()

    @Slot(str,float,float)
    def moveLayer(self,identifier,x,y):
        if not math.isfinite(x) or not math.isfinite(y):return
        for index,item in enumerate(self.scene['layers']):
            if item['id']==identifier:
                if index!=self.selected_index:self.select(index)
                self.updateSelected({'x':max(0,min(240-item['width'],round(x))),'y':max(0,min(240-item['height'],round(y)))})
                return

    def add_layer(self,kind,path=None):
        identifiers={item['id'] for item in self.scene['layers']};number=1
        while 'layer-'+str(number) in identifiers:number+=1
        item=layer('layer-'+str(number),kind)
        if kind=='media':
            exists=any(value['kind']=='media' for value in self.scene['layers'])
            item.update(path=path,x=60 if exists else 0,y=60 if exists else 0,width=120 if exists else 240,height=120 if exists else 240)
        if kind=='arc':item.update(x=0,y=0,width=240,height=240,color='#73dfc1')
        items=list(self.scene['layers'])
        if kind in ('media','arc'):
            selected=max((index+1 for index,value in enumerate(items) if value['kind']=='media'),default=0)
            items.insert(selected,item)
        else:items.append(item);selected=len(items)-1
        try:self.replace({'version':1,'layers':items},selected)
        except ValueError as error:self.rejected.emit(str(error))

    @Slot(str)
    def add(self,kind):
        if kind in ('text','metric','arc'):self.add_layer(kind)

    @Slot()
    def removeSelected(self):
        if self.selected_index<0:return
        items=list(self.scene['layers']);items.pop(self.selected_index)
        self.replace({'version':1,'layers':items})

    @Slot(int)
    def reorder(self,direction):
        index=self.selected_index;target=index+direction
        if direction not in (-1,1) or index<0 or not 0<=target<self.rowCount():return
        items=list(self.scene['layers']);items[index],items[target]=items[target],items[index]
        self.replace({'version':1,'layers':items},target)

    @Slot()
    def undo(self):
        if not self.history:return
        payload=self.history.pop();self.beginResetModel();self.scene=parse_scene(payload)
        self.selected_index=min(self.selected_index,len(self.scene['layers'])-1)
        self.endResetModel();self.changed.emit();self.sceneChanged.emit()

    @Slot(bool)
    def resetComposition(self,blank):self.replace({'version':1,'layers':[]} if blank else default_scene(),-1 if blank else 0)
