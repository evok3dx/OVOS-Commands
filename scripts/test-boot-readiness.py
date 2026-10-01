#!/usr/bin/env python3
"""Real executor cancellation and readiness policy, without live services."""
import hashlib
import os
from pathlib import Path
import sys
import threading
import types
import importlib.util
import json
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import isolation_worker as worker

if os.getuid()==0:raise RuntimeError('Run regression as the ordinary user')

class Message:
    def __init__(self,name):self.msg_type=name

class Boot:
    def __init__(self,settings=None):
        self.settings=dict(settings or {})
        self.config_core={'skills':{'blacklisted_skills':['online','disabled']}}
        self.requests=[];self.responses={};self.messages=[];self.speech=[]
        self.bus=types.SimpleNamespace(emit=lambda m:self.messages.append(m.msg_type))
        self.initialized=False;self.cleaned=False
    def initialize(self):self.initialized=True
    def shutdown(self):self.cleaned=True
    def check_services_ready(self,services):
        name=next(iter(services));self.requests.append(name)
        return self.responses.get(name,False)
    def handle_ready(self,message):
        if self.settings.get('speak_ready',True):self.speech.append('ready')
    def handle_check_device_readiness(self,message=None):raise AssertionError('Old polling callback used')
    def is_device_ready(self):raise AssertionError('Old unfiltered inventory used')

module=types.SimpleNamespace(__file__=__file__,BootFinishedSkill=Boot,Message=Message,
                            get_installed_skill_ids=lambda conf:['local','online','disabled'])
with patch.dict(sys.modules,{'ovos_skill_boot_finished':module}):
    try:worker.install_boot_readiness()
    except RuntimeError:pass
    else:raise AssertionError('Unknown upstream source accepted')
    with patch.object(worker,'BOOT_SOURCE_SHA256',hashlib.sha256(Path(__file__).read_bytes()).hexdigest()):
        worker.install_boot_readiness();worker.install_boot_readiness()

skill=Boot();skill.initialize();assert skill.initialized
skill.responses=dict.fromkeys(('skills','voice','audio','local'),True)
skill.handle_ready(Message('mycroft.ready'));assert not skill.speech
skill.handle_check_device_readiness()
assert skill.messages==['mycroft.ready']
assert skill.requests==['skills','voice','audio','local']
skill.handle_ready(Message('mycroft.ready'));skill.handle_ready(Message('mycroft.ready'))
skill.handle_check_device_readiness()
assert skill.speech==['ready'] and skill.messages==['mycroft.ready']
assert skill.settings=={} and skill.config_core['skills']['blacklisted_skills']==['online','disabled']

custom=Boot({'ready_settings':['custom'],'speak_ready':False,'future':7})
custom.initialize();custom.responses['custom']=True
custom.handle_check_device_readiness();custom.handle_ready(Message('mycroft.ready'))
assert custom.requests==['custom'] and not custom.speech
assert custom.settings=={'ready_settings':['custom'],'speak_ready':False,'future':7}

clock=[0.0]
class ClockEvent:
    def is_set(self):return False
    def wait(self,seconds):clock[0]+=seconds;return False
never=Boot({'ready_settings':['missing']});never.initialize();never._jarvis_ready_stop=ClockEvent()
with patch.object(worker.time,'monotonic',side_effect=lambda:clock[0]):
    assert not never.is_device_ready()
assert clock[0]==60 and not never.speech and not never.messages

# An executor task is non-daemon and holds interpreter exit. It must finish
# when the skill shuts down, including an explicit unmet owner dependency.
for names in (['missing'],['online']):
    pending=Boot({'ready_settings':names});pending.initialize()
    entered=threading.Event()
    class Responses(dict):
        def get(self,key,default=None):entered.set();return False
    pending.responses=Responses()
    executor=ThreadPoolExecutor(max_workers=1)
    future=executor.submit(pending.handle_check_device_readiness)
    assert entered.wait(2)
    pending.shutdown();future.result(timeout=2);executor.shutdown(wait=True)
    assert pending.cleaned and not pending.messages and not pending.speech
    pending.handle_ready(Message('mycroft.ready'));assert not pending.speech
    assert pending.requests==names
print('PASS: source guard, enabled readiness replies, owner settings, once-only announcement, missing readiness and real executor shutdown cancellation')

if len(sys.argv)==2:
    # CI downloads only the hash-locked upstream wheel, without installing it.
    # Execute its actual class against bounded bus/skill adapters.
    root=Path(__file__).resolve().parents[1]
    record=json.loads((root/'voice/runtime-wheels-linux-x86_64-py311.artifacts.json').read_text())['packages']['ovos-skill-boot-finished']
    wheel=Path(sys.argv[1]);assert hashlib.sha256(wheel.read_bytes()).hexdigest()==record['sha256']
    dependencies={
        'ovos_bus_client.message':types.SimpleNamespace(Message=Message),
        'ovos_utils.log':types.SimpleNamespace(LOG=types.SimpleNamespace(info=lambda *a:None,debug=lambda *a:None)),
        'ovos_workshop.decorators':types.SimpleNamespace(intent_handler=lambda name:lambda func:func),
        'ovos_plugin_manager.skills':types.SimpleNamespace(get_installed_skill_ids=lambda conf:['local','online','disabled'])}
    class Base:
        def __init__(self,settings=None):
            self.settings=dict(settings or {})
            self.config_core={'skills':{'blacklisted_skills':['online','disabled']}}
            self.requests=[];self.messages=[];self.speech=[];self.events={}
            self.responses=dict.fromkeys(('skills','voice','audio','local'),True)
            self.bus=types.SimpleNamespace(emit=lambda m:self.messages.append(m.msg_type),wait_for_response=self.response)
            self.enclosure=types.SimpleNamespace(eyes_on=lambda:None,eyes_blink=lambda *a:None)
            self.log=types.SimpleNamespace(debug=lambda *a:None)
        def response(self,message):
            name=message.msg_type.removeprefix('mycroft.').removesuffix('.is_ready')
            self.requests.append(name)
            return types.SimpleNamespace(data={'status':True}) if self.responses.get(name) else None
        def add_event(self,name,handler):self.events[name]=handler
        def shutdown(self):pass
        def acknowledge(self):pass
        def speak_dialog(self,name):self.speech.append(name)
    dependencies['ovos_workshop.skills']=types.SimpleNamespace(OVOSSkill=Base)
    # The actual upstream Message call uses data/context keyword arguments.
    class RealMessage(Message):
        def __init__(self,name,*args,**kwargs):super().__init__(name)
    dependencies['ovos_bus_client.message'].Message=RealMessage
    with tempfile.TemporaryDirectory() as folder,patch.dict(sys.modules,dependencies):
        with zipfile.ZipFile(wheel) as archive:source=archive.read('ovos_skill_boot_finished/__init__.py')
        path=Path(folder)/'boot.py';path.write_bytes(source)
        spec=importlib.util.spec_from_file_location('ovos_skill_boot_finished',path)
        upstream=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'ovos_skill_boot_finished':upstream}):
            spec.loader.exec_module(upstream);worker.install_boot_readiness()
            real=upstream.BootFinishedSkill();real.initialize()
            real.handle_check_device_readiness();real.handle_ready(RealMessage('mycroft.ready'))
            real.handle_ready(RealMessage('mycroft.ready'))
            assert real.speech==['ready'] and real.requests==['skills','voice','audio','local']
            assert real.messages==['mycroft.ready.check','mycroft.ready']
            real.shutdown();real.handle_check_device_readiness()
            assert real.messages==['mycroft.ready.check','mycroft.ready']
            pending=upstream.BootFinishedSkill({'ready_settings':['disabled'],'speak_ready':False})
            pending.initialize();entered=threading.Event()
            class Pending(dict):
                def get(self,key,default=None):entered.set();return False
            pending.responses=Pending()
            executor=ThreadPoolExecutor(max_workers=1)
            future=executor.submit(pending.handle_check_device_readiness)
            assert entered.wait(2);pending.shutdown();future.result(timeout=2);executor.shutdown(wait=True)
            assert not pending.speech and pending.requests==['disabled']
            assert pending.settings=={'ready_settings':['disabled'],'speak_ready':False}
    print('PASS: exact hash-locked upstream boot skill, real readiness methods and executor cancellation')
