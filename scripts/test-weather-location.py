#!/usr/bin/env python3
"""Requested-city regression against the exact pinned Weather methods."""
import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types
from unittest.mock import Mock,patch
import zipfile
import weather_boundary as boundary

assert os.getuid()!=0, 'Run as the ordinary user'
root=Path(__file__).resolve().parents[1]
logger=Mock()
class Fixture:
    def _get_intent_data(self,message):return message
    def _get_weather(self,intent):return intent.config
    def _display_current_conditions(self,*args):pass
    def _speak_weather(self,*args):pass

def exercise(cls,module):
    home={'location':{'coordinate':{'latitude':1,'longitude':2},
                      'timezone':{'code':'UTC'},'city':{'name':'Home'}}}
    original=deepcopy(home)
    skill=cls()
    for location,latitude,longitude,timezone in (
            ('Sydney',-33.87,151.21,'Australia/Sydney'),
            ('New York',40.71,-74.01,'America/New_York')):
        config=types.SimpleNamespace(core_config=deepcopy(home),settings={'units':'metric'})
        intent=types.SimpleNamespace(location=location,config=config,
            geolocation={'latitude':latitude,'longitude':longitude,'timezone':timezone},
            intent_datetime=0,location_datetime=0,utterance='weather')
        module.WeatherIntent=lambda *args:intent
        message=types.SimpleNamespace(data={'utterance':'weather'})
        # The generic fixture returns the intent directly; the pinned method
        # builds it from the message and its actual config handling.
        result=skill._get_intent_data(intent if cls is Fixture else message)
        assert result.config is not config and config.core_config==original
        assert result.config.core_config['location']['coordinate']=={
            'latitude':latitude,'longitude':longitude}
        assert result.config.core_config['location']['timezone']['code']==timezone
        report=skill._get_weather(result)
        assert report.core_config['location']['coordinate']['latitude']==latitude
        assert result.config.settings=={'units':'metric'}
    local=types.SimpleNamespace(location=None,config=types.SimpleNamespace(core_config=home),
        intent_datetime=0,location_datetime=0,utterance='weather')
    module.WeatherIntent=lambda *args:local
    result=skill._get_intent_data(local if cls is Fixture else message)
    assert result.config is local.config and home==original

with tempfile.TemporaryDirectory() as folder:
    base=Path(folder);(base/'__init__.py').write_text('unreviewed')
    module=types.SimpleNamespace(__file__=str(base/'__init__.py'),WeatherSkill=Fixture)
    with patch.dict(sys.modules,{'ovos_skill_weather':module,'ovos_utils.log':types.SimpleNamespace(LOG=logger)}):
        try:boundary.install_weather_skill()
        except RuntimeError:pass
        else:raise AssertionError('Unreviewed weather source accepted')
        with patch.object(boundary,'WEATHER_SOURCES',{'__init__.py':hashlib.sha256(b'unreviewed').hexdigest()}):
            boundary.install_weather_skill();boundary.install_weather_skill()
        exercise(Fixture,module)
assert any('intent/location' in c.args[0] for c in logger.info.call_args_list)
assert all('Sydney' not in repr(c) and 'New York' not in repr(c) for c in logger.info.call_args_list)
print('PASS: source guard, named-city coordinates/timezone, unchanged home/settings and private timing labels')

if len(sys.argv)==2:
    wheel=Path(sys.argv[1])
    record=json.loads((root/'voice/runtime-wheels-linux-x86_64-py311.artifacts.json').read_text())['packages']['ovos-skill-weather']
    assert hashlib.sha256(wheel.read_bytes()).hexdigest()==record['sha256']
    with tempfile.TemporaryDirectory() as folder,zipfile.ZipFile(wheel) as archive:
        base=Path(folder)
        for name,digest in boundary.WEATHER_SOURCES.items():
            source=archive.read('ovos_skill_weather/'+name)
            assert hashlib.sha256(source).hexdigest()==digest
            path=base/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(source)
        source=(base/'__init__.py').read_text();tree=ast.parse(source)
        cls_node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='WeatherSkill')
        methods=[]
        for name in ('_get_intent_data','_get_weather'):
            method=next(n for n in cls_node.body if isinstance(n,ast.FunctionDef) and n.name==name)
            method.decorator_list=[];methods.append(method)
        node=ast.ClassDef(name='WeatherSkill',bases=[],keywords=[],body=methods,decorator_list=[])
        scope={'Message':object,'WeatherIntent':object,'WeatherReport':object,'DAILY':'daily','HOURLY':'hourly',
               'get_report':lambda cfg:cfg,'LOG':logger,'HTTPError':type('HTTPError',(Exception,),{}),
               'LocationNotFoundError':type('LocationNotFoundError',(Exception,),{})}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),
                     'exact-pinned-weather-methods','exec'),scope)
        cls=scope['WeatherSkill'];cls._get_weather_config=lambda self,msg:None
        cls.voc_match=lambda *args:False
        cls._display_current_conditions=lambda *args:None;cls._speak_weather=lambda *args:None
        module=types.SimpleNamespace(__file__=str(base/'__init__.py'),WeatherSkill=cls)
        class ScopeModule:
            def __setattr__(self,key,value):
                if key=='WeatherIntent':scope[key]=value
                else:object.__setattr__(self,key,value)
        # Reproduce wrong-location data before installing the adapter.
        original=types.SimpleNamespace(config=types.SimpleNamespace(core_config={'home':True}))
        assert cls()._get_weather(original).core_config=={'home':True}
        with patch.dict(sys.modules,{'ovos_skill_weather':module,'ovos_utils.log':types.SimpleNamespace(LOG=logger)}):
            boundary.install_weather_skill()
            exercise(cls,ScopeModule())
    print('PASS: exact hash-locked upstream handler fetches separate named-city forecasts without changing home location')
