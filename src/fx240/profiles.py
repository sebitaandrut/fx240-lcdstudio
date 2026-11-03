# SPDX-License-Identifier: GPL-3.0-or-later
"""Private local profile library. Names are metadata, never filesystem paths."""
import json
import os
from pathlib import Path
import re
import tempfile
from .localfiles import read_regular,config_home
from .scene import parse_scene,scene_json,plain

MAX_LIBRARY_BYTES=256*1024
MAX_PROFILES=8


def validate_library(data):
    if not isinstance(data,dict) or set(data)!={'version','profiles'} or type(data['version']) is not int or data['version']!=1:
        raise ValueError('Unsupported profile library format')
    if not isinstance(data['profiles'],list) or len(data['profiles'])>MAX_PROFILES:
        raise ValueError('The library supports at most eight profiles')
    identifiers=set();names=set();result=[]
    for item in data['profiles']:
        if not isinstance(item,dict) or set(item)!={'id','name','scene'}:raise ValueError('Invalid profile entry')
        identifier=item['id'];name=item['name']
        if not isinstance(identifier,str) or re.fullmatch(r'profile-[1-9][0-9]{0,6}',identifier) is None or identifier in identifiers:
            raise ValueError('Invalid or duplicate profile identifier')
        if not plain(name,32) or not name.strip() or name!=name.strip() or name.casefold() in names|{'focus'}:
            raise ValueError('Choose a unique profile name with 1 to 32 characters')
        parsed=parse_scene(item['scene']);identifiers.add(identifier);names.add(name.casefold())
        result.append({'id':identifier,'name':name,'scene':scene_json(parsed)})
    return {'version':1,'profiles':result}


class ProfileStore:
    def __init__(self,path=None,*,memory=False):
        base=config_home()
        self.path=Path(path) if path else base/'fx240-linux/profiles.json'
        self.profiles=[];self.error='';self.memory=memory
        if memory:return
        try:
            payload=read_regular(self.path,MAX_LIBRARY_BYTES,private=True)
            self.profiles=validate_library(json.loads(payload))['profiles']
        except FileNotFoundError:pass
        except (OSError,ValueError,TypeError,RecursionError):
            self.error='Profile library could not be read; the existing file was preserved'

    def get(self,identifier):return next((dict(item) for item in self.profiles if item['id']==identifier),None)

    def _write(self,profiles):
        if self.error:raise ValueError(self.error)
        data=validate_library({'version':1,'profiles':profiles})
        text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
        if len(text.encode('utf-8'))>MAX_LIBRARY_BYTES:raise ValueError('Profile library exceeds the size limit')
        if self.memory:
            self.profiles=data['profiles'];return
        self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=self.path.parent,delete=False) as stream:
                temporary=stream.name;stream.write(text);stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,self.path)
            self.profiles=data['profiles']
        finally:
            if temporary and Path(temporary).exists():Path(temporary).unlink()

    def save(self,name,payload,identifier=None):
        if not isinstance(name,str):raise ValueError('Choose a unique profile name with 1 to 32 characters')
        name=name.strip();payload=scene_json(parse_scene(payload))
        items=[dict(item) for item in self.profiles]
        if identifier is not None and self.get(identifier) is None:raise ValueError('Profile no longer exists')
        if identifier is None:
            number=1
            while self.get('profile-'+str(number)):number+=1
            identifier='profile-'+str(number)
            items.append({'id':identifier,'name':name,'scene':payload})
        else:
            items=[{'id':identifier,'name':name,'scene':payload} if item['id']==identifier else item for item in items]
        self._write(items)
        return identifier

    def delete(self,identifier):
        if self.get(identifier) is None:raise ValueError('Profile no longer exists')
        self._write([item for item in self.profiles if item['id']!=identifier])
