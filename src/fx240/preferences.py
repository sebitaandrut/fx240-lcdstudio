# SPDX-License-Identifier: GPL-3.0-or-later
"""Private, versioned desktop preferences. No device path or output state is saved."""
from dataclasses import asdict,replace,fields
import json
import os
from pathlib import Path
import tempfile
from .session import Settings
from .localfiles import read_regular,config_home


MAX_PREFERENCE_BYTES = 64 * 1024


class Preferences:
    def __init__(self,path=None):
        base=config_home()
        self.path=Path(path) if path else Path(base)/'fx240-linux/settings.json'
        self.warning=''
        self.issues=[]
        self.load_error=''

    def load(self):
        self.warning=''
        self.issues=[]
        self.load_error=''
        defaults=Settings()
        ui={'language':'es','theme':'dark'}
        try:
            payload=read_regular(self.path,MAX_PREFERENCE_BYTES,private=True)
            data=json.loads(payload)
            if not isinstance(data,dict) or data.get('version')!=1:
                raise ValueError('Unsupported preferences format')
            values=data.get('display',{})
            if not isinstance(values,dict):raise ValueError('Invalid display preferences')
            # Validate incrementally so one damaged field does not discard all preferences.
            types={field.name:field.type for field in fields(Settings)}
            for key,value in values.items():
                if key=='device' or key not in asdict(defaults):continue
                if types[key] is int:
                    valid_type=isinstance(value,int) and not isinstance(value,bool)
                elif types[key] is float:
                    valid_type=isinstance(value,(int,float)) and not isinstance(value,bool)
                else:
                    valid_type=isinstance(value,str) or (value is None and key in ('font_path','background_path'))
                try:
                    if not valid_type:
                        expected='Expected a whole number' if types[key] is int else 'Expected a number' if types[key] is float else 'Expected text or an empty font selection'
                        raise ValueError(expected)
                    candidate=replace(defaults,**{key:value});candidate.validate()
                    if key=='font_path' and value:
                        from .focus import resolve_font
                        resolve_font(value)
                    if key=='background_path' and value:
                        from .background import Background
                        Background(value)
                    defaults=candidate
                except (ValueError,TypeError,OSError) as error:
                    self.issues.append({'field':key,'reason':str(error),'fallback':getattr(defaults,key)})
                    self.warning='Some saved preferences were invalid and have been reset'
            saved_ui=data.get('application',{})
            if isinstance(saved_ui,dict):
                for key,allowed in (('language',('en','es')),('theme',('dark','light'))):
                    if key not in saved_ui:continue
                    if saved_ui[key] in allowed:ui[key]=saved_ui[key]
                    else:
                        self.issues.append({'field':key,'reason':'Unsupported selection','fallback':ui[key]})
                        self.warning='Some saved preferences were invalid and have been reset'
        except FileNotFoundError:
            pass
        except (OSError,ValueError,TypeError,RecursionError) as error:
            self.load_error=str(error)
            self.warning='Saved preferences could not be loaded; defaults are in use'
        return defaults,ui

    def save(self,settings,language,theme):
        settings.validate()
        if language not in ('en','es') or theme not in ('dark','light'):
            raise ValueError('Invalid application preferences')
        values=asdict(settings);values.pop('device',None)
        if settings.profile_id:values.pop('scene_json',None)
        payload={'version':1,'application':{'language':language,'theme':theme},'display':values}
        serialized=json.dumps(payload,indent=2,ensure_ascii=False)+'\n'
        if len(serialized.encode('utf-8'))>MAX_PREFERENCE_BYTES:
            raise ValueError('Saved preferences exceed the 64 KiB limit')
        self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        name=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=self.path.parent,delete=False) as file:
                name=file.name
                file.write(serialized);file.flush();os.fsync(file.fileno())
            os.replace(name,self.path)
        finally:
            if name and Path(name).exists():Path(name).unlink()
