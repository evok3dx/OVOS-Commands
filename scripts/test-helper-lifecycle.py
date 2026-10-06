#!/usr/bin/env python3
"""Reproduce duplicate standalone handlers without network, speech or launches."""
import ast
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import types
from typing import Optional
from unittest.mock import patch
import zipfile
import isolation_worker as worker

if os.getuid()==0:raise RuntimeError('Run regression as the ordinary user')


class Message:
    def __init__(self,name,data=None):self.msg_type=name;self.data=data or {}


class Bus:
    def __init__(self):self.handlers=[];self.loads=0
    def play(self):
        # Each live registration represents one status reply/search/open.
        return len(tuple(self.handlers))


class Loader:
    """Bounded skill boundary; creating twice leaves the first handler alive."""
    def __init__(self,bus,skill_id):self.bus=bus;self.skill_id=skill_id;self.instance=None
    def load(self,*args):return self._load()
    def _load(self):
        self.instance=object();self.bus.handlers.append(self.instance);self.bus.loads+=1
        return True
    def _unload(self):
        if self.instance is not None:self.bus.handlers.remove(self.instance)
        self.instance=None
    def reload(self):self._unload();return self._load()
    def deactivate(self):self._unload()


class Fixture:
    def __init__(self,skill_id,bus=None):self.skill_id=skill_id;self.bus=bus;self.skill_loader=None
    def load_skill(self,message=None):
        if self.skill_loader:self.skill_loader.reload();return
        self.skill_loader=Loader(self.bus,self.skill_id);self.skill_loader.load()
    def do_load(self,message):
        if message.data['skill']==self.skill_id and self.skill_loader:self.skill_loader._load()
    def do_unload(self,message):
        if message.data['skill']==self.skill_id and self.skill_loader:self.skill_loader._unload()
    def unload(self):
        if self.skill_loader:self.skill_loader.deactivate();self.skill_loader._unload()


def install(cls,path,digest=None):
    module=types.SimpleNamespace(__file__=str(path),SkillContainer=cls)
    with patch.dict(sys.modules,{'ovos_workshop':types.SimpleNamespace(skill_launcher=module),
                                 'ovos_workshop.skill_launcher':module}):
        if digest is None:worker.install_helper_lifecycle()
        else:
            with patch.object(worker,'SKILL_LAUNCHER_SOURCE_SHA256',digest):
                worker.install_helper_lifecycle()


try:install(Fixture,Path(__file__))
except RuntimeError:pass
else:raise AssertionError('Unknown launcher source accepted')
digest=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
install(Fixture,Path(__file__),digest)
initialise=Fixture.__init__;install(Fixture,Path(__file__),digest)
assert Fixture.__init__ is initialise
bus=Bus();container=Fixture('helper',bus)
other=Fixture('other',Bus())
assert container._jarvis_container_lock is not other._jarvis_container_lock
container.load_skill();container.do_load(Message('skillmanager.activate',{'skill':'helper'}))
assert bus.play()==1 and bus.loads==1
container.do_unload(Message('skillmanager.deactivate',{'skill':'helper'}));assert bus.play()==0
container.do_load(Message('skillmanager.activate',{'skill':'other'}));assert bus.play()==0
container.do_load(Message('skillmanager.activate',{'skill':'helper'}));assert bus.play()==1
container.load_skill(Message('mycroft.ready'));assert bus.play()==1 and bus.loads==3
container.unload();container.unload()
container.load_skill();container.do_load(Message('skillmanager.activate',{'skill':'helper'}))
assert bus.play()==0 and bus.loads==3
print('PASS: source refusal, once-only adapter, independent locks, idempotent activation, reload, reactivation and final shutdown')

for role,suffix in (('media','jarvis-media'),('weather','weather')):
    skill_id='ovos-skill-'+suffix+'.openvoiceos'
    for disabled in (False,True):
        calls=[]
        instance=types.SimpleNamespace(run=lambda:calls.append('run'))
        def create(*args):calls.append('container');return instance
        config=types.SimpleNamespace(Configuration=lambda:{'skills':{'blacklisted_skills':[skill_id] if disabled else []}})
        launcher=types.SimpleNamespace(SkillContainer=create)
        with patch.dict(sys.modules,{'ovos_config':config,'ovos_workshop.skill_launcher':launcher}), \
             patch.object(worker,'install_helper_lifecycle',side_effect=lambda:calls.append('guard')):
            worker.run_component(role)
        assert calls==([] if disabled else ['guard','container','run'])
        if not disabled:assert instance.skill_directory is None
print('PASS: both helper entry points guard before construction and preserve explicit disabled choices')

if len(sys.argv)==2:
    root=Path(__file__).resolve().parents[1]
    record=json.loads((root/'voice/runtime-wheels-linux-x86_64-py311.artifacts.json').read_text())['packages']['ovos-workshop']
    wheel=Path(sys.argv[1])/record['file']
    assert hashlib.sha256(wheel.read_bytes()).hexdigest()==record['sha256']
    with zipfile.ZipFile(wheel) as archive:source=archive.read('ovos_workshop/skill_launcher.py')
    assert hashlib.sha256(source).hexdigest()==worker.SKILL_LAUNCHER_SOURCE_SHA256
    cls_node=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='SkillContainer')

    def exact_class():
        scope={'Optional':Optional,'MessageBusClient':Bus,'Message':Message,
               'setup_locale':lambda:None,'get_skill_directories':lambda:[],
               'PluginSkillLoader':Loader,'SkillLoader':Loader,
               'LOG':types.SimpleNamespace(info=lambda *a:None,debug=lambda *a:None,
                                           exception=lambda *a:None)}
        exec(compile(ast.Module(body=[cls_node],type_ignores=[]),'reviewed-skill-container','exec'),scope)
        return scope['SkillContainer'],scope

    def race(cls,scope,guarded):
        bus=Bus();container=cls('helper',bus=bus)
        first_entered=threading.Event();second_entered=threading.Event()
        second_attempted=threading.Event();release=threading.Event();finds=[]
        def plugins():
            finds.append(True)
            (first_entered if len(finds)==1 else second_entered).set()
            assert release.wait(3)
            return {'helper':object}
        scope['find_skill_plugins']=plugins
        def second_load():
            second_attempted.set();container.load_skill(Message('mycroft.ready'))
        with ThreadPoolExecutor(max_workers=2) as executor:
            one=executor.submit(container.load_skill)
            assert first_entered.wait(2)
            two=executor.submit(second_load);assert second_attempted.wait(2)
            if guarded:assert not second_entered.wait(0.1)
            else:assert second_entered.wait(2)
            release.set();one.result(timeout=2);two.result(timeout=2)
        assert bus.play()==(1 if guarded else 2)
        assert len(finds)==(1 if guarded else 2)
        return container,bus

    original,scope=exact_class()
    container,bus=race(original,scope,False)
    container.unload()
    assert bus.play()==1, 'Race must reproduce the orphaned handler'

    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'skill_launcher.py';path.write_bytes(source)
        for skill_id in ('ovos-skill-jarvis-media.openvoiceos','ovos-skill-weather.openvoiceos'):
            cls,scope=exact_class();install(cls,path)
            container,bus=race(cls,scope,True)
            container.skill_id=skill_id;container.skill_loader.skill_id=skill_id
            assert bus.play()==1
            before=bus.loads
            with ThreadPoolExecutor(max_workers=4) as executor:
                list(executor.map(container.do_load,[Message('skillmanager.activate',{'skill':skill_id})]*4))
            assert bus.play()==1 and bus.loads==before
            container.do_unload(Message('skillmanager.deactivate',{'skill':skill_id}));assert bus.play()==0
            container.do_load(Message('skillmanager.activate',{'skill':skill_id}));assert bus.play()==1
            container.load_skill(Message('mycroft.ready'));assert bus.play()==1
            container.unload();container.load_skill();assert bus.play()==0

        # Stop during the original startup load must clean up and prevent a
        # queued ready callback from recreating handlers after final shutdown.
        cls,scope=exact_class();install(cls,path)
        bus=Bus();container=cls('helper',bus=bus)
        entered=threading.Event();release=threading.Event();stopping=threading.Event()
        def plugins():
            entered.set();assert release.wait(3);return {'helper':object}
        scope['find_skill_plugins']=plugins
        def stop():stopping.set();container.unload()
        with ThreadPoolExecutor(max_workers=2) as executor:
            loading=executor.submit(container.load_skill);assert entered.wait(2)
            shutdown=executor.submit(stop);assert stopping.wait(2)
            release.set();loading.result(timeout=2);shutdown.result(timeout=2)
        container.load_skill(Message('mycroft.ready'));assert bus.play()==0

        # A failed initial plugin lookup releases the lifecycle lock and does
        # not prevent a later legitimate readiness attempt from succeeding.
        cls,scope=exact_class();install(cls,path)
        bus=Bus();container=cls('helper',bus=bus)
        scope['find_skill_plugins']=lambda:{}
        try:container.load_skill()
        except ValueError:pass
        else:raise AssertionError('Missing plugin accepted')
        assert bus.play()==0
        scope['find_skill_plugins']=lambda:{'helper':object}
        container.load_skill();assert bus.play()==1
        container.unload();assert bus.play()==0
    print('PASS: exact hash-locked upstream reproduces two live handlers; guarded Media/Weather startup, activation and concurrent shutdown retain at most one')
