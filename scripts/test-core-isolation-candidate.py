#!/usr/bin/env python3
"""Failure-focused policy/transaction tests. No live service, root or network calls."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
from unittest.mock import Mock,patch

import isolation_services as services
import isolation_worker as worker
import prepare_core_isolation as prepare
import verify_core_isolation as verify
import weather_boundary as weather
import prepare_model_isolation as model
import runtime_provenance as provenance


def rejected(function,*args,**kwargs):
    try:function(*args,**kwargs)
    except (OSError,RuntimeError,ValueError):return
    raise AssertionError('Unsafe operation accepted')


original={'skills':{'blacklisted_skills':['user-disabled'],'future':3},'future':{'retain':[1]},
          'intents':{'pipeline':['ovos-adapt-pipeline-plugin-high','ovos-persona-pipeline-plugin-high',
                                'ovos-common-query-pipeline-plugin','ovos-ocp-pipeline-plugin-high',
                                'jarvis-media-pipeline','jarvis-qwen-pipeline','jarvis-qwen-chat-pipeline']},
          'stt':{'module':'ovos-stt-plugin-fasterwhisper'},'tts':{'module':'ovos-tts-plugin-phoonnx'}}
before=json.dumps(original)
value=worker.overlay(original,'core')
assert json.dumps(original)==before and value['future']==original['future']
assert value['skills']['blacklisted_skills'][0]=='user-disabled'
assert set(worker.ONLINE_SKILLS)<=set(value['skills']['blacklisted_skills'])
assert all('persona' not in s and 'ocp' not in s and 'common-query' not in s for s in value['intents']['pipeline'])
assert 'jarvis-qwen-chat-pipeline' in value['intents']['pipeline']
assert worker.overlay(original,'weather')==original
pins=json.loads((Path(__file__).resolve().parents[1]/'voice/runtime-linux-x86_64-py311.json').read_text())['packages']
with patch.object(worker.metadata,'version',side_effect=lambda name:pins[name]),patch.object(provenance,'matches',return_value=False):
    rejected(worker.verify_pins)
with patch.object(worker.metadata,'version',side_effect=lambda name:'0.4.5a2' if name=='ovos-ww-plugin-openwakeword' else pins[name]),\
     patch.object(provenance,'matches',return_value=True):rejected(worker.verify_pins)
rejected(worker.overlay,{'stt':{'module':'cloud'}},'listener')
rejected(worker.overlay,{'tts':{'module':'cloud'}},'audio')
rejected(worker.overlay,{'skills':{'blacklisted_skills':'invalid'}},'core')
with patch.multiple(worker.os,getuid=lambda:1000,geteuid=lambda:1000,getgid=lambda:1000,getegid=lambda:1000):
    with patch.object(Path,'read_text',side_effect=['CapEff:\t0\nNoNewPrivs:\t1','0::/system.slice/jarvis-v4-1000-core.service']):
        worker.worker_identity('core',1000,1000)
    for status,cgroup in [('CapEff:\t1\nNoNewPrivs:\t1',''),('CapEff:\t0\nNoNewPrivs:\t0',''),
                           ('CapEff:\t0\nNoNewPrivs:\t1','0::/user.slice/other')]:
        with patch.object(Path,'read_text',side_effect=[status,cgroup]):rejected(worker.worker_identity,'core',1000,1000)
    rejected(worker.worker_identity,'arbitrary',1000,1000)
    rejected(worker.worker_identity,'core',0,1000)

units,rule,dropins=prepare.render(1000,1000,'fixture','/home/fixture','/home/fixture/deployment')
assert len(units)==5 and '[Install]' not in ''.join(units.values())
assert all('EnvironmentFile=/home/fixture/.local/state/jarvis/isolation/session.env\n' in body for body in units.values())
assert prepare.environment_file_path('/home/fixture space%name/session.env')=='/home/fixture space%%name/session.env'
for path in ('relative/path','/home/fixture\nEnvironment=bad','/home/fixture\x00'):
    rejected(prepare.environment_file_path,path)
# Exercise the native parser, which ignores quoted EnvironmentFile paths even
# when verify returns success. No service is installed, started or restarted.
analyze=shutil.which('systemd-analyze')
if analyze:
    if os.getuid()==0:raise RuntimeError('Run native parser regression as an ordinary user')
    with tempfile.TemporaryDirectory(prefix='jarvis-env-parser-') as directory:
        root=Path(directory);session=root/'session space%name.env'
        session.write_text('DISPLAY=":0"\nXAUTHORITY="/home/fixture/.Xauthority"\n')
        for quoted in (True,False):
            path=prepare.unit_string(session) if quoted else prepare.environment_file_path(session)
            fixture=root/'jarvis-env-parser.service'
            fixture.write_text('[Service]\nType=oneshot\nExecStart=/usr/bin/true\nEnvironmentFile='+path+'\n')
            result=subprocess.run([analyze,'verify',str(fixture)],capture_output=True,text=True,
                                  timeout=20,env={**os.environ,'LC_ALL':'C','SYSTEMD_LOG_COLOR':'0'})
            assert result.returncode==0,result.stderr
            if quoted:assert 'EnvironmentFile' in result.stderr and 'not absolute' in result.stderr,result.stderr
            else:assert 'EnvironmentFile' not in result.stderr,result.stderr
    print('PASS: native systemd EnvironmentFile parser rejects enclosing quotes and accepts literal space/percent paths')
else:print('NOT RUN: native systemd EnvironmentFile parser unavailable')
assert all('User=1000\nGroup=1000\n' in body and 'NoNewPrivileges=yes' in body for body in units.values())
for name,body in units.items():assert ('IPAddressDeny=any' in body)==any(name.endswith('-'+part+'.service') for part in services.LOGICAL.values())
rejected(prepare.render,0,1000,'fixture','/home/fixture','/home/fixture/deployment')
rejected(prepare.render,1000,1000,'bad\nname','/home/fixture','/home/fixture/deployment')
rejected(prepare.render,1000,1000,'fixture','/home/fixture\n[Service]','/home/fixture/deployment')
assert '%%' in prepare.unit_string('/home/fixture%name')
node=shutil.which('node')
if node:
    script="""const vm=require('vm');let callback;const p=JSON.parse(require('fs').readFileSync(0,'utf8'));
vm.runInNewContext(p.rule,{polkit:{addRule:f=>callback=f,Result:{YES:'yes'}}});
console.log(JSON.stringify(p.cases.map(c=>callback({id:c.id,lookup:k=>c[k]},{user:c.user})==='yes')));"""
    cases=[{'id':'org.freedesktop.systemd1.manage-units','user':'fixture','unit':name,'verb':verb} for name in units for verb in ('start','stop','restart')]
    base=cases[0]
    cases.extend([{**base,'unit':'ssh.service'},{**base,'user':'other'},{**base,'verb':'set-property'},
                  {**base,'id':'org.freedesktop.systemd1.manage-unit-files'}, {'id':base['id'],'user':'fixture','verb':'start'}])
    result=subprocess.run([node,'-e',script],input=json.dumps({'rule':rule,'cases':cases}),capture_output=True,text=True,check=True)
    assert json.loads(result.stdout)==[True]*15+[False]*5
    print('PASS: actual JavaScript fixed-unit/verb authorisation and negative cases')
else:print('NOT RUN: optional JavaScript evaluation; Jarvis requires no new OS dependency')

with patch.object(services,'active',return_value=True),patch.object(services.os,'getuid',return_value=1000):
    assert services.control_arguments(['systemctl','--user','stop','ovos-listener.service'])==['systemctl','--system','stop','--no-ask-password','jarvis-v4-1000-listener.service']
    for args in (['systemctl','--user','start','ssh.service'],['systemctl','--user','set-property','ovos-core.service'],
                 ['systemctl','--user','start','ovos.service']):assert services.control_arguments(args)==args
    rejected(services.physical,'ssh.service')
    rejected(services.guard_deployment,'install',Path('/tmp'))
with patch.dict(os.environ,{'DISPLAY':':0','XAUTHORITY':'/home/fixture/.Xauthority'},clear=True):assert 'DISPLAY=":0"' in services.session_text()
with patch.dict(os.environ,{'DISPLAY':'remote.invalid:0'},clear=True):rejected(services.session_text)

# Ordinary-user CI must inspect its private fixtures, never assume unreadable
# native policy is absent and never access a real desktop home in test mode.
with tempfile.TemporaryDirectory(prefix='jarvis-native-guard-') as directory:
    home=Path(directory)
    with patch.dict(os.environ,{'JARVIS_TEST_MODE':'1'}):
        services.guard_deployment('install',home)
        native=home/'.local/state/jarvis/test-native/polkit-1/rules.d'
        native.mkdir(parents=True)
        (native/f'90-jarvis-v4-{os.getuid()}.rules').write_text('fixture')
        for operation in ('install','rollback','uninstall'):
            rejected(services.guard_deployment,operation,home)
        rejected(services.guard_deployment,'install',Path.home())
    with patch.dict(os.environ,{'JARVIS_TEST_MODE':'0'}),patch.object(services,'active',return_value=False),\
         patch.object(Path,'lstat',side_effect=PermissionError):
        rejected(services.guard_deployment,'install',home)

# Restricted polkit directory alone cannot force administrator authentication.
# All five fixed privileged targets must be absent in the actual system manager.
with patch.object(services.os,'getuid',return_value=1000):
    rule=Path('/etc/polkit-1/rules.d/90-jarvis-v4-1000.rules')
    names=sorted(f'jarvis-v4-1000-{part}.service' for part in services.COMPONENTS)
    blocks=[f'Id={name}\nLoadState=not-found\nActiveState=inactive\nFragmentPath=\nDropInPaths=' for name in names]
    absent='\n\n'.join(blocks)+'\n'
    with patch.object(services.subprocess,'run',return_value=Mock(returncode=0,stdout=absent,stderr='')) as native:
        assert services.native_workers_absent() is True
        assert native.call_args.args[0]==['/usr/bin/systemctl','--system','--no-pager','--no-ask-password','show','--all',
                                        '--property=Id,LoadState,ActiveState,FragmentPath,DropInPaths','--',*names]
        assert native.call_args.kwargs['timeout']==5 and native.call_args.kwargs['env']['LC_ALL']=='C'
    for output in (absent.replace('LoadState=not-found','LoadState=loaded',1),
                   absent.replace('ActiveState=inactive','ActiveState=active',1),
                   absent.replace('FragmentPath=','FragmentPath=/etc/systemd/system/fixture',1),
                   absent.replace('DropInPaths=','DropInPaths=/run/systemd/system/fixture',1),
                   '\n\n'.join(blocks[:-1]),'\n\n'.join([*blocks[:-1],blocks[0]]),
                   absent.replace('Id='+names[0],'Id=other.service',1),
                   absent.replace('LoadState=not-found\n','',1),
                   absent.replace('LoadState=not-found\n','LoadState=not-found\nLoadState=not-found\n',1),
                   absent.replace('LoadState=not-found','LoadState=masked',1), 'unparsed', 'x'*32769):
        with patch.object(services.subprocess,'run',return_value=Mock(returncode=0,stdout=output,stderr='')):
            rejected(services.native_workers_absent)
    for result in (Mock(returncode=1,stdout=absent,stderr=''),Mock(returncode=0,stdout=absent,stderr='denied')):
        with patch.object(services.subprocess,'run',return_value=result):rejected(services.native_workers_absent)
    with patch.object(services.subprocess,'run',side_effect=subprocess.TimeoutExpired(['systemctl'],5)):
        rejected(services.native_workers_absent)
    with patch.object(Path,'lstat',side_effect=PermissionError),\
         patch.object(services,'native_workers_absent',return_value=True) as native:
        assert not services.native_policy_present(rule,rule)
        rejected(services.native_policy_present,Path('/etc/systemd/system/unknown.service'),rule)
        rejected(services.native_policy_present,rule,None)
        assert native.call_count==1
    for present in (False,True):
        def state(path,protected_rule=None):
            if path==rule:
                assert protected_rule==rule
                return present
            return False
        with patch.dict(os.environ,{'JARVIS_TEST_MODE':'0'}),\
             patch.object(services,'active',return_value=False),\
             patch.object(services,'native_policy_present',side_effect=state):
            if present:rejected(services.guard_deployment,'install',Path('/home/fixture'))
            else:services.guard_deployment('install',Path('/home/fixture'))
with patch.object(services.os,'getuid',return_value=0):
    rejected(services.native_workers_absent)
print('PASS: password-free protected-directory guard, complete fixed worker absence, loaded/stale/unknown/denial/timeout rejection')

# Real files, private permissions and rollback after partial daemon-reload failure.
with tempfile.TemporaryDirectory(prefix='jarvis-isolation-transaction-') as directory:
    home=Path(directory)
    configuration=home/'.config/mycroft/mycroft.conf';configuration.parent.mkdir(parents=True)
    configuration.write_text('{"future":{"retain":true}}');settings=home/'.config/jarvis/startup.json'
    settings.parent.mkdir();settings.write_text('{"enabled":false,"future":2}')
    original_files=configuration.read_bytes(),settings.read_bytes()
    info={'uid':1000,'gid':1000}
    calls=[]
    def command(*args):
        calls.append(args)
        if args[:2]==('--system','show'):return 'ActiveState=inactive\n'
        return ''
    with patch.object(Path,'home',return_value=home),patch.object(prepare,'read_candidate',return_value=(info,units,rule,dropins)),\
         patch.object(prepare,'stopped'),patch.object(prepare,'verify_native_units'),patch.object(prepare,'verify_native_rule'),\
         patch.object(prepare,'command',side_effect=command),patch.dict(os.environ,{'DISPLAY':':0'}):
        def failed_reload(*args):
            if args==('--user','daemon-reload') and not calls:
                calls.append(args);raise RuntimeError('Injected reload failure')
            return command(*args)
        with patch.object(prepare,'command',side_effect=failed_reload):rejected(prepare.activate,home)
        assert not services.active(home) and not any(p.exists() for p in prepare.owned_paths(dropins))
        calls.clear();prepare.activate(home)
        assert services.active(home)
        paths=[*prepare.owned_paths(dropins),home/'.local/state/jarvis/isolation/active.json',home/'.local/state/jarvis/isolation/session.env']
        assert all(p.stat().st_mode & 0o777==0o600 for p in paths)
        content={path:path.read_bytes() for path in paths}
        failed=[False]
        def fail_deactivation(*args):
            if args==('--user','daemon-reload') and not failed[0]:
                failed[0]=True;raise RuntimeError('Injected removal reload failure')
            return command(*args)
        with patch.object(prepare,'command',side_effect=fail_deactivation):rejected(prepare.deactivate,home)
        assert services.active(home) and {path:path.read_bytes() for path in paths}==content
        # Reject a changed owned file before touching any unrelated settings.
        paths[0].write_text('changed')
        rejected(prepare.deactivate,home);paths[0].write_bytes(content[paths[0]])
        calls.clear();prepare.deactivate(home)
        assert not services.active(home) and not any(path.exists() for path in paths)
        assert ('--user','stop',*reversed(services.LOGICAL)) in calls
        assert (configuration.read_bytes(),settings.read_bytes())==original_files
print('PASS: activation/removal transactions, partial-failure recovery, private files and configuration preservation')

# Downloads contains private candidates directly; legacy paths still work.
with tempfile.TemporaryDirectory(prefix='jarvis-download-candidates-') as directory:
    home=Path(directory);account=Mock(pw_uid=os.getuid(),pw_gid=os.getgid(),pw_name='fixture',pw_dir=str(home))
    deployment=Path(__file__).resolve().parents[1]
    with patch.object(prepare.pwd,'getpwuid',return_value=account),patch.object(prepare,'verify_pins'),\
         patch.object(prepare,'source_hashes',return_value={'fixture':'hash'}),patch.object(Path,'home',return_value=home):
        for relative in ('Downloads/jarvis-v4-isolation-candidates/new', '.local/state/jarvis/isolation-candidates/legacy'):
            output=home/relative
            assert prepare.prepare(output,deployment)==output
            assert output.stat().st_mode & 0o777==0o700
            assert all(path.stat().st_mode & 0o777==0o600 for path in output.iterdir())
            prepare.read_candidate(output)
            # Exact quoted legacy candidates remain removable after upgrade,
            # but cannot be activated and changed native policy still fails.
            info=json.loads((output/'candidate.json').read_text())
            session=home/'.local/state/jarvis/isolation/session.env'
            for name in info['sha256']:
                path=output/name
                text=path.read_text().replace('EnvironmentFile='+prepare.environment_file_path(session)+'\n',
                                             'EnvironmentFile='+prepare.unit_string(session)+'\n')
                path.write_text(text)
                import hashlib
                info['sha256'][name]=hashlib.sha256(text.encode()).hexdigest()
            (output/'candidate.json').write_text(json.dumps(info))
            prepare.read_candidate(output,validate_source=False)
            rejected(prepare.read_candidate,output)
            first=output/next(name for name in info['sha256'] if name.endswith('.service'))
            first.write_text(first.read_text()+'Environment=UNREVIEWED=1\n')
            rejected(prepare.read_candidate,output,False)
            assert str(output) in (output/'REVIEW.md').read_text()
        rejected(prepare.prepare,home/'Downloads/unreviewed',deployment)
        root=home/'Downloads/jarvis-v4-isolation-candidates';root.chmod(0o755)
        rejected(prepare.prepare,root/'unsafe',deployment);root.chmod(0o700)
    with patch.object(Path,'home',return_value=home),patch.object(model,'daemon_context',return_value={'fixture':True}):
        output=home/'Downloads/jarvis-v4-model-isolation-candidates/new'
        assert model.prepare(output)==output and output.stat().st_mode & 0o777==0o700
        assert all(path.stat().st_mode & 0o777==0o600 for path in output.iterdir())
        rejected(model.prepare,home/'Downloads/unreviewed-model')
print('PASS: direct Downloads preparation, private permissions, exact review paths and legacy candidate compatibility')

forecast={'latitude':0,'longitude':0,'hourly':'temperature_2m','daily':'temperature_2m_max','current_weather':True,
          'temperature_unit':'celsius','windspeed_unit':'kmh','precipitation_unit':'mm','timezone':'UTC'}
assert weather.parameters(weather.FORECAST,forecast)['latitude']==0
for url in ('http://api.open-meteo.com/v1/forecast',weather.FORECAST+'?x=1',weather.FORECAST+'.evil.invalid'):
    rejected(weather.parameters,url,forecast)
for data in ({**forecast,'latitude':float('nan')},{**forecast,'longitude':True},{**forecast,'timezone':'../bad'},{**forecast,'unreviewed':1}):
    rejected(weather.parameters,weather.FORECAST,data)
assert weather.parameters(weather.NOMINATIM+'search',{'q':'Sydney, Australia','format':'json','limit':1})['limit']==1
rejected(weather.parameters,weather.NOMINATIM+'search',{'q':'https://evil.invalid','format':'json','limit':1})
rejected(weather.validated,'POST',weather.FORECAST,{'params':forecast})
rejected(weather.validated,'GET',weather.FORECAST,{'params':forecast,'auth':('fixture','fixture')})
try:import requests
except ModuleNotFoundError:
    class RequestException(Exception):pass
    requests=types.SimpleNamespace(RequestException=RequestException)
    sys.modules['requests']=requests
session=Mock(proxies={},cookies={},headers={})
response=Mock(status_code=200,headers={'Content-Length':'2'});response.iter_content.return_value=[b'{}']
request=Mock(return_value=response)
weather.fetch(request,session,weather.FORECAST,forecast,'en')
assert session.trust_env is False and session.auth is None and session.cert is None and session.params=={}
assert request.call_args.kwargs['allow_redirects'] is False and request.call_args.kwargs['verify'] is True
assert request.call_args.kwargs['timeout']==(5,5) and response.close.called
for status,length,chunks in ((302,None,[]),(200,str(weather.MAX_BYTES+1),[]),(200,None,[b'x'*(weather.MAX_BYTES+1)])):
    reply=Mock(status_code=status,headers={} if length is None else {'Content-Length':length});reply.iter_content.return_value=chunks
    try:weather.fetch(Mock(return_value=reply),session,weather.FORECAST,forecast,'en')
    except requests.RequestException:assert reply.close.called
    else:raise AssertionError('Unsafe weather reply accepted')
with patch.object(weather.subprocess,'run',side_effect=subprocess.TimeoutExpired(['fixed'],14)) as process:
    try:weather.request(session,'GET',weather.FORECAST,params=forecast)
    except requests.RequestException:pass
    else:raise AssertionError('Unbounded weather child')
    assert process.call_args.kwargs['timeout']==14 and process.call_args.args[0][1]=='-I'

with tempfile.TemporaryDirectory(prefix='jarvis-probe-ticket-') as directory:
    root=Path(directory);token='a'*32;ticket=root/(token+'.json')
    with patch.object(verify,'ticket_directory',return_value=root):
        assert not verify.claim('../../bad','core',now=100)
        prepare.private_file(ticket,json.dumps({'expires':120,'components':list(verify.COMPONENTS)}))
        assert verify.claim(token,'core',now=100) and not verify.claim(token,'core',now=100)
        assert not verify.claim(token,'listener',now=121)
        ticket.chmod(0o644);assert not verify.claim(token,'listener',now=100)

controls={name:{'reachable':True,'outcome':'connected'} for name in (*verify.EXTERNAL,*verify.LOCAL)}
restricted={**controls,**{name:{'reachable':False,'outcome':'permission_denied'} for name in verify.EXTERNAL}}
result={'status':'completed','unit_context_verified':True,'desktop_user_identity_verified':True,'tests':restricted}
assert verify.assessment(controls,result,controls)['all_external_paths_denied']
assert not verify.assessment({},result,controls)['all_external_paths_denied']
assert not verify.assessment(controls,{**result,'unit_context_verified':False},controls)['all_external_paths_denied']
assert not verify.assessment(controls,{},controls)['required_loopback_preserved']
assert verify.safe_worker({**result,'worker_source_sha256':'wrong'},'reviewed')['status']=='worker_source_unverified'

class Message:
    def __init__(self,name,data):self.msg_type,self.data=name,data

class Bus:
    def __init__(self,**kw):
        assert kw=={'host':'127.0.0.1','port':8181,'ssl':False}
        self.handlers={};self.connected_event=Mock(wait=lambda seconds:True);self.closed=False
    def on(self,name,handler):self.handlers[name]=handler
    def run_in_thread(self):pass
    def close(self):self.closed=True
    def emit(self,message):pass

with tempfile.TemporaryDirectory(prefix='jarvis-probe-cleanup-') as directory:
    root=Path(directory)
    with patch.object(verify,'active',return_value=True),patch.multiple(verify.os,getuid=lambda:1000,geteuid=lambda:1000,getgid=lambda:1000,getegid=lambda:1000),\
         patch.object(verify,'ticket_directory',return_value=root),patch.object(verify,'tests',return_value=controls),\
         patch.object(verify,'source_hash',return_value='reviewed'):
        fake=types.SimpleNamespace(MessageBusClient=Mock(side_effect=RuntimeError('Constructor failure')),Message=Message)
        with patch.dict(sys.modules,{'ovos_bus_client':fake}):rejected(verify.collect,timeout=0)
        assert not list(root.iterdir())
        bus=Bus(host='127.0.0.1',port=8181,ssl=False)
        fake.MessageBusClient=lambda **kw:bus
        with patch.dict(sys.modules,{'ovos_bus_client':fake}):report=verify.collect(timeout=0)
        assert not report['actual_core_listener_audio_socket_tests_passed'] and bus.closed and not list(root.iterdir())
        bus=Bus(host='127.0.0.1',port=8181,ssl=False);bus.connected_event=Mock(wait=lambda seconds:False)
        with patch.dict(sys.modules,{'ovos_bus_client':fake}):rejected(verify.collect,timeout=0)
        assert bus.closed and not list(root.iterdir())

bus=Bus(host='127.0.0.1',port=8181,ssl=False)
fake=types.SimpleNamespace(MessageBusClient=lambda **kw:bus,Message=Message)
with patch.dict(sys.modules,{'ovos_bus_client':fake}),patch.object(verify,'claim',return_value=True),\
     patch.object(verify,'worker_identity',side_effect=RuntimeError('Wrong identity')),patch.object(verify,'tests') as network:
    verify.attach('core',1000,1000)
    bus.handlers[verify.EVENT](Message(verify.EVENT,{'token':'a'*32,'test_network':True}))
    assert not network.called
print('PASS: provider/HTTP bounds, identity/control guards, single-use tests, missing-worker/outage verdicts and cleanup')

assert 'User=' not in model.POLICY and 'ExecStart=' not in model.POLICY and 'Capability' not in model.POLICY
assert 'IPAddressDeny=any' in model.POLICY and 'IPAddressAllow=127.0.0.1 ::1' in model.POLICY
base='LoadState=loaded\nActiveState=active\nMainPID=999\nFragmentPath=/etc/systemd/system/ollama.service\n'
with patch.object(model.subprocess,'run',return_value=subprocess.CompletedProcess([],0,base,'')),\
     patch.object(model,'regular',return_value='fixture unit') as native,\
     patch.object(Path,'read_text',side_effect=lambda *args,**kw:'Uid:\t0\t0\t0\t0\n'):
    rejected(model.daemon_context)
    assert not native.called
with patch.object(model.subprocess,'run',return_value=subprocess.CompletedProcess([],0,base+'IPAddressAllow=any\n','')),\
     patch.object(model,'regular',return_value='fixture unit'),patch.object(Path,'read_text',return_value='Uid:\t1000\t1000\t1000\t1000\n'):
    rejected(model.daemon_context)
print('PASS: full-runtime provenance is required and model policy preserves identity/executable while refusing root/custom policy')
