"""Fixed local operations for the Jarvis desktop window; no GTK dependencies."""
import concurrent.futures
import contextlib
import fcntl
from functools import wraps
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from isolation_services import active as isolation_active, control_arguments, state_arguments, journal_arguments, refresh_session

UNITS = ('ovos-audio.service', 'ovos-listener.service', 'ovos-core.service')
CORE, LISTENER = UNITS[2], UNITS[1]
SPEECH_NOTE_HELPER = Path.home() / '.local/bin/jarvis-speechnote-setup'
UNINSTALL_HELPER = Path.home() / '.local/bin/jarvis-uninstall'
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
    result = subprocess.run(control_arguments(args), capture_output=True, text=True,
                            timeout=timeout, check=False)
    if check and result.returncode:
        raise RuntimeError((result.stderr or result.stdout or 'Command failed').strip()[-3000:])
    return result


def sanitise_log_text(text):
    """Redact common private context before logs enter the Control Centre."""

    value = str(text).replace(str(Path.home()), "~")
    username = os.environ.get('USER') or os.environ.get('LOGNAME')
    if username and len(username) > 2:
        value = re.sub(
            rf'(?<![\w-]){re.escape(username)}(?![\w-])', '<user>', value)
    value = re.sub(
        r"(?i)(['\"]?location['\"]?\s*:\s*)\{[^{}\n]{0,500}\}",
        r"\1{<redacted-location>}", value)
    value = re.sub(
        r"(?i)(['\"]?(?:lat|latitude|lon|longitude)['\"]?\s*[:=]\s*)"
        r"-?\d{1,3}(?:\.\d+)?",
        r"\1<redacted-location>", value)
    value = re.sub(
        r'(?i)\b(api[_-]?key|access[_-]?token|authorization|password|secret)'
        r'\s*[:=]\s*[^\s,;]+', r'\1=<redacted>', value)
    return value


def speech_note_status():
    """Inspect the bounded per-user Speech Note integration."""
    result = run([SPEECH_NOTE_HELPER, '--status'], timeout=30, check=False)
    detail = (result.stdout or result.stderr or 'Speech Note status unavailable.').strip()
    return {'installed': result.returncode == 0, 'detail': detail}


def speech_note_action(action):
    """Open or explicitly install Speech Note through the packaged helper."""
    if action not in {'open', 'install', 'guide'}:
        raise ValueError('Unknown Speech Note action')
    arguments = [SPEECH_NOTE_HELPER, '--' + action]
    if action == 'install':
        arguments.append('--yes')
    result = run(arguments, timeout=1800)
    text = result.stdout.strip() or 'Speech Note setup complete.'
    if action == 'install':
        opened = run([SPEECH_NOTE_HELPER, '--open'], timeout=30)
        text += '\n' + (opened.stdout.strip() or 'Speech Note opened.')
    return text


def uninstall_jarvis(remove_model=False, remove_settings=False, remove_ovos=False):
    """Run the fixed local uninstaller with only explicit destructive options."""
    arguments=[UNINSTALL_HELPER,'--yes']
    if remove_model:arguments.append('--remove-model')
    if remove_settings:arguments.append('--remove-settings')
    if remove_ovos:arguments.append('--remove-ovos')
    result=run(arguments,timeout=1800)
    return result.stdout.strip() or 'Jarvis was removed.'


def snapshot():
    states = {}
    for unit in UNITS:
        output = run(state_arguments(unit,'ActiveState','SubState','Requires','BindsTo','PartOf','InvocationID')).stdout
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


def wait_ready(units, report=lambda text: None, timeout=180):
    deadline = time.monotonic() + timeout
    next_report = time.monotonic() + 15
    report('Waiting for voice services to report ready…')
    while time.monotonic() < deadline:
        states = snapshot()
        if any(states[u].get('ActiveState') == 'failed' for u in units):
            raise RuntimeError('A voice service failed during startup. See Maintenance → Recent logs.')
        ready = all(states[u].get('ActiveState') == 'active' for u in units)
        for unit in units:
            if unit not in MARKERS:
                continue
            invocation = states[unit].get('InvocationID')
            if not invocation:
                ready = False
                continue
            logs = run(journal_arguments(unit,invocation), timeout=10).stdout
            ready = ready and any(marker in logs for marker in MARKERS[unit])
        if ready:
            return
        if time.monotonic() >= next_report:
            report('Voice services are still loading; waiting for readiness…')
            next_report = time.monotonic() + 15
        time.sleep(0.5)
    raise RuntimeError('Services have not reported ready. See Maintenance → Recent logs.')


@exclusive
def service_action(action, report=lambda text: None):
    if action not in {'start', 'stop', 'restart', 'commands'}:
        raise ValueError('Unknown service action')
    if action != 'stop':
        from isolation_install import installation_blocked
        if installation_blocked():
            raise RuntimeError('An installation needs recovery. Jarvis remains stopped; protection was not disabled.')
    if action!='stop':refresh_session()
    before = snapshot()  # Includes dependency relations before any mutation.
    active = [u for u in UNITS if before[u].get('ActiveState') == 'active']
    if action in {'restart', 'commands'} and CORE not in active:
        raise RuntimeError('Jarvis is stopped. Choose Start Jarvis first.')
    try:
        if action=='start' and isolation_active():
            run(['systemctl','--user','start','ovos.service'],timeout=45)
        if action == 'stop':
            report('Stopping Jarvis…')
            run(['systemctl', '--user', 'stop', *reversed(UNITS)], timeout=45)
            current = snapshot()
            if any(current[u].get('ActiveState') not in {'inactive', 'failed'} for u in UNITS):
                raise RuntimeError('Some voice services are still running')
            if any(current[u].get('ActiveState') == 'failed' for u in UNITS):
                raise RuntimeError('Voice services stopped with a shutdown failure. See Maintenance → Recent logs.')
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
        if action == 'stop':
            # A Stop request must never recover by starting voice again.
            raise RuntimeError(str(original)) from original
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
    refresh_session()
    before = snapshot()
    active = before[LISTENER].get('ActiveState') == 'active'
    try:
        if not active and isolation_active():run(['systemctl','--user','start','ovos.service'],timeout=45)
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
            logs = run(journal_arguments(unit,invocation), timeout=10).stdout
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


def audio_settings():
    listener=read_json(Path.home()/'.config/mycroft/mycroft.conf').get('listener',{})
    listener=listener if isinstance(listener,dict) else {}
    value=listener.get('barge_in_volume',20)
    try:value=int(value)
    except (TypeError,ValueError):value=20
    return {'enabled':listener.get('fake_barge_in',True) is True,
            'volume':min(50,max(10,value))}


def atomic_json(path,value,mode=None):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    mode=mode if mode is not None else (path.stat().st_mode & 0o777 if path.exists() else 0o600)
    descriptor,name=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.new',dir=path.parent)
    temporary=Path(name)
    try:
        with os.fdopen(descriptor,'w',encoding='utf-8') as output:
            json.dump(value,output,indent=2,sort_keys=True);output.write('\n')
            output.flush();os.fsync(output.fileno())
        temporary.chmod(mode);temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True);raise


def update_status(home=None):
    home=Path(home or Path.home())
    state=home/'.local/state/jarvis'
    current=read_json(state/'current.json'); latest=read_json(state/'updates/latest.json')
    def version(text):
        match=re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)(?:rc(\d+))?',str(text))
        if not match:return None
        major,minor,patch,candidate=match.groups()
        return (int(major),int(minor),int(patch),0 if candidate else 1,
                int(candidate) if candidate else 0)
    installed=str(current.get('version','Unknown'))
    newest=str(latest.get('latest','Not checked'))
    old,new=version(current.get('version')),version(latest.get('latest'))
    available=bool(latest.get('update_available') is True and old and new and new>old)
    checked=bool(latest.get('check_succeeded') is True and old and new)
    failed=latest.get('check_succeeded') is False
    return {'installed':installed, 'latest':newest,
            'release_date':str(latest.get('release_date','')),
            'available':available and not failed, 'checked':checked, 'failed':failed}


def update_available(home=None):
    information=update_status(home)
    return information['latest'] if information['available'] else None


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


def _run_cancellable_update(arguments, cancel_event, timeout=600):
    """Run the fixed updater command in its own cancellable process group."""
    process = subprocess.Popen(
        [str(value) for value in arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        close_fds=True,
    )
    deadline = time.monotonic() + timeout
    while True:
        try:
            stdout, stderr = process.communicate(timeout=0.25)
            return subprocess.CompletedProcess(
                arguments, process.returncode, stdout, stderr)
        except subprocess.TimeoutExpired:
            if cancel_event.is_set():
                reason = 'Update cancelled. No further update steps will run.'
            elif time.monotonic() >= deadline:
                reason = 'Update timed out and was stopped.'
            else:
                continue

        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()
        detail = (stdout + '\n' + stderr).strip()
        raise RuntimeError(reason + (('\n' + detail[-12000:]) if detail else ''))


def maintenance(action, cancel_event=None):
    commands={
        'health':([str(Path.home()/'.local/bin/jarvis-health-check')],150),
        'report':([str(Path.home()/'.local/bin/jarvis-report')],120),
        'updates':([str(Path.home()/'.local/bin/jarvis-update'),'check'],90),
        # The Control Centre has already shown its own confirmation dialog.
        # Its subprocess has no terminal on which to answer the CLI prompt.
        'install':([str(Path.home()/'.local/bin/jarvis-update'),'install','--yes'],600),
        'logs':(['journalctl','--user',*[x for u in UNITS for x in ('-u',u)],'-n','120','--no-pager'],15),
    }
    if action=='about':
        current=read_json(Path.home()/'.local/state/jarvis/current.json')
        script="from importlib.metadata import distributions; print('\\n'.join(sorted((d.metadata.get('Name','')+' '+d.version) for d in distributions() if d.metadata.get('Name','').lower().startswith('ovos-'))))"
        result=run([Path.home()/'.venvs/ovos/bin/python','-c',script],timeout=15)
        return 'Jarvis '+str(current.get('version','local build'))+'\n\n'+result.stdout
    if action not in commands:raise ValueError('Unknown maintenance action')
    argv,timeout=commands[action]
    if action=='logs' and isolation_active():
        argv=['journalctl',*[x for u in UNITS for x in ('-u',state_arguments(u)[3])],'-n','120','--no-pager']
    if action=='install':
        with operation_lock():
            result=(_run_cancellable_update(argv,cancel_event,timeout)
                    if cancel_event is not None else
                    run(argv,timeout=timeout,check=False))
    else:
        result=run(argv,timeout=timeout,check=False)
    text=(result.stdout+'\n'+result.stderr).strip()
    if result.returncode:raise RuntimeError(text[-16000:] or 'Action failed')
    if action == 'logs':
        text = sanitise_log_text(text)
    return text[-20000:] or 'Completed.'


def relaunch_control_center(wait_pid=None):
    """Start the installed post-update GUI after this process has exited."""
    helper = Path(__file__).with_name('relaunch-control-center.py')
    launcher = Path.home()/'.local/bin/jarvis-setup'
    if not helper.is_file() or not launcher.is_file():
        raise RuntimeError('Updated Control Centre launcher is unavailable')
    process = subprocess.Popen(
        [sys.executable, str(helper), '--wait-pid',
         str(wait_pid or os.getpid()), '--launcher', str(launcher)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    return process.pid


@exclusive
def voice_setting(kind, values, report=lambda text: None):
    if kind not in {'wake','shortcuts','audio'}:raise ValueError('Unknown voice setting')
    before=snapshot()
    if kind=='audio':
        if len(values)!=2 or not isinstance(values[0],bool):
            raise ValueError('Invalid background-audio setting')
        try:volume=int(values[1])
        except (TypeError,ValueError):raise ValueError('Listening volume must be a number')
        if volume<10 or volume>50 or volume%5:
            raise ValueError('Listening volume must be 10–50% in five-point steps')
        path=Path.home()/'.config/mycroft/mycroft.conf'
        original=path.read_bytes();mode=path.stat().st_mode & 0o777
        try:config=json.loads(original)
        except (TypeError,ValueError):raise ValueError('OVOS configuration is not valid JSON')
        if not isinstance(config,dict):raise ValueError('OVOS configuration root is invalid')
        listener=config.setdefault('listener',{})
        if not isinstance(listener,dict):raise ValueError('OVOS listener settings are invalid')
        listener['fake_barge_in']=values[0]
        listener['barge_in_volume']=volume
        listener['instant_listen']=False
        if listener.get('barge_in_delay')==0.25:listener.pop('barge_in_delay')
        report('Saving background-audio settings…')
        try:
            atomic_json(path,config,mode)
            if before[LISTENER].get('ActiveState')=='active':
                run(['systemctl','--user','restart',LISTENER],timeout=45)
                restore_active(before);wait_ready([LISTENER],report)
        except Exception:
            descriptor,name=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.restore',dir=path.parent)
            with os.fdopen(descriptor,'wb') as output:
                output.write(original);output.flush();os.fsync(output.fileno())
            temporary=Path(name);temporary.chmod(mode);temporary.replace(path)
            if before[LISTENER].get('ActiveState')=='active':
                run(['systemctl','--user','restart',LISTENER],timeout=45)
            restore_active(before)
            raise
        return 'Background audio while listening saved.'
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
