#!/usr/bin/env python3
"""Exercise actual Media pipeline/bridge across a simulated worker boundary."""
import importlib.util
import os
from pathlib import Path
import sys
import types
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
    assert match.match_type=='jarvis.media.play_query' and match.match_data=={'query':'Funky Music'}
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
