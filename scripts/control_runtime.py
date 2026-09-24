"""Fixed local operations for the Jarvis desktop window; no GTK dependencies."""
import concurrent.futures
import contextlib
import fcntl
from functools import wraps
import json
import os
from pathlib import Path
import re
import subprocess
import time

UNITS = ('ovos-audio.service', 'ovos-listener.service', 'ovos-core.service')
CORE, LISTENER = UNITS[2], UNITS[1]
MARKERS = {CORE: ('Jarvis configuration ready', 'Skill ovos-skill-jarvis-dispatcher.openvoiceos loaded successfully'),
           LISTENER: ('DinkumVoiceService is ready.',)}


@contextlib.contextmanager
def operation_lock():
    directory=Path.home()/'.local/state/jarvis-ui'
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'controls.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another Jarvis control action is running. Please wait.')
        try:yield
        finally:fcntl.flock(lock,fcntl.LOCK_UN)


def exclusive(function):
    @wraps(function)
    def guarded(*args,**kwargs):
        with operation_lock():return function(*args,**kwargs)
    return guarded


def save_with_lock(work):
    with operation_lock():return work()


def run(args, timeout=15, check=True):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                            timeout=timeout, check=False)
    if check and result.returncode:
        raise RuntimeError((result.stderr or result.stdout or 'Command failed').strip()[-3000:])
    return result


def snapshot():
    states = {}
    for unit in UNITS:
        output = run(['systemctl', '--user', 'show', unit,
                      '--property=ActiveState,SubState,Requires,BindsTo,PartOf,InvocationID']).stdout
        states[unit] = dict(line.split('=', 1) for line in output.splitlines() if '=' in line)
    return states


def restore_active(before):
    failures = []
    for unit in UNITS:
        if before[unit].get('ActiveState') == 'active':
            try:
                run(['systemctl', '--user', 'start', unit], timeout=40)
            except Exception as error:
                failures.append(f'{unit}: {error}')
    current = snapshot()
    missing = [u for u in UNITS if before[u].get('ActiveState') == 'active'
               and current[u].get('ActiveState') != 'active']
    if failures or missing:
        raise RuntimeError('Could not restore services: ' + '; '.join(failures + missing))


def wait_ready(units, report=lambda text: None, timeout=60):
    deadline = time.monotonic() + timeout
    report('Waiting for voice services to report ready…')
    while time.monotonic() < deadline:
        states = snapshot()
        ready = all(states[u].get('ActiveState') == 'active' for u in units)
        for unit in units:
            if unit not in MARKERS:
                continue
            invocation = states[unit].get('InvocationID')
            if not invocation:
                ready = False
                continue
            logs = run(['journalctl', '--user', '-u', unit,
                        '_SYSTEMD_INVOCATION_ID=' + invocation,
                        '--no-pager', '-o', 'cat'], timeout=10).stdout
            ready = ready and any(marker in logs for marker in MARKERS[unit])
        if ready:
            return
        time.sleep(0.5)
    raise RuntimeError('Services have not reported ready. See Maintenance → Recent logs.')


@exclusive
def service_action(action, report=lambda text: None):
    if action not in {'start', 'stop', 'restart', 'commands'}:
        raise ValueError('Unknown service action')
    before = snapshot()  # Includes dependency relations before any mutation.
    active = [u for u in UNITS if before[u].get('ActiveState') == 'active']
    if action in {'restart', 'commands'} and CORE not in active:
        raise RuntimeError('Jarvis is stopped. Choose Start Jarvis first.')
    try:
        if action == 'stop':
            report('Stopping Jarvis…')
            run(['systemctl', '--user', 'stop', *reversed(UNITS)], timeout=45)
            current = snapshot()
            if any(current[u].get('ActiveState') not in {'inactive', 'failed'} for u in UNITS):
                raise RuntimeError('Some voice services are still running')
            return 'Jarvis is stopped.'
        if action in {'restart', 'commands'}:
            report('Stopping voice services…' if action == 'restart' else 'Restarting commands…')
            run(['systemctl', '--user', 'stop', *(reversed(UNITS) if action == 'restart' else [CORE])], timeout=45)
        desired = list(UNITS) if action == 'start' else active
        # Respect a deliberately stopped microphone during a restart.
        for unit in UNITS:
            if unit in desired:
                report('Starting ' + {'ovos-audio.service':'speech', LISTENER:'the microphone', CORE:'commands'}[unit] + '…')
                run(['systemctl', '--user', 'start', unit], timeout=45)
        if action != 'start' and LISTENER not in active:
            run(['systemctl', '--user', 'stop', LISTENER], timeout=30)
        wait_ready(desired, report)
        current = snapshot()
        if not all(current[u].get('ActiveState') == 'active' for u in desired):
            raise RuntimeError('A voice service stopped during startup')
        return 'Jarvis is ready.' if LISTENER in desired else 'Jarvis is ready. Microphone remains paused.'
    except Exception as original:
        report('Recovering previously running services…')
        try:
            restore_active(before)
            if LISTENER not in active:
                run(['systemctl', '--user', 'stop', LISTENER], timeout=30)
            if active:
                wait_ready(active, timeout=30)
        except Exception as recovery:
            raise RuntimeError(f'{original}\nRecovery also needs attention: {recovery}') from original
        raise RuntimeError(f'{original}\nPreviously running services were restored.') from original


@exclusive
def microphone_action():
    before = snapshot()
    active = before[LISTENER].get('ActiveState') == 'active'
    try:
        run(['systemctl', '--user', 'stop' if active else 'start', LISTENER], timeout=40)
        # Restore other components affected by listener dependency relationships.
        for unit in UNITS:
            if unit != LISTENER and before[unit].get('ActiveState') == 'active':
                run(['systemctl', '--user', 'start', unit], timeout=40)
        if active:
            # A dependent service start must not silently reactivate the mic.
            run(['systemctl', '--user', 'stop', LISTENER], timeout=30)
            if snapshot()[LISTENER].get('ActiveState') not in {'inactive', 'failed'}:
                raise RuntimeError('Jarvis microphone is still running')
        else:
            wait_ready([LISTENER])
    except Exception:
        restore_active(before)
        if not active:
            run(['systemctl', '--user', 'stop', LISTENER], timeout=30)
        raise
    return 'Jarvis microphone paused.' if active else 'Jarvis microphone active.'


def status():
    states = snapshot()
    values = {u: v.get('ActiveState', 'unknown') for u, v in states.items()}
    if 'failed' in values.values():
        state = 'failed'
    elif all(v == 'inactive' for v in values.values()):
        state = 'stopped'
    elif values[CORE] == 'active' and values[UNITS[0]] == 'active' and values[LISTENER] == 'inactive':
        state = 'muted'
    elif all(v == 'active' for v in values.values()):
        state = 'ready'
        for unit in MARKERS:
            invocation = states[unit].get('InvocationID')
            if not invocation:
                state = 'starting'; break
            logs = run(['journalctl', '--user', '-u', unit, '_SYSTEMD_INVOCATION_ID='+invocation,
                        '--no-pager', '-o', 'cat'], timeout=10).stdout
            if not any(marker in logs for marker in MARKERS[unit]):
                state = 'starting'; break
    else:
        state = 'starting'
    return {'state':state, 'microphone':values[LISTENER] == 'active', 'services':values}


def read_json(path):
    try:
        value=json.loads(Path(path).read_text())
        return value if isinstance(value,dict) else {}
    except (OSError, ValueError):return {}


def update_available(home=None):
    home=Path(home or Path.home())
    state=home/'.local/state/jarvis'
    current=read_json(state/'current.json'); latest=read_json(state/'updates/latest.json')
    def version(text):
        match=re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)',str(text))
        return tuple(map(int,match.groups())) if match else None
    old,new=version(current.get('version')),version(latest.get('latest'))
    return str(latest['latest']) if latest.get('update_available') is True and old and new and new>old else None


def speech_stop():
    """Issue the established global cancel plus an independent reader stop."""
    python=Path.home()/'.venvs/ovos/bin/python'
    def ovos():
        script='''
from ovos_bus_client import MessageBusClient, Message
import time
bus=MessageBusClient();bus.run_in_thread()
try:
    if not bus.connected_event.wait(3):raise RuntimeError('Voice message bus unavailable')
    bus.emit(Message('mycroft.stop'))
    bus.emit(Message('mycroft.audio.speech.stop'))
    time.sleep(0.15)
finally:bus.close()
'''
        run([python,'-c',script],timeout=8)
    def reader():
        base=['/usr/bin/gdbus','call','--session']
        owner=run(base+['--dest','org.freedesktop.DBus','--object-path','/org/freedesktop/DBus',
                        '--method','org.freedesktop.DBus.NameHasOwner','net.mkiol.SpeechNote'],timeout=3)
        if 'true' not in owner.stdout:return
        base+=['--dest','net.mkiol.SpeechNote','--object-path','/net/mkiol/SpeechNote']
        state=run(base+['--method','org.freedesktop.DBus.Properties.Get','net.mkiol.SpeechNote','TaskState'],timeout=3)
        found=re.search(r'<(\d+)>',state.stdout)
        if found and int(found.group(1)) in {4,5}:
            run(base+['--method','net.mkiol.SpeechNote.InvokeAction','cancel','{}'],timeout=3)
    errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        tasks=[pool.submit(ovos),pool.submit(reader)]
        for future in tasks:
            try:future.result()
            except Exception as error:errors.append(str(error))
    if errors:raise RuntimeError('Stop requested where available. '+ '; '.join(errors))
    return 'Stop requested.'


def maintenance(action):
    commands={
        'health':([str(Path.home()/'.local/bin/jarvis-health-check')],150),
        'report':([str(Path.home()/'.local/bin/jarvis-report')],120),
        'updates':([str(Path.home()/'.local/bin/jarvis-update'),'check'],90),
        'install':([str(Path.home()/'.local/bin/jarvis-update'),'install'],600),
        'logs':(['journalctl','--user',*[x for u in UNITS for x in ('-u',u)],'-n','120','--no-pager'],15),
    }
    if action=='about':
        current=read_json(Path.home()/'.local/state/jarvis/current.json')
        script="from importlib.metadata import distributions; print('\\n'.join(sorted((d.metadata.get('Name','')+' '+d.version) for d in distributions() if d.metadata.get('Name','').lower().startswith('ovos-'))))"
        result=run([Path.home()/'.venvs/ovos/bin/python','-c',script],timeout=15)
        return 'Jarvis '+str(current.get('version','local build'))+'\n\n'+result.stdout
    if action not in commands:raise ValueError('Unknown maintenance action')
    argv,timeout=commands[action]
    if action=='install':
        with operation_lock():
            result=run(argv,timeout=timeout,check=False)
    else:
        result=run(argv,timeout=timeout,check=False)
    text=(result.stdout+'\n'+result.stderr).strip()
    if result.returncode:raise RuntimeError(text[-16000:] or 'Action failed')
    return text[-20000:] or 'Completed.'


@exclusive
def voice_setting(kind, values, report=lambda text: None):
    if kind not in {'wake','shortcuts'}:raise ValueError('Unknown voice setting')
    before=snapshot()
    helper=Path.home()/'.local/bin'/('jarvis-wake-phrase' if kind=='wake' else 'jarvis-listen-shortcut')
    args=['--phrase',values[0]] if kind=='wake' else ['--shortcut',values[0],'--microphone-shortcut',values[1]]
    report('Applying voice settings…')
    try:
        result=run([helper,*args],timeout=90)
    finally:
        if kind=='wake':
            restore_active(before)
            if before[LISTENER].get('ActiveState')!='active':
                run(['systemctl','--user','stop',LISTENER],timeout=30)
    if kind=='wake' and before[LISTENER].get('ActiveState')=='active':wait_ready([LISTENER],report)
    return result.stdout.strip() or 'Voice settings saved.'
