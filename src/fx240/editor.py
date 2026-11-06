# SPDX-License-Identifier: GPL-3.0-or-later
"""Qt scene model. Roles expose geometry/titles, never asset paths or scripts."""
from PySide6.QtCore import QAbstractListModel,QModelIndex,Qt,Property,Signal,Slot
import math
from .scene import parse_scene,scene_json,layer,default_scene,effect_layer
from .presets import EDITOR_EFFECTS, EFFECT_TITLES

TITLES={'cpu_temp':'CPU temperature','cpu_clock':'CPU frequency','gpu_temp':'GPU temperature','gpu_clock':'GPU frequency'}
ROLE_FIELDS=('layerId','kind','px','py','pw','ph','shown','title','angle','marked')


class EditorModel(QAbstractListModel):
    changed=Signal()
    sceneChanged=Signal()
    rejected=Signal(str)

    def __init__(self,payload=''):
        super().__init__()
        self.scene=parse_scene(payload)
        self.selected_index=0 if self.scene['layers'] else -1
        self.selection = {self.selected_index} if self.selected_index >= 0 else set()
        self.history = []
        self.gesture = False
        self._gesture_start = None
        self._gesture_layers = {}

    def roleNames(self):return {Qt.UserRole+index+1:name.encode() for index,name in enumerate(ROLE_FIELDS)}
    def rowCount(self,parent=QModelIndex()):return 0 if parent.isValid() else len(self.scene['layers'])
    def data(self,index,role):
        if not index.isValid() or not 0<=index.row()<self.rowCount():return None
        position=role-Qt.UserRole-1
        if not 0<=position<len(ROLE_FIELDS):return None
        item=self.scene['layers'][index.row()]
        name=ROLE_FIELDS[position]
        if name == 'marked':
            return index.row() in self.selection
        if name=='title':
            if item['kind']=='effect':
                return EFFECT_TITLES[item['effect']]
            return TITLES[item['metric']] if item['kind']=='metric' else {'text':'Text','media':'Image / GIF','arc':'Arc','gradient':'Gradient'}[item['kind']]
        key={'layerId':'id','px':'x','py':'y','pw':'width','ph':'height','shown':'visible','angle':'rotation'}.get(name,name)
        return item[key]

    @Property('QVariantMap',notify=changed)
    def selected(self):return dict(self.scene['layers'][self.selected_index]) if self.selected_index>=0 else {}
    @Property(int,notify=changed)
    def selectedIndex(self):return self.selected_index
    @Property(bool,notify=changed)
    def canUndo(self):return bool(self.history)
    def payload(self):return scene_json(self.scene)

    @Property(int, notify=changed)
    def selectionCount(self):
        return len(self.selection)

    @Property(bool, notify=changed)
    def selectionHasColor(self):
        return any(self.scene['layers'][index]['kind'] != 'media' for index in self.selection)

    @staticmethod
    def bounds(items):
        x = min(item['x'] for item in items)
        y = min(item['y'] for item in items)
        right = max(item['x'] + item['width'] for item in items)
        bottom = max(item['y'] + item['height'] for item in items)
        return dict(x=x, y=y, width=right - x, height=bottom - y)

    @Property('QVariantMap', notify=changed)
    def selectionBounds(self):
        return self.bounds([self.scene['layers'][index] for index in self.selection]) if self.selection else {}

    def snapshot(self):
        return self.payload(), self.selected_index, self.selection.copy()

    def remember(self):
        if self.gesture and self._gesture_start is None:
            return
        self.history.append(self._gesture_start if self.gesture else self.snapshot())
        self.history = self.history[-20:]
        if self.gesture:
            self._gesture_start = None

    def set_selection(self, indices, primary):
        if indices == self.selection and primary == self.selected_index:
            return
        affected = indices ^ self.selection
        self.selection = indices
        self.selected_index = primary
        self.notify_rows(affected, [Qt.UserRole + len(ROLE_FIELDS)])
        self.changed.emit()

    def notify_rows(self, indices, roles):
        for row in sorted(indices):
            index = self.index(row, 0)
            self.dataChanged.emit(index, index, roles)

    @Slot(int)
    def select(self,index):
        if -1 <= index < self.rowCount():
            self.set_selection({index} if index >= 0 else set(), index)

    @Slot(int)
    def toggleSelection(self, index):
        if not 0 <= index < self.rowCount():
            return
        indices = self.selection ^ {index}
        primary = index if index in indices else self.selected_index
        if primary not in indices:
            primary = min(indices, default=-1)
        self.set_selection(indices, primary)

    @Slot(int)
    def selectForDrag(self, index):
        if index not in self.selection:
            self.select(index)

    @Slot()
    def beginGesture(self):
        if not self.gesture:
            self._gesture_start = self.snapshot()
            self._gesture_layers = {index: self.scene['layers'][index] for index in self.selection}
            self.gesture = True

    @Slot()
    def endGesture(self):
        self.gesture = False
        self._gesture_start = None
        self._gesture_layers = {}

    def reset_model(self, scene, primary, indices):
        self.beginResetModel()
        self.scene = scene
        self.selected_index = primary
        self.selection = indices
        self.endResetModel()
        self.changed.emit()
        self.sceneChanged.emit()

    def replace(self,scene,selected=None):
        parsed=parse_scene(scene_json(scene))
        self.endGesture()
        self.remember()
        primary = min(self.selected_index if selected is None else selected, len(parsed['layers']) - 1)
        self.reset_model(parsed, primary, {primary} if primary >= 0 else set())

    def apply_updates(self, updates):
        if not updates:
            return
        items = list(self.scene['layers'])
        for index, values in updates.items():
            items[index] = {**items[index], **values}
        try:
            parsed = parse_scene(scene_json({**self.scene, 'layers': items}))
        except ValueError as error:
            self.rejected.emit(str(error))
            return
        if parsed == self.scene:
            return
        self.remember()
        self.scene = parsed
        self.notify_rows(updates, list(self.roleNames()))
        self.changed.emit()
        self.sceneChanged.emit()

    @Slot('QVariantMap')
    def updateSelected(self,values):
        if self.selected_index<0:return
        if set(values)-({'x','y','width','height','visible','color','size','weight','align','text','metric','label','opacity','font_path','animation','path','rotation','gif_pacing','media_zoom','effect_style','gradient_color','gradient_style','gradient_angle'}):
            self.rejected.emit('Unknown composition fields');return
        values=dict(values)
        for key in ('x','y','width','height','size','weight','rotation','gradient_angle'):
            value=values.get(key)
            if type(value) is float and math.isfinite(value) and value.is_integer():values[key]=int(value)
        self.apply_updates({self.selected_index: values})

    @Slot('QVariantMap')
    def updateSelectionStyle(self, values):
        if set(values) - {'visible', 'color', 'opacity'}:
            return
        self.apply_updates({
            index: {key: value for key, value in values.items() if key != 'color' or self.scene['layers'][index]['kind'] != 'media'}
            for index in self.selection
        })

    @Slot(float, float)
    def moveSelection(self, dx, dy):
        if not self.gesture or not self._gesture_layers or not all(map(math.isfinite, (dx, dy))):
            return
        bounds = self.bounds(self._gesture_layers.values())
        dx = max(-bounds['x'], min(240 - bounds['x'] - bounds['width'], round(dx)))
        dy = max(-bounds['y'], min(240 - bounds['y'] - bounds['height'], round(dy)))
        self.apply_updates({index: dict(x=item['x'] + dx, y=item['y'] + dy)
                            for index, item in self._gesture_layers.items()})

    @Slot(float)
    def scaleSelection(self, scale):
        if not self.gesture or not self._gesture_layers or not math.isfinite(scale):
            return
        bounds = self.bounds(self._gesture_layers.values())
        x, y = bounds['x'], bounds['y']
        maximum = min((240 - x) / bounds['width'], (240 - y) / bounds['height'])
        minimum = max(12 / min(item['width'], item['height']) for item in self._gesture_layers.values())
        scale = max(minimum, min(maximum, scale))
        updates = {}
        for index, item in self._gesture_layers.items():
            left = x + round((item['x'] - x) * scale)
            top = y + round((item['y'] - y) * scale)
            right = x + round((item['x'] + item['width'] - x) * scale)
            bottom = y + round((item['y'] + item['height'] - y) * scale)
            updates[index] = dict(x=left, y=top, width=max(12, right - left), height=max(12, bottom - top))
            if item['kind'] in ('text', 'metric'):
                updates[index]['size'] = max(6, min(72, round(item['size'] * scale)))
        self.apply_updates(updates)

    @Slot(int)
    def rotateSelection(self, degrees):
        if not self.selection:
            return
        if len(self.selection) == 1:
            self.updateSelected({'rotation': (self.selected['rotation'] + degrees) % 360})
            return
        bounds = self.selectionBounds
        cx = bounds['x'] + bounds['width'] / 2
        cy = bounds['y'] + bounds['height'] / 2
        angle = math.radians(degrees % 360)
        c, s = math.cos(angle), math.sin(angle)
        updates = {}
        for index in self.selection:
            item = self.scene['layers'][index]
            dx = item['x'] + item['width'] / 2 - cx
            dy = item['y'] + item['height'] / 2 - cy
            updates[index] = dict(x=round(cx + c * dx - s * dy - item['width'] / 2),
                                  y=round(cy + s * dx + c * dy - item['height'] / 2),
                                  width=item['width'], height=item['height'],
                                  rotation=(item['rotation'] + degrees) % 360)
        rotated = self.bounds(updates.values())
        if rotated['width'] > 240 or rotated['height'] > 240:
            self.rejected.emit('The rotated selection does not fit the canvas')
            return
        dx = max(-rotated['x'], min(0, 240 - rotated['x'] - rotated['width']))
        dy = max(-rotated['y'], min(0, 240 - rotated['y'] - rotated['height']))
        for item in updates.values():
            item['x'] += dx
            item['y'] += dy
        self.apply_updates(updates)

    @Property('QVariantList', constant=True)
    def effectCatalog(self):
        return [{'key': key, 'label': label} for key, (label, _) in EDITOR_EFFECTS.items()]

    def add_layer(self,kind,path=None,*,effect=None):
        items=list(self.scene['layers'])
        if kind == 'gradient':
            for index, existing in enumerate(items):
                if existing['kind'] == 'gradient':
                    self.select(index)
                    return
        identifiers={item['id'] for item in self.scene['layers']};number=1
        while 'layer-'+str(number) in identifiers:number+=1
        identifier='layer-'+str(number)
        item=effect_layer(identifier,effect) if effect else layer(identifier,kind)
        if kind=='media':
            exists=any(value['kind']=='media' for value in self.scene['layers'])
            item.update(path=path,x=60 if exists else 0,y=60 if exists else 0,width=120 if exists else 240,height=120 if exists else 240)
        if kind == 'gradient':
            item.update(x=0, y=0, width=240, height=240)
        if kind in ('media','gradient'):
            selected = max((index+1 for index, value in enumerate(items)
                            if value['kind'] in ('media', 'gradient')
                            or (value['kind'] == 'effect' and value['effect'] == 'disc')), default=0)
            items.insert(selected,item)
        elif effect:
            selected = next((index for index, value in enumerate(items)
                             if value['kind'] in ('text', 'metric')), len(items))
            items.insert(selected, item)
        else:items.append(item);selected=len(items)-1
        try:self.replace({**self.scene,'layers':items},selected)
        except ValueError as error:self.rejected.emit(str(error))

    @Slot(str)
    def add(self,kind):
        if kind in ('text','metric','gradient'):self.add_layer(kind)

    @Slot(str)
    def addEffect(self, effect):
        if effect in EDITOR_EFFECTS:
            self.add_layer('effect', effect=effect)

    @Slot()
    def removeSelected(self):
        if self.selected_index<0:return
        items = [item for index, item in enumerate(self.scene['layers']) if index not in self.selection]
        self.replace({**self.scene, 'layers': items}, min(self.selection))

    @Slot(int)
    def reorder(self,direction):
        index=self.selected_index;target=index+direction
        if len(self.selection) != 1 or direction not in (-1,1) or index<0 or not 0<=target<self.rowCount():return
        items=list(self.scene['layers']);items[index],items[target]=items[target],items[index]
        self.replace({**self.scene,'layers':items},target)

    @Slot()
    def undo(self):
        if not self.history:return
        self.endGesture()
        payload, primary, indices = self.history.pop()
        self.reset_model(parse_scene(payload), primary, indices)

    @Property(str,notify=changed)
    def temperatureUnit(self):return self.scene.get('temperature_unit','inherit')

    def update_composition(self, **values):
        try:
            scene = parse_scene(scene_json({**self.scene, **values}))
        except ValueError as error:
            self.rejected.emit(str(error))
            return
        if scene != self.scene:
            self.remember()
            self.scene = scene
            self.changed.emit()
            self.sceneChanged.emit()

    @Slot(int)
    def setTemperatureDecimals(self, decimals):
        self.update_composition(temperature_decimals=decimals)

    @Slot(float)
    def setMotionSpeed(self, speed):
        self.update_composition(motion_speed=speed)

    @Slot(str)
    def setTemperatureUnit(self,unit):
        if unit not in ('inherit','C','F'):
            self.rejected.emit('Temperature unit must be C or F');return
        scene=dict(self.scene)
        if unit=='inherit':scene.pop('temperature_unit',None)
        else:scene['temperature_unit']=unit
        if scene==self.scene:return
        self.remember();self.scene=scene;self.changed.emit();self.sceneChanged.emit()

    @Slot(bool)
    def resetComposition(self,blank):
        self.replace({**self.scene,'layers':[] if blank else default_scene()['layers']},-1 if blank else 0)
