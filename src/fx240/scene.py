# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded declarative LCD scenes. No expressions, QML, URLs, or executable profiles."""
import json
import math
from pathlib import Path
import re
from PIL import Image,ImageDraw
from .background import Background
from .focus import SCALE,accent_rgb,font,resolve_font,readings,temperature,frequency,round_arc,draw_active_arc
from .telemetry import collect

MAX_SCENE_BYTES=24576
METRICS=('cpu_temp','cpu_clock','gpu_temp','gpu_clock')
KINDS=('text','metric','media','arc')
DEFAULTS={'x':24,'y':80,'width':192,'height':40,'visible':True,'color':'#edf4f5',
          'size':24,'weight':350,'align':'center','text':'Text','metric':'cpu_temp','label':'',
          'path':None,'font_path':None,'opacity':1.0,'animation':'comet'}


def layer(identifier,kind,**values):
    return {'id':identifier,'kind':kind,**DEFAULTS,**values}


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
        if not isinstance(scene,dict) or set(scene)!={'version','layers'} or type(scene['version']) is not int or scene['version']!=1:
            raise ValueError('Unsupported composition format')
        if not isinstance(scene['layers'],list) or len(scene['layers'])>16:
            raise ValueError('A composition supports at most 16 layers')
        identifiers=set();counts={kind:0 for kind in KINDS};result=[]
        for item in scene['layers']:
            if not isinstance(item,dict) or set(item)-({'id','kind'}|set(DEFAULTS)):
                raise ValueError('Unknown composition fields')
            identifier=item.get('id');kind=item.get('kind')
            if not isinstance(identifier,str) or re.fullmatch(r'[a-z][a-z0-9_-]{0,31}',identifier) is None or identifier in identifiers:
                raise ValueError('Invalid or duplicate layer identifier')
            if kind not in KINDS:raise ValueError('Unknown layer type')
            identifiers.add(identifier);counts[kind]+=1
            value={**DEFAULTS,**item}
            for key,low,high in (('x',0,239),('y',0,239),('width',12,240),('height',12,240),('size',6,72),('weight',100,900)):
                if type(value[key]) is not int or not low<=value[key]<=high:raise ValueError('Invalid layer dimensions or typography')
            if value['x']+value['width']>240 or value['y']+value['height']>240:
                raise ValueError('Layer bounds must fit the square canvas')
            if type(value['visible']) is not bool or value['align'] not in ('left','center','right'):
                raise ValueError('Invalid layer visibility or alignment')
            if value['metric'] not in METRICS or value['animation'] not in ('comet','orbit','pulse','none'):
                raise ValueError('Unknown metric or animation')
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
        return {'version':1,'layers':result}
    except (RecursionError,TypeError,KeyError,OverflowError) as error:
        raise ValueError('Invalid composition data') from error


def scene_json(scene):
    return json.dumps(scene,ensure_ascii=False,separators=(',',':'))


class SceneRenderer:
    def __init__(self,fps=24,provider=None,font_path=None,temperature_decimals=1,temperature_unit='C',scene_json='',comet_speed=1.0,**kwargs):
        self.scene=parse_scene(scene_json)
        self.fps=fps;self.provider=provider if provider is not None else collect
        self.temperature_decimals=temperature_decimals;self.temperature_unit=temperature_unit
        self.comet_speed=comet_speed;self.comet_offset=0
        self.sampled_at=None;self.values=(None,)*4
        self.assets={};self.fonts={}
        resolved={}
        for item in self.scene['layers']:
            if not item['visible']:continue
            if item['kind']=='media':self.assets[item['id']]=Background(item['path'],0)
            elif item['kind'] in ('text','metric'):
                source=item['font_path'] or font_path
                if source not in resolved:resolved[source]=resolve_font(source)
                self.fonts[item['id']]=resolved[source]

    def sample(self,elapsed):
        self.values=readings(self.provider());self.sampled_at=elapsed

    def comet_time(self,elapsed):return elapsed*self.comet_speed+self.comet_offset
    def arc_value(self,elapsed):return 0 if self.values[0] is None else max(0,min(1,self.values[0]/100))
    def inherit_motion(self,other,elapsed):self.comet_offset=other.comet_time(elapsed)-elapsed*self.comet_speed

    def text_value(self,item):
        if item['kind']=='text':return item['text']
        index=METRICS.index(item['metric']);value=self.values[index]
        text=temperature(value,self.temperature_decimals,self.temperature_unit)+'°'+self.temperature_unit if index in (0,2) and value is not None else frequency(value) if index in (1,3) else 'N/A'
        return (item['label']+' ' if item['label'] else '')+text

    def __call__(self,elapsed):
        if self.sampled_at is None or elapsed<self.sampled_at or elapsed-self.sampled_at>=1:self.sample(elapsed)
        canvas=Image.new('RGB',(240*SCALE,240*SCALE),'black')
        for item in self.scene['layers']:
            if not item['visible']:continue
            size=(item['width']*SCALE,item['height']*SCALE)
            if item['kind']=='media':
                surface=self.assets[item['id']].frame(elapsed).resize(size,Image.Resampling.LANCZOS).convert('RGBA')
            elif item['kind']=='arc':
                surface=Image.new('RGB',(240*SCALE,240*SCALE),'black')
                round_arc(ImageDraw.Draw(surface),135,405,(28,42,46))
                progress=self.arc_value(elapsed)
                if progress>0:draw_active_arc(surface,self.comet_time(elapsed),progress,accent_rgb(item['color']),'accent',item['animation'])
                mask=Image.new('L',surface.size);round_arc(ImageDraw.Draw(mask),135,405,255)
                surface=surface.convert('RGBA');surface.putalpha(mask);surface=surface.resize(size,Image.Resampling.LANCZOS)
            else:
                surface=Image.new('RGBA',size)
                face=font(self.fonts[item['id']],item['size'],item['weight']);text=self.text_value(item)
                box=face.getbbox(text,anchor='lt');width=box[2]-box[0]
                left=0 if item['align']=='left' else size[0]-width if item['align']=='right' else (size[0]-width)/2
                ImageDraw.Draw(surface).text((left-box[0],-box[1]),text,font=face,fill=item['color'],anchor='lt')
            if item['opacity']!=1:surface.putalpha(surface.getchannel('A').point(lambda value:round(value*item['opacity'])))
            canvas.paste(surface,(item['x']*SCALE,item['y']*SCALE),surface)
        return canvas.resize((240,240),Image.Resampling.LANCZOS),1/self.fps
