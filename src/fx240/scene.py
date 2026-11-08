# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded declarative LCD scenes. No expressions, QML, URLs, or executable profiles."""
import json
import math
from collections import deque
from functools import lru_cache
from pathlib import Path
import re
from PIL import Image,ImageDraw
from .background import Background
from .focus import SCALE,accent_rgb,font,resolve_font,readings,temperature,frequency,round_arc,draw_active_arc
from .telemetry import collect
from .presets import EDITOR_EFFECTS, EFFECT_TITLES, draw_effect_base, draw_effect_motion, update_trace
from .protocol import validate_brightness

MAX_SCENE_BYTES=24576
METRICS=('cpu_temp','cpu_clock','gpu_temp','gpu_clock')
KINDS=('text','metric','media','arc','effect','gradient')
GRADIENT_DEFAULTS = {'color': '#1e6872', 'gradient_color': '#644e8b',
                     'gradient_style': 'aurora', 'gradient_angle': 0}
GRADIENT_FIELDS = set(GRADIENT_DEFAULTS) - {'color'}
DEFAULTS={'x':24,'y':80,'width':192,'height':40,'visible':True,'color':'#edf4f5',
          'size':24,'weight':350,'align':'center','text':'Text','metric':'cpu_temp','label':'',
          'path':None,'font_path':None,'opacity':1.0,'animation':'comet','rotation':0,'gif_pacing':'source','media_zoom':1.0,
          'effect':'halo','effect_style':'accent','vertical_align':'top','degree_only':False,'unit_suffix':False}


def layer(identifier,kind,**values):
    defaults = {**DEFAULTS, **GRADIENT_DEFAULTS} if kind == 'gradient' else DEFAULTS
    return {'id':identifier,'kind':kind,**defaults,**values}


def effect_layer(identifier, effect):
    _, color = EDITOR_EFFECTS[effect]
    geometry = dict(x=0, y=0, width=240, height=240, color=color)
    if effect == 'arc':
        return layer(identifier, 'arc', **geometry)
    return layer(identifier, 'effect', effect=effect, animation='signature', **geometry)


def default_scene():
    return {'version':1,'layers':[
        layer('layer-1','text',x=85,y=36,width=70,height=24,size=14,text='CPU',color='#a5b6bb'),
        layer('layer-2','metric',x=20,y=70,width=200,height=62,size=48),
        layer('layer-3','metric',x=55,y=134,width=130,height=28,size=18,metric='cpu_clock',color='#73dfc1'),
        layer('layer-4','metric',x=40,y=171,width=160,height=28,size=18,metric='gpu_temp',label='GPU'),
        layer('layer-5','metric',x=60,y=201,width=120,height=22,size=14,metric='gpu_clock',color='#a5b6bb')]}


def plain(value,limit):
    return isinstance(value,str) and len(value)<=limit and not any(ord(c)<32 for c in value)


def parse_scene(payload=''):
    try:
        if not isinstance(payload,str) or len(payload.encode('utf-8'))>MAX_SCENE_BYTES:
            raise ValueError('Composition exceeds the size limit')
        scene=json.loads(payload) if payload else default_scene()
        if not isinstance(scene,dict) or not {'version','layers'}<=set(scene) or set(scene)-{'version','layers','temperature_unit','temperature_decimals','motion_speed','lcd_brightness'} or type(scene['version']) is not int or scene['version']!=1:
            raise ValueError('Unsupported composition format')
        if not isinstance(scene['layers'],list) or len(scene['layers'])>16:
            raise ValueError('A composition supports at most 16 layers')
        unit=scene.get('temperature_unit','inherit')
        if unit not in ('inherit','C','F'):raise ValueError('Temperature unit must be C or F')
        if 'temperature_decimals' in scene:
            decimals = scene['temperature_decimals']
            if type(decimals) is not int or decimals not in (0, 1):
                raise ValueError('Invalid temperature precision')
        if 'motion_speed' in scene:
            speed = scene['motion_speed']
            if type(speed) not in (int, float) or not .25 <= speed <= 3:
                raise ValueError('Comet speed must be between 0.25 and 3')
        if 'lcd_brightness' in scene:
            validate_brightness(scene['lcd_brightness'])
        identifiers=set();counts={kind:0 for kind in KINDS};result=[]
        for item in scene['layers']:
            if not isinstance(item,dict) or set(item)-({'id','kind'}|GRADIENT_FIELDS|set(DEFAULTS)):
                raise ValueError('Unknown composition fields')
            identifier=item.get('id');kind=item.get('kind')
            if not isinstance(identifier,str) or re.fullmatch(r'[a-z][a-z0-9_-]{0,31}',identifier) is None or identifier in identifiers:
                raise ValueError('Invalid or duplicate layer identifier')
            if kind not in KINDS:raise ValueError('Unknown layer type')
            identifiers.add(identifier);counts[kind]+=1
            if kind == 'gradient':
                value = {**DEFAULTS, **GRADIENT_DEFAULTS, **item}
                accent_rgb(value['gradient_color'])
                angle = value['gradient_angle']
                if value['gradient_style'] not in ('aurora', 'linear', 'radial') or type(angle) is not int or not 0 <= angle < 360:
                    raise ValueError('Invalid gradient style or direction')
            else:
                if GRADIENT_FIELDS.intersection(item):
                    raise ValueError('Unknown composition fields')
                value = {**DEFAULTS, **item}
            for key,low,high in (('x',0,239),('y',0,239),('width',12,240),('height',12,240),('size',6,72),('weight',100,900),('rotation',0,359)):
                if type(value[key]) is not int or not low<=value[key]<=high:raise ValueError('Invalid layer dimensions or typography')
            if value['x']+value['width']>240 or value['y']+value['height']>240:
                raise ValueError('Layer bounds must fit the square canvas')
            if type(value['visible']) is not bool or value['align'] not in ('left','center','right'):
                raise ValueError('Invalid layer visibility or alignment')
            if value['gif_pacing'] not in ('source','smooth'):raise ValueError('Unknown GIF timing mode')
            zoom=value['media_zoom']
            if type(zoom) not in (float,int) or not math.isfinite(zoom) or not .25<=zoom<=4:
                raise ValueError('Layer zoom must be between 25% and 400%')
            if value['metric'] not in METRICS or value['animation'] not in ('comet','orbit','pulse','none','signature'):
                raise ValueError('Unknown metric or animation')
            if value['effect'] not in EFFECT_TITLES or value['effect_style'] not in ('accent','rainbow'):
                raise ValueError('Unknown metric or animation')
            if value['vertical_align'] not in ('top','center') or any(type(value[key]) is not bool for key in ('degree_only','unit_suffix')):
                raise ValueError('Invalid layer visibility or alignment')
            if not plain(value['text'],160) or not plain(value['label'],32):raise ValueError('Invalid layer text')
            accent_rgb(value['color'])
            opacity=value['opacity']
            if type(opacity) not in (float,int) or not math.isfinite(opacity) or not 0<=opacity<=1:raise ValueError('Invalid layer opacity')
            for key in ('path','font_path'):
                path=value[key]
                if path is not None and (not plain(path,4096) or not Path(path).is_absolute()):raise ValueError('Layer assets must be absolute local file paths')
            if kind=='media' and not value['path']:raise ValueError('Choose a local image or GIF')
            result.append(value)
        if counts['media']>2 or counts['arc']>2:raise ValueError('A composition supports at most two media and two arc layers')
        if counts['gradient'] > 1:
            raise ValueError('A composition supports one gradient layer')
        result={'version':1,'layers':result}
        if unit!='inherit':result['temperature_unit']=unit
        for key in ('temperature_decimals', 'motion_speed', 'lcd_brightness'):
            if key in scene:
                result[key] = scene[key]
        return result
    except (RecursionError,TypeError,KeyError,OverflowError) as error:
        raise ValueError('Invalid composition data') from error


def scene_json(scene):
    return json.dumps(scene,ensure_ascii=False,separators=(',',':'))


def zoom_surface(source, size, zoom):
    """Sample a centered viewport into the layer without a zoom-sized allocation."""
    cx, cy = source.width / 2, source.height / 2
    half_width, half_height = cx / zoom, cy / zoom
    return source.transform(size, Image.Transform.EXTENT,
                            (cx - half_width, cy - half_height, cx + half_width, cy + half_height),
                            Image.Resampling.BICUBIC, fillcolor=(0, 0, 0, 0))


def gradient_mask(sample):
    size = 96
    mask = Image.new('L', (size, size))
    coords = [(index + .5)/size - .5 for index in range(size)]
    mask.putdata([round(255 * max(0, min(1, sample(x, y)))) for y in coords for x in coords])
    return mask


@lru_cache(maxsize=12)
def gradient_masks(style, angle):
    if style == 'radial':
        return (gradient_mask(lambda x, y: math.hypot(x, y)/.49),)
    radians = math.radians(angle)
    c, s = math.cos(radians), math.sin(radians)
    if style == 'linear':
        return (gradient_mask(lambda x, y: .5 + c*x + s*y),)

    def glow(x, y):
        cx, cy = c*x - s*y, s*x + c*y
        return gradient_mask(lambda px, py: max(0, 1 - math.hypot(px-cx, py-cy)/.9)**1.5)

    return glow(-.31, .30), glow(.33, -.27)


def gradient_surface(item):
    """Build the gradient once per validated renderer configuration."""
    size = (item['width']*SCALE, item['height']*SCALE)
    style = item['gradient_style']
    colors = (item['color'], item['gradient_color'])
    if style == 'aurora':
        base = '#090d17'
    else:
        base, colors = colors[0], colors[1:]
    surface = Image.new('RGB', size, base)
    angle = item['gradient_angle'] if style != 'radial' else 0
    for color, mask in zip(colors, gradient_masks(style, angle)):
        mask = mask.resize(size, Image.Resampling.BILINEAR)
        surface.paste(accent_rgb(color), (0, 0, *size), mask)
    surface.putalpha(round(255*item['opacity']))
    if item['media_zoom'] != 1:
        surface = zoom_surface(surface, size, item['media_zoom'])
    return surface


class SceneRenderer:
    def __init__(self,fps=24,provider=None,font_path=None,temperature_decimals=1,temperature_unit='C',scene_json='',comet_speed=1.0,**kwargs):
        self.scene=parse_scene(scene_json)
        self.fps=fps;self.provider=provider if provider is not None else collect
        self.temperature_decimals=self.scene.get('temperature_decimals', temperature_decimals)
        self.temperature_unit=self.scene.get('temperature_unit',temperature_unit)
        self.comet_speed=self.scene.get('motion_speed', comet_speed);self.comet_offset=0
        self.sampled_at=None;self.values=(None,)*4
        self.assets={};self.fonts={};self.gradients={}
        self.history = deque(maxlen=60)
        self.trace = []
        self.has_trace = any(item['kind']=='effect' and item['effect']=='trace' for item in self.scene['layers'])
        resolved={}
        try:
            for item in self.scene['layers']:
                if not item['visible']:continue
                if item['kind']=='media':self.assets[item['id']]=Background(item['path'],0,pacing_fps=self.fps if item['gif_pacing']=='smooth' else None)
                elif item['kind'] == 'gradient':
                    self.gradients[item['id']] = gradient_surface(item)
                elif item['kind'] in ('text','metric'):
                    source=item['font_path'] or font_path
                    if source not in resolved:resolved[source]=resolve_font(source)
                    self.fonts[item['id']]=resolved[source]
        except Exception:
            self.close();raise

    def close(self):
        for asset in self.assets.values():asset.close()
        self.assets.clear()
        self.gradients.clear()

    def sample(self,elapsed):
        self.values=readings(self.provider());self.sampled_at=elapsed
        if self.has_trace:
            self.trace = update_trace(self.history, elapsed, self.values[0])

    def comet_time(self,elapsed):return elapsed*self.comet_speed+self.comet_offset
    def arc_value(self,elapsed):return 0 if self.values[0] is None else max(0,min(1,self.values[0]/100))
    def inherit_motion(self,other,elapsed):
        self.comet_offset=other.comet_time(elapsed)-elapsed*self.comet_speed
        if self.has_trace:
            self.history.extend(getattr(other, 'history', ()))

    def text_value(self,item):
        if item['kind']=='text':
            return item['text'] + ('°' + self.temperature_unit if item['unit_suffix'] else '')
        index=METRICS.index(item['metric']);value=self.values[index]
        suffix = '°' if item['degree_only'] else '°' + self.temperature_unit
        text=temperature(value,self.temperature_decimals,self.temperature_unit)+suffix if index in (0,2) and value is not None else frequency(value) if index in (1,3) else 'N/A'
        return (item['label']+' ' if item['label'] else '')+text

    def __call__(self,elapsed):
        if self.sampled_at is None or elapsed<self.sampled_at or elapsed-self.sampled_at>=1:self.sample(elapsed)
        canvas=Image.new('RGB',(240*SCALE,240*SCALE),'black')
        for item in self.scene['layers']:
            if not item['visible']:continue
            size=(item['width']*SCALE,item['height']*SCALE)
            zoom = item['media_zoom']  # Keep the stored field name for existing profiles.
            if item['kind']=='media':
                source=self.assets[item['id']].frame(elapsed)
                if zoom==1:
                    surface=source.resize(size,Image.Resampling.LANCZOS).convert('RGBA')
                else:
                    surface=zoom_surface(source.convert('RGBA'),size,zoom)
            elif item['kind']=='gradient':
                surface = self.gradients[item['id']]
            elif item['kind']=='arc':
                surface=Image.new('RGB',(240*SCALE,240*SCALE),'black')
                round_arc(ImageDraw.Draw(surface),135,405,(28,42,46))
                progress=self.arc_value(elapsed)
                if progress>0:draw_active_arc(surface,self.comet_time(elapsed),progress,accent_rgb(item['color']),item['effect_style'],item['animation'])
                mask=Image.new('L',surface.size);round_arc(ImageDraw.Draw(mask),135,405,255)
                surface=surface.convert('RGBA');surface.putalpha(mask)
            elif item['kind']=='effect':
                surface = Image.new('RGBA', (240 * SCALE, 240 * SCALE))
                draw = ImageDraw.Draw(surface)
                color = accent_rgb(item['color'])
                draw_effect_base(draw, item['effect'], color, self.trace)
                if item['animation'] != 'none':
                    draw_effect_motion(draw, item['effect'], color, self.comet_time(elapsed),
                                       item['effect_style'], self.trace)
            else:
                surface=Image.new('RGBA',size)
                face=font(self.fonts[item['id']],item['size'],item['weight']);text=self.text_value(item)
                if item['vertical_align'] == 'center':
                    font_size = item['size']
                    while font_size > 6 and face.getlength(text) > size[0]:
                        font_size -= 1
                        face = font(self.fonts[item['id']],font_size,item['weight'])
                    x, anchor = {'left':(0,'lm'), 'center':(size[0]/2,'mm'), 'right':(size[0],'rm')}[item['align']]
                    ImageDraw.Draw(surface).text((x,size[1]/2),text,font=face,fill=item['color'],anchor=anchor)
                else:
                    box=face.getbbox(text,anchor='lt');width=box[2]-box[0]
                    left=0 if item['align']=='left' else size[0]-width if item['align']=='right' else (size[0]-width)/2
                    ImageDraw.Draw(surface).text((left-box[0],-box[1]),text,font=face,fill=item['color'],anchor='lt')
            if item['kind'] not in ('media', 'gradient'):
                if zoom != 1:
                    surface = zoom_surface(surface, size, zoom)
                elif surface.size != size:
                    surface = surface.resize(size, Image.Resampling.LANCZOS)
            if item['kind'] != 'gradient' and item['opacity']!=1:surface.putalpha(surface.getchannel('A').point(lambda value:round(value*item['opacity'])))
            left=item['x']*SCALE;top=item['y']*SCALE
            if item['rotation']:
                # Clockwise about the layer center, with transparent expansion.
                # Geometry stays in LCD pixels; final canvas/circle clips overflow.
                surface=surface.rotate(-item['rotation'],resample=Image.Resampling.BICUBIC,expand=True)
                left-=(surface.width-size[0])//2;top-=(surface.height-size[1])//2
            canvas.paste(surface,(left,top),surface)
        return canvas.resize((240,240),Image.Resampling.LANCZOS),1/self.fps
