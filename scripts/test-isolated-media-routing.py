#!/usr/bin/env python3
"""Exercise actual Media pipeline/bridge across a simulated worker boundary."""
import importlib.util
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import types
import zipfile
from unittest.mock import patch
import isolation_worker as worker

assert os.getuid()!=0, 'Run as the ordinary user'
root=Path(__file__).resolve().parents[1]
package=types.ModuleType('ovos_skill_jarvis_media')
package.__path__=[str(root/'plugins/ovos-skill-jarvis-media/ovos_skill_jarvis_media')]
class Message:
    def __init__(self,name,context=None):self.msg_type=name;self.context=context or {}
class Pipeline:
    def __init__(self,bus=None,config=None):self.bus=bus;self.config=config or {}
modules={'ovos_skill_jarvis_media':package,
         'ovos_plugin_manager.templates.pipeline':types.SimpleNamespace(
             PipelinePlugin=Pipeline, IntentHandlerMatch=lambda **kw:types.SimpleNamespace(**kw)),
         'ovos_bus_client.message':types.SimpleNamespace(Message=Message)}
with patch.dict(sys.modules,modules):
    from ovos_skill_jarvis_media import bridge, pipeline
    requests=[]
    answer=[{'ready':True,'revision':'jarvis.media.plugin.2','actions':['play']}]
    def response(message,timeout):
        assert message.msg_type=='jarvis.media.status' and timeout==0.5
        assert message.context['destination']==pipeline.SKILL_ID
        requests.append(message.msg_type)
        return types.SimpleNamespace(data=answer[0]) if answer[0] is not None else None
    route=pipeline.JarvisMediaPipeline(types.SimpleNamespace(wait_for_response=response))
    utterance=Message('recognizer_loop:utterance')
    assert bridge.get_skill() is None
    assert route.match(['Play Funky Music'],'en-US',utterance) is None and not requests
    bridge.enable_remote(True)
    match=route.match(['Play Funky Music'],'en-US',utterance)
    assert match.match_type=='jarvis.media.play_query' and match.match_data=={
        'query':'Funky Music','skill_id':pipeline.SKILL_ID}
    # Core's automatic load blacklist includes Media; the fixed remote event
    # must not activate that unloaded local actor or be rejected for its ID.
    assert match.skill_id is None
    for invalid in (None,{'ready':False},{'ready':True,'revision':'unknown','actions':['play']},
                    {'ready':True,'revision':'jarvis.media.plugin.2','actions':[]}):
        answer[0]=invalid
        assert route.match(['Play Funky Music'],'en-US',utterance) is None
    count=len(requests)
    for text in ('play music','pause music','open Firefox','do not play a song'):
        assert route.match([text],'en-US',utterance) is None
    assert route.match(['Play Funky Music'],'fr-FR',utterance) is None
    assert route.match(['Play Funky Music'],'en-US',Message('unrelated')) is None
    assert len(requests)==count
    # Existing same-process mode retains its skill activation and no bus probe.
    skill=types.SimpleNamespace(skill_id=pipeline.SKILL_ID)
    # SimpleNamespace is not weak-referenceable; use an ordinary instance.
    skill=type('Skill',(),{'skill_id':pipeline.SKILL_ID})()
    bridge.register(skill)
    assert route.match(['Play Funky Music'],'en-US',utterance).skill_id==pipeline.SKILL_ID
    bridge.unregister(skill)
    config={'skills':{'blacklisted_skills':[]},'intents':{'pipeline':['jarvis-media-pipeline','jarvis-qwen-pipeline']}}
    class Configuration:
        filter_and_merge=staticmethod(lambda configs:configs)
        @staticmethod
        def load_all_configs():Configuration.filter_and_merge(config)
    with patch.dict(sys.modules,{'ovos_config':types.SimpleNamespace(Configuration=Configuration)}):
        worker.install_overlay('core')
        assert bridge.remote_enabled()
        value=Configuration.filter_and_merge(config)
        assert pipeline.SKILL_ID in value['skills']['blacklisted_skills']
        assert value['intents']['pipeline']==config['intents']['pipeline']
        config['skills']['blacklisted_skills']=[pipeline.SKILL_ID]
        Configuration.load_all_configs()
        assert not bridge.remote_enabled()
        config['skills']['blacklisted_skills']=[]
        Configuration.load_all_configs()
        assert bridge.remote_enabled()
print('PASS: isolated direct title route, actual helper readiness, disabled/missing helper guards, owner reload and retained Qwen')

if len(sys.argv)==2:
    wheel=Path(sys.argv[1])
    record=json.loads((root/'voice/runtime-wheels-linux-x86_64-py311.artifacts.json').read_text())['packages']['ovos-core']
    assert hashlib.sha256(wheel.read_bytes()).hexdigest()==record['sha256']
    with zipfile.ZipFile(wheel) as archive:source=archive.read('ovos_core/intent_services/dispatcher.py')
    class WireMessage:
        def __init__(self,name,data=None,context=None):
            self.msg_type=name;self.data=data or {};self.context=context or {}
        def forward(self,name,data=None):return WireMessage(name,data,self.context.copy())
    class Bus:
        def __init__(self):self.events=[];self.handlers={}
        def on(self,name,function):self.handlers[name]=function
        def emit(self,message):self.events.append(message)
    topics=types.SimpleNamespace(INTENT_HANDLER_START='start',INTENT_HANDLER_COMPLETE='complete',
                                INTENT_HANDLER_ERROR='error')
    dependencies={'ovos_bus_client.client':types.SimpleNamespace(MessageBusClient=Bus),
        'ovos_bus_client.message':types.SimpleNamespace(Message=WireMessage),
        'ovos_spec_tools':types.SimpleNamespace(SpecMessage=topics),
        'ovos_utils.fakebus':types.SimpleNamespace(FakeBus=Bus),
        'ovos_utils.log':types.SimpleNamespace(LOG=types.SimpleNamespace(
            warning=lambda *args:None,error=lambda *args:None,exception=lambda *args:None)),
        'ovos_core.intent_services.working_session':types.SimpleNamespace(
            raw_session_id=lambda message:message.context['session']['session_id'])}
    scope={}
    with patch.dict(sys.modules,dependencies):exec(compile(source,'exact-pinned-core-dispatcher','exec'),scope)
    owner=pipeline.SKILL_ID;event=pipeline.EVENT_PLAY
    completion=WireMessage('mycroft.skill.handler.complete',{'intent_name':event},
        {'skill_id':owner,'session':{'session_id':'test'}})
    # Reproduce the reported 300s watchdog using the old inferred owner.
    bus=Bus();old=scope['IntentDispatcher'](bus,timeout=0)
    dispatch=WireMessage(event,context={'session':{'session_id':'test'}})
    old.dispatch(dispatch);old._on_skill_complete(completion)
    assert old._in_flight
    old._on_timeout('test',old._in_flight['test'][0])
    assert bus.events[-1].msg_type=='error'
    # Same wire topic and unloaded-local-skill policy, correct fixed owner.
    bus=Bus();terminals=[]
    current=scope['IntentDispatcher'](bus,timeout=0,on_terminal=terminals.append)
    match=pipeline.IntentHandlerMatch(match_type=event,match_data={'query':'Title','skill_id':owner},
                                     skill_id=None,utterance='Play Title')
    inferred=match.skill_id or match.match_data.get('skill_id') or dispatch.msg_type.split(':',1)[0]
    current.dispatch(dispatch,inferred,event);current._on_skill_complete(completion)
    current._on_skill_complete(completion)
    assert not current._in_flight and len(terminals)==1
    assert [message.msg_type for message in bus.events]==['start',event,'complete']
    # Production registration carries the fixed intent name on the done-signal.
    tree=ast.parse((root/'plugins/ovos-skill-jarvis-media/ovos_skill_jarvis_media/__init__.py').read_text())
    initialise=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='initialize')
    registration=next(n for n in ast.walk(initialise) if isinstance(n,ast.Call)
                      and isinstance(n.func,ast.Attribute) and n.func.attr=='add_event'
                      and isinstance(n.args[0],ast.Attribute) and n.args[0].attr=='EVENT_PLAY')
    assert any(k.arg=='intent_name' and isinstance(k.value,ast.Attribute)
               and k.value.attr=='EVENT_PLAY' for k in registration.keywords)
    print('PASS: exact pinned core reproduces old Media timeout; fixed remote owner completes once without local activation')
