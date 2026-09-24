#!/usr/bin/env python3
"""Connect enabled Jarvis app names to the existing Whisper initial prompt."""
import argparse
import ast
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import time
from jarvis_app_hints import prompt_for

ROOT = Path(__file__).resolve().parent
UNITS = ('ovos-audio.service', 'ovos-core.service', 'ovos-listener.service')
CORE, LISTENER = UNITS[1:]
PLUGIN = 'ovos-stt-plugin-fasterwhisper'
MARKER = 'Jarvis dynamic Whisper app hints active'
WRAPPER = """

def _jarvis_app_initial_prompt(stt):
    try:
        from .jarvis_app_hints import prompt_for
        return prompt_for(stt.config.get('initial_prompt'),
                          getattr(stt.engine, 'hf_tokenizer', None))[0]
    except Exception:
        return stt.config.get('initial_prompt')
"""
INIT = """
        try:
            from .jarvis_app_hints import prompt_for
            _, info = prompt_for(self.config.get('initial_prompt'),
                                 getattr(self.engine, 'hf_tokenizer', None), strict=True)
            LOG.info('Jarvis dynamic Whisper app hints active: %s names; %s tokens; limited=%s',
                     info['names'], info['tokens'], info['limited'])
        except Exception:
            LOG.warning('Jarvis app hints unavailable; retaining configured Whisper prompt')
"""


def method(source, name):
    cls = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == 'FasterWhisperSTT')
    return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)


def shape(node):
    return ast.dump(node, include_attributes=False)


def patch_source(data):
    source = data.decode()
    base = (ROOT/'reviewed-plugin-0.4.0.py').read_text()
    if '_jarvis_app_initial_prompt' in source or MARKER in source:
        raise RuntimeError('Dynamic hints already present; inspect status instead of patching twice')
    execute = method(source, 'execute')
    expected = method(base, 'execute')
    patched = method(base.replace('vad_filter=self.config.get("vad_filter", False)',
                                 'vad_filter=self.config.get("vad_filter", False), initial_prompt=self.config.get("initial_prompt")'), 'execute')
    if shape(execute) not in (shape(expected), shape(patched)):
        raise RuntimeError('Installed execute method differs from the reviewed plugin; no files changed')
    init = method(source, '__init__')
    old_marker = 'Jarvis Whisper name hints active for small.en'
    normalized_init = method(source, '__init__')
    if (normalized_init.body and isinstance(normalized_init.body[-1], ast.If)
            and old_marker in ast.unparse(normalized_init.body[-1])):
        # Only the exact earlier log block is accepted, never arbitrary code.
        expected_log = ast.parse('if self.config.get("initial_prompt") and model == "small.en":\n    LOG.info("'+old_marker+'")').body[0]
        if shape(normalized_init.body[-1]) == shape(expected_log):
            normalized_init.body.pop()
    if shape(normalized_init) != shape(method(base, '__init__')):
        raise RuntimeError('Installed constructor differs from the reviewed plugin; no files changed')
    lines = source.splitlines(keepends=True)
    segment = ''.join(lines[execute.lineno-1:execute.end_lineno])
    if shape(execute) == shape(expected):
        segment = segment.replace('vad_filter=self.config.get("vad_filter", False)',
                                  'vad_filter=self.config.get("vad_filter", False),\n            initial_prompt=_jarvis_app_initial_prompt(self)')
    else:
        segment = segment.replace('initial_prompt=self.config.get("initial_prompt")',
                                  'initial_prompt=_jarvis_app_initial_prompt(self)')
    if 'initial_prompt=_jarvis_app_initial_prompt(self)' not in segment:
        raise RuntimeError('Unsupported formatting of transcription call; no changes made')
    lines[execute.lineno-1:execute.end_lineno] = [segment]
    # Constructor precedes execute in the reviewed layout.
    lines.insert(init.end_lineno, INIT)
    result = ''.join(lines)+WRAPPER
    compile(result, '<dynamic Whisper plugin>', 'exec')
    verify_forwarding(result)
    return result.encode()


def verify_forwarding(source):
    namespace = {'_jarvis_app_initial_prompt':lambda stt:'Jarvis, Mega.'}
    execute = method(source, 'execute')
    exec(compile(ast.Module(body=[execute],type_ignores=[]),'<execute check>','exec'),namespace)
    class Engine:
        def transcribe(self,audio,**kwargs):
            self.seen = audio, kwargs
            return iter([type('Segment',(),{'text':' result '})()]), None
    class Stub:
        engine=Engine();lang='en-US';beam_size=7;config={'vad_filter':True}
        def audiodata2array(self,audio):return ('same audio',audio)
        def detect_language(self,audio):return 'en',1
    stub=Stub()
    assert namespace['execute'](stub,'audio')=='result'
    assert stub.engine.seen==(('same audio','audio'),{
        'beam_size':7,'condition_on_previous_text':False,'language':'en',
        'vad_filter':True,'initial_prompt':'Jarvis, Mega.'})


PROBE = r"""
import contextlib, io, json, inspect, importlib.util
from importlib.metadata import version
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    from ovos_config import Configuration
    from faster_whisper import WhisperModel
    stt=Configuration().get('stt',{})
    selected=stt.get('ovos-stt-plugin-fasterwhisper',{})
    spec=importlib.util.find_spec('ovos_stt_plugin_fasterwhisper')
    result={'version':version('ovos-stt-plugin-fasterwhisper'), 'path':spec.origin,
            'module':stt.get('module'), 'model':selected.get('model'),
            'hint':selected.get('initial_prompt'),
            'supports_hint':'initial_prompt' in inspect.signature(WhisperModel.transcribe).parameters}
print(json.dumps(result))
"""


def ready(states, updated):
    if states[LISTENER]['ActiveState'] != 'active':
        return
    invocation = snapshot()[LISTENER].get('InvocationID')
    if not invocation:
        raise RuntimeError('Cannot identify restarted listener')
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        result=run(['journalctl','--user','-u',LISTENER,
                    '_SYSTEMD_INVOCATION_ID='+invocation,'--no-pager','-o','cat'],
                   capture_output=True,text=True).stdout
        if 'DinkumVoiceService is ready.' in result and (not updated or MARKER in result):
            return
        time.sleep(.5)
    raise RuntimeError('Listener readiness and dynamic hint activation not confirmed')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read(path):
    return path.read_bytes() if path.exists() else None

def digest(path):
    data = read(path)
    return sha(data) if data is not None else None

def encode(value):
    return (json.dumps(value, indent=2) + '\n').encode()

def safe(home, relative):
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise RuntimeError('Invalid managed path')
    path = home / relative
    for node in [path, *path.parents]:
        if node == home:
            break
        if node.is_symlink():
            raise RuntimeError('Refusing to replace a symlink: ' + str(node))
    return path

def atomic(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)

def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, timeout=kwargs.pop('timeout', 60), **kwargs)

def snapshot():
    states = {}
    for unit in UNITS:
        out = run(['systemctl', '--user', 'show', unit,
                   '--property=ActiveState,SubState,Requires,BindsTo,PartOf,InvocationID'],
                  capture_output=True, text=True).stdout
        states[unit] = dict(line.split('=', 1) for line in out.splitlines() if '=' in line)
    return states

def restore_services(states):
    for unit in UNITS:
        if states[unit]['ActiveState'] == 'active':
            run(['systemctl', '--user', 'start', unit], capture_output=True)
    current = snapshot()
    missing = [u for u in UNITS if states[u]['ActiveState'] == 'active'
               and current[u]['ActiveState'] != 'active']
    if missing:
        raise RuntimeError('Previously active services are not running: ' + ', '.join(missing))

def clear_cache(path):
    if path.suffix == '.py':
        for p in (path.parent / '__pycache__').glob(path.stem + '.*.pyc'):
            p.unlink()

def verify_backup(home, backup, manifest):
    for item in manifest['files']:
        path = safe(home, item['relative'])
        if digest(path) not in (item['before'], item['after']):
            raise RuntimeError('Later edits detected; nothing overwritten: ' + str(path))
        if item['before'] is not None and digest(backup / item['backup']) != item['before']:
            raise RuntimeError('Backup checksum mismatch')

def restore_files(home, backup, manifest):
    verify_backup(home, backup, manifest)
    for item in manifest['files']:
        path = safe(home, item['relative'])
        if item['before'] is None:
            path.unlink(missing_ok=True)
        else:
            atomic(path, (backup / item['backup']).read_bytes(), item['mode'])
        clear_cache(path)

def transaction(home, backup, manifest, payloads, marker, ops=True):
    try:
        if ops:
            run(['systemctl', '--user', 'stop', LISTENER], capture_output=True)
        for item, data in zip(manifest['files'], payloads):
            path = safe(home, item['relative'])
            if digest(path) != item['before']:
                raise RuntimeError('A managed file changed during installation')
            atomic(path, data, item.get('write_mode', item['mode']))
            clear_cache(path)
        if ops:
            restore_services(manifest['services'])
            ready(manifest['services'], True)
            restore_services(manifest['services'])
        atomic(marker, encode({'backup': str(backup)}))
    except BaseException:
        if ops:
            run(['systemctl', '--user', 'stop', LISTENER], capture_output=True)
        try:
            restore_files(home, backup, manifest)
        finally:
            if ops:
                restore_services(manifest['services'])
        if ops:
            ready(manifest['services'], False)
            restore_services(manifest['services'])
        marker.unlink(missing_ok=True)
        print('Previous files restored. Backup retained: ' + str(backup), flush=True)
        raise

def rollback(home, state):
    marker = state / 'latest.json'
    backup = Path(json.loads(marker.read_text())['backup'])
    if not backup.resolve().is_relative_to(state.resolve()):
        raise RuntimeError('Invalid backup location')
    manifest = json.loads((backup / 'manifest.json').read_text())
    verify_backup(home, backup, manifest)
    states = snapshot()
    run(['systemctl', '--user', 'stop', LISTENER], capture_output=True)
    try:
        restore_files(home, backup, manifest)
    finally:
        restore_services(states)
    ready(states, False)
    restore_services(states)
    marker.unlink()
    print('Dynamic Whisper hints rolled back; previous plugin and running services restored.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rollback',action='store_true')
    parser.add_argument('--check',action='store_true',help='Read-only compatibility and hint preview')
    args=parser.parse_args()
    if os.geteuid()==0:raise RuntimeError('Run as your desktop user, without sudo')
    home=Path.home()
    state=safe(home,'.local/state/jarvis/whisper-app-hints')
    state.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (state/'update.lock').open('w') as lock:
        os.chmod(state/'update.lock',0o600)
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.rollback:
            rollback(home,state);return
        info=json.loads(run([home/'.venvs/ovos/bin/python','-c',PROBE],capture_output=True,text=True).stdout)
        if info['module']!=PLUGIN or info['model']!='small.en' or not info['supports_hint']:
            raise RuntimeError('Expected the existing Faster-Whisper small.en with initial_prompt support')
        source=Path(info['path'])
        venv=(home/'.venvs/ovos').resolve()
        if source.is_symlink() or not source.resolve().is_relative_to(venv):
            raise RuntimeError('Plugin must be inside your existing OVOS virtual environment')
        source=safe(home,str(source.relative_to(home)))
        helper=source.with_name('jarvis_app_hints.py')
        config=home/'.config/mycroft/mycroft.conf'
        config_before=config.read_bytes()
        original=source.read_bytes()
        print('Installed Faster-Whisper plugin: '+info['version'],flush=True)
        fixed=b'initial_prompt=self.config.get("initial_prompt")' in original
        print('Previous fixed-hint forwarding: '+('present' if fixed else 'not detected'),flush=True)
        preview,counts=prompt_for(info['hint'],home=home,strict=True)
        print('Hint preview (conservative byte budget): '+str(preview),flush=True)
        print('Names included: '+str(counts['names'])+' / '+str(counts['available_names']),flush=True)
        if MARKER.encode() in original:
            if not (state/'latest.json').is_file():
                raise RuntimeError('Dynamic patch present without its backup record; no changes made')
            backup=Path(json.loads((state/'latest.json').read_text())['backup'])
            manifest=json.loads((backup/'manifest.json').read_text())
            if not all(digest(safe(home,i['relative']))==i['after'] for i in manifest['files']):
                raise RuntimeError('Managed source changed since installation; no files overwritten')
            print('Dynamic hints are installed. Preview only; no services restarted.');return
        updated=patch_source(original)
        if helper.exists():raise RuntimeError('A hint helper already exists; nothing overwritten')
        if args.check:
            print('PASS: compatible transcription code; no plugin, configuration or services changed.');return
        states=snapshot()
        if any(states[u]['ActiveState']!='active' for u in UNITS):
            raise RuntimeError('Start Jarvis first; core, audio and listener must be active')
        if config.read_bytes()!=config_before:
            raise RuntimeError('Voice settings changed during preflight; retry after the other update finishes')
        backup=Path(tempfile.mkdtemp(prefix=time.strftime('%Y%m%dT%H%M%S-'),dir=state))
        files=[];payloads=[]
        for index,(path,data) in enumerate(((helper,(ROOT/'jarvis_app_hints.py').read_bytes()),(source,updated))):
            if path.exists() and path.stat().st_uid!=os.getuid():
                raise RuntimeError('Plugin files must belong to your desktop user')
            path=safe(home,str(path.relative_to(home)))
            before=read(path)
            if path==source and before!=original:raise RuntimeError('Plugin changed during preflight')
            if before is not None:atomic(backup/str(index),before)
            files.append({'relative':str(path.relative_to(home)),'before':sha(before) if before is not None else None,
                          'after':sha(data),'mode':stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600,
                          'backup':str(index)})
            payloads.append(data)
        manifest={'services':states,'files':files}
        atomic(backup/'manifest.json',encode(manifest))
        print('Backup: '+str(backup),flush=True)
        transaction(home,backup,manifest,payloads,state/'latest.json')
        print('PASS: listener ready; dynamic app-name hints active; running voice services restored.')
        print('App and spoken-name changes are read on the next transcription. No model or configuration changed.')
        print('Rollback: python3 '+str(ROOT/'install.py')+' --rollback')


if __name__=='__main__':
    try:main()
    except Exception as error:raise SystemExit('ERROR: '+str(error))
