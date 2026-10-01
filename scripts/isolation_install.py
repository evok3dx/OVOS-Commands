#!/usr/bin/env python3
"""Normal-user installation coordinator; privilege is limited to fixed native data.

Keep policies and relays installed while managed code is replaced. A private,
process-bound journal authorises only this transaction's install/rollback, never
uninstall or arbitrary remaining native data. Interrupted transactions fail closed.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import secrets
import signal
import stat
import subprocess
import sys
import tempfile

from isolation_services import COMPONENTS, LOGICAL, active, regular
from prepare_core_isolation import render, private_file, properties, owned_paths
import private_ollama as model

ROOT = Path(__file__).resolve().parents[1]
CHOICE = Path('.config/jarvis/network-isolation.json')
JOURNAL = Path('.local/state/jarvis/isolation-install/current.json')
EXPLANATION = ('Recommended. Administrator approval is needed to block internet access '
               'for Jarvis voice processing and its dedicated local model. '
               'Weather and music stay online.')


def atomic(path, value):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Installation state must be regular')
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists():
        regular(path, private=True, limit=200000)
    fd, name = tempfile.mkstemp(prefix='.isolation-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def read_choice(home):
    path = home / CHOICE
    if not path.exists() and not path.is_symlink():
        return None
    value = json.loads(regular(path, private=True, limit=8192))
    if value.get('schema_version') != 1 or type(value.get('enabled')) is not bool:
        raise ValueError('Existing isolation preference needs review')
    return value


def select(home, existing, explicit=None):
    saved = read_choice(home)
    activated = active(home)
    if saved is not None:
        enabled = saved['enabled']
        if enabled != activated:
            raise RuntimeError('Saved isolation choice and activation disagree. Repair before upgrading; no automatic downgrade.')
    elif existing:
        enabled = activated
    else:
        enabled = None
    if enabled is not None:
        if explicit is not None and explicit != enabled:
            raise RuntimeError('Upgrades preserve the existing isolation choice. Change protection separately, after review.')
        print('Existing network isolation choice will be preserved: ' + ('enabled.' if enabled else 'disabled.'))
        return enabled, saved or {'schema_version': 1, 'enabled': enabled}
    if explicit is not None:
        return explicit, {'schema_version': 1, 'enabled': explicit}
    print(EXPLANATION)
    if sys.stdin.isatty() and sys.stdout.isatty():
        while True:
            answer = input('Enable network isolation? [Y/n] ').strip().lower()
            if answer in ('', 'y', 'yes', 'n', 'no'):
                enabled = answer not in ('n', 'no')
                return enabled, {'schema_version': 1, 'enabled': enabled}
    if os.environ.get('DISPLAY'):
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
        dialog = Gtk.Dialog(title='Jarvis installation')
        dialog.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Continue', Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        box.set_border_width(20)
        choice = Gtk.CheckButton(label='Enable network isolation (recommended)')
        choice.set_active(True)
        box.pack_start(choice, False, False, 8)
        label = Gtk.Label(label=EXPLANATION)
        label.set_line_wrap(True)
        label.set_max_width_chars(60)
        box.pack_start(label, False, False, 8)
        dialog.show_all()
        response = dialog.run()
        enabled = choice.get_active()
        dialog.destroy()
        if response != Gtk.ResponseType.OK:
            raise RuntimeError('Installation cancelled; protection was not changed')
        return enabled, {'schema_version': 1, 'enabled': enabled}
    raise RuntimeError('Choose --isolation or --no-isolation for unattended first installation. No administrator prompt was attempted.')


def process_start(pid):
    raw = Path('/proc', str(pid), 'stat').read_text()
    return raw.rsplit(')', 1)[1].split()[19]


def ancestor(pid):
    current = os.getpid()
    for _ in range(32):
        if current == pid:
            return True
        text = Path('/proc', str(current), 'status').read_text()
        values = dict(line.split(':', 1) for line in text.splitlines() if ':' in line)
        current = int(values['PPid'].strip())
        if current <= 0:
            break
    return False


def authorised_transaction(operation, home):
    if operation not in {'install', 'rollback'} or home != Path.home():
        raise RuntimeError('Only the active managed installation/rollback can use this boundary')
    journal = home / JOURNAL
    if os.environ.get('JARVIS_ISOLATION_TRANSACTION') != str(journal):
        raise ValueError('Unexpected installation journal')
    value = json.loads(regular(journal, private=True, limit=200000))
    pid = value.get('pid')
    if (value.get('uid') != os.getuid() or type(pid) is not int or pid <= 0
            or value.get('schema_version') != 1 or not isinstance(value.get('token'), str)
            or len(value['token']) < 32
            or value.get('token') != os.environ.get('JARVIS_ISOLATION_TOKEN')
            or value.get('phase') not in {'updating', 'recovering'}
            or process_start(pid) != value.get('process_start') or not ancestor(pid)):
        raise RuntimeError('Installation authorisation is stale or belongs to another process')
    account = pwd.getpwuid(os.getuid())
    deployment = home / '.local/src/ovos-skill-jarvis-dispatcher'
    expected_units, _, _ = render(account.pw_uid, account.pw_gid, account.pw_name,
                                   home, deployment, value.get('original_binary'))
    # Fresh installs have no native units until commit; upgraded units remain
    # restricted and stopped. Never accept arbitrary files from the journal.
    desired, _, _ = render(account.pw_uid, account.pw_gid, account.pw_name,
                           home, deployment, value['binary'])
    for name in set(expected_units) | set(desired):
        path = Path('/etc/systemd/system') / name
        if not path.exists() and not path.is_symlink():
            if value.get('was_active') and name in expected_units:
                raise RuntimeError('Previous isolation policy disappeared; installation blocked')
            continue
        body = regular(path, owner=0)
        if body not in {expected_units.get(name), desired.get(name)}:
            raise RuntimeError('Unexpected native policy; installation remains blocked')
        props = properties('--system', name, 'ActiveState', 'DropInPaths', 'User', 'Group')
        if (props.get('ActiveState') not in {'inactive', 'failed'} or props.get('DropInPaths')
                or props.get('User') != str(os.getuid()) or props.get('Group') != str(account.pw_gid)):
            raise RuntimeError('Native identity, overrides or running state changed')
    legacy = Path('/etc/systemd/system/ollama.service.d/90-jarvis-isolation.conf')
    if legacy.exists() or legacy.is_symlink():
        from prepare_model_isolation import POLICY
        if not value.get('was_active') or regular(legacy, owner=0) != POLICY:
            raise RuntimeError('Unrelated general Ollama policy needs review')
    return value


def installation_blocked(home=None):
    """A dead coordinator leaves workers blocked until deliberate recovery."""
    path = Path(home or Path.home()) / JOURNAL
    if not path.exists() and not path.is_symlink():
        return False
    value = json.loads(regular(path, private=True, limit=200000))
    return value.get('phase') not in {'checking', 'recovering-ready'}


class Native:
    """Only root-owned native tools, fixed data destinations, no privileged script."""
    def __init__(self):
        self.prefix = None

    def approve(self):
        if self.prefix is not None:
            return
        if sys.stdin.isatty():
            subprocess.run(['/usr/bin/sudo', '-v'], check=True)
            self.prefix = ['/usr/bin/sudo', '-n', '--']
        elif os.environ.get('DISPLAY') and Path('/usr/bin/pkexec').is_file():
            self.prefix = ['/usr/bin/pkexec']
        else:
            raise RuntimeError('Administrator approval is required for native isolation setup. Run this installer in your desktop terminal.')

    def run(self, tool, *args, capture=False, check=True):
        if tool not in {'install', 'rm', 'stat', 'sha256sum', 'systemctl'}:
            raise ValueError('Unreviewed administrator operation')
        path = Path('/usr/bin') / tool
        for part in (path.resolve(strict=True), *path.resolve().parents):
            info = part.stat()
            if info.st_uid != 0 or info.st_mode & 0o022:
                raise RuntimeError('Native administrator tool ownership needs review')
        self.approve()
        return subprocess.run([*self.prefix, str(path), *map(str, args)],
                              check=check, capture_output=capture, text=True, timeout=120)


def native_snapshot(account, home, deployment, saved, enabled):
    binary = saved.get('model_binary') if saved else None
    previous, rule, _ = render(account.pw_uid, account.pw_gid, account.pw_name,
                                home, deployment, binary)
    was_active = active(home)
    result = {}
    for name in [*previous, model.unit_name()]:
        path = Path('/etc/systemd/system') / name
        if was_active and name in previous:
            if regular(path, owner=0) != previous[name]:
                raise RuntimeError('Existing native service differs from reviewed policy. Nothing was replaced.')
            props = properties('--system', name, 'ActiveState', 'DropInPaths', 'User', 'Group')
            if (props.get('DropInPaths') or props.get('User') != str(account.pw_uid)
                    or props.get('Group') != str(account.pw_gid)
                    or props.get('ActiveState') not in {'active', 'inactive', 'failed'}):
                raise RuntimeError('Existing worker identity or overrides need review')
            result[name] = previous[name]
        elif path.exists() or path.is_symlink():
            raise RuntimeError('Unowned native Jarvis model/service data needs review')
    return result, rule, binary


def verify_rule(native, expected):
    path = Path('/etc/polkit-1/rules.d') / f'90-jarvis-v4-{os.getuid()}.rules'
    result = native.run('stat', '--format=%u %f', '--', path, capture=True, check=False)
    if expected is None:
        if result.returncode == 0:
            raise RuntimeError('An existing native rule needs review; refusing replacement')
        # Native stat must distinguish absence from inaccessible data, without
        # publishing error content that might include private paths.
        if 'No such file' not in result.stderr:
            raise RuntimeError('Could not verify native rule absence')
        return
    values = result.stdout.strip().split()
    if result.returncode or len(values) != 2 or values[0] != '0':
        raise RuntimeError('Native rule ownership cannot be confirmed')
    mode = int(values[1], 16)
    if not stat.S_ISREG(mode) or mode & 0o022:
        raise RuntimeError('Native rule permissions need review')
    result = native.run('sha256sum', '--', path, capture=True)
    if result.stdout.split()[0] != hashlib.sha256(expected.encode()).hexdigest():
        raise RuntimeError('Native rule differs from reviewed policy; refusing replacement')


def apply_native(native, units, rule, originals, old_rule, directory):
    changed = units != originals or rule != old_rule
    if not changed:
        return False
    native.approve()
    verify_rule(native, old_rule if originals else None)
    directory.mkdir(mode=0o700)
    for name, body in units.items():
        path = Path('/etc/systemd/system') / name
        if name in originals:
            if regular(path, owner=0) != originals[name]:
                raise RuntimeError('Native data changed before update')
        elif path.exists() or path.is_symlink():
            raise RuntimeError('Native destination appeared during setup')
        private_file(directory / name, body)
    rule_name = f'90-jarvis-v4-{os.getuid()}.rules'
    private_file(directory / rule_name, rule)
    for name in units:
        native.run('install', '-o', 'root', '-g', 'root', '-m', '0644', '--',
                   directory / name, Path('/etc/systemd/system') / name)
    native.run('install', '-o', 'root', '-g', 'root', '-m', '0644', '--',
               directory / rule_name, Path('/etc/polkit-1/rules.d') / rule_name)
    native.run('systemctl', 'daemon-reload')
    return True


def stop_workers(home, was_active):
    from control_runtime import service_action
    desired = []
    if was_active:
        for unit, part in LOGICAL.items():
            name = f'jarvis-v4-{os.getuid()}-{part}.service'
            if properties('--system', name, 'ActiveState').get('ActiveState') == 'active':
                desired.append(unit)
    else:
        for unit in LOGICAL:
            if properties('--user', unit, 'ActiveState').get('ActiveState') == 'active':
                desired.append(unit)
    if was_active or desired:
        service_action('stop', print)
    return desired


def restore_running(desired):
    from control_runtime import run, wait_ready
    if desired:
        run(['systemctl', '--user', 'start', *desired], timeout=45)
        wait_ready(desired, print, timeout=180)


def run_child(command, environment):
    child = subprocess.Popen(command, env=environment, start_new_session=True)
    try:
        return child.wait()
    except BaseException:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=10)
        raise


def tree_identity(root):
    if not root.exists():
        return None
    values = {}
    for path in sorted(root.rglob('*')):
        if '.git' in path.parts or '__pycache__' in path.parts or path.suffix == '.pyc':
            continue
        if path.is_symlink():
            raise RuntimeError('Managed source contains a symlink; review before upgrading')
        if path.is_file():
            if path.stat().st_size > 16_000_000:
                raise RuntimeError('Managed source contains an unexpected large file')
            values[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return values


def record_backup(home, backup):
    authorised_transaction('install', home)
    base = home / '.local/state/jarvis/backups'
    if base not in backup.parents or any(p.is_symlink() for p in (backup, *backup.parents)):
        raise ValueError('Unexpected managed backup path')
    if not backup.is_dir() or backup.stat().st_uid != os.getuid():
        raise ValueError('Managed backup must be user-owned')
    state = home / JOURNAL
    journal = json.loads(regular(state, private=True, limit=200000))
    if journal.get('backup') not in (None, str(backup)):
        raise ValueError('Managed backup identity changed')
    journal['backup'] = str(backup)
    atomic(state, journal)


def recover_transaction(home, journal, native):
    account = pwd.getpwuid(os.getuid())
    deployment = home / '.local/src/ovos-skill-jarvis-dispatcher'
    binary = journal['binary']
    original_binary = journal.get('original_binary')
    was_active = journal['was_active']
    native_started = journal.get('native_started', False)
    previous_desired = journal['previous_desired']
    token = journal['token']
    state = home / JOURNAL
    environment = {**os.environ, 'JARVIS_ISOLATION_COORDINATED': '1',
                   'JARVIS_ISOLATION_TRANSACTION': str(state),
                   'JARVIS_ISOLATION_TOKEN': token}
    old_router = home / '.config/jarvis/router.json'
    old_router_text = journal['original_router']
    backup = Path(journal['backup']) if journal.get('backup') else None
    if backup is not None:
        base = home / '.local/state/jarvis/backups'
        if base not in backup.parents or any(p.is_symlink() for p in (backup, *backup.parents)):
            raise RuntimeError('Recovery backup path needs review')
    originals, old_rule, _ = render(account.pw_uid, account.pw_gid, account.pw_name,
                                   home, deployment, original_binary)
    if not was_active:
        originals = {}
    units, rule, _ = render(account.pw_uid, account.pw_gid, account.pw_name,
                           home, deployment, binary)
    journal['phase'] = 'recovering'
    atomic(state, journal)
    try:
        from control_runtime import service_action
        service_action('stop', print)
        if native_started:
            native.run('systemctl', 'stop', *units)
            # Remove only unchanged new files; restore only exact reviewed originals.
            recovery = state.parent / ('restore-' + secrets.token_hex(8))
            recovery.mkdir(mode=0o700)
            for name, body in units.items():
                path = Path('/etc/systemd/system') / name
                if not path.exists():
                    continue
                if regular(path, owner=0) not in {body, originals.get(name)}:
                    raise RuntimeError('Native recovery found changed data; workers remain stopped')
                if name in originals:
                    private_file(recovery / name, originals[name])
                    native.run('install', '-o', 'root', '-g', 'root', '-m', '0644', '--', recovery / name, path)
                else:
                    native.run('rm', '--', path)
            rule_path = Path('/etc/polkit-1/rules.d') / f'90-jarvis-v4-{os.getuid()}.rules'
            # A partial write may leave the old or new rule; neither permits arbitrary services.
            result = native.run('sha256sum', '--', rule_path, capture=True, check=False)
            digest = result.stdout.split()[:1]
            accepted = [hashlib.sha256(text.encode()).hexdigest() for text in (rule, old_rule) if text]
            if digest and digest[0] not in accepted:
                raise RuntimeError('Native rule changed during recovery; review required')
            if originals:
                private_file(recovery / rule_path.name, old_rule)
                native.run('install', '-o', 'root', '-g', 'root', '-m', '0644', '--', recovery / rule_path.name, rule_path)
            elif digest:
                native.run('rm', '--', rule_path)
            native.run('systemctl', 'daemon-reload')
        if not was_active and active(home):
            # Mapping files were created only by this transaction and have not been changed.
            _, _, dropins = render(account.pw_uid, account.pw_gid, account.pw_name, home, deployment, binary)
            for path, body in zip(owned_paths(dropins), dropins.values()):
                if regular(path, private=True) != body:
                    raise RuntimeError('Isolation relay changed during recovery')
                path.unlink()
            for name in ('active.json', 'session.env'):
                (home / '.local/state/jarvis/isolation' / name).unlink()
            subprocess.run(['/usr/bin/systemctl', '--user', 'daemon-reload'], check=True)
        if tree_identity(deployment) != journal['original_tree']:
            if backup is None:
                raise RuntimeError('Deployment changed without a complete backup; manual recovery required')
            subprocess.run(['bash', str(ROOT / 'scripts/rollback.sh'), str(backup), '--no-restart'],
                           env=environment, check=True)
        if tree_identity(deployment) != journal['original_tree']:
            raise RuntimeError('Previous source identity did not restore; workers remain stopped')
        if old_router_text is None:
            old_router.unlink(missing_ok=True)
        else:
            atomic(old_router, json.loads(old_router_text))
        journal['phase'] = 'recovering-ready'
        atomic(state, journal)
        if original_binary and previous_desired:
            subprocess.run(['/usr/bin/systemctl', '--system', '--no-ask-password', 'start', model.unit_name()], check=True)
            model.wait_model()
        restore_running(previous_desired)
        previous_choice = journal.get('original_choice')
        if previous_choice is None:
            (home / CHOICE).unlink(missing_ok=True)
        else:
            atomic(home / CHOICE, previous_choice)
        state.unlink()
    except BaseException:
        journal['phase'] = 'blocked'
        atomic(state, journal)
        print('Recovery could not finish. Workers stay stopped and the journal is retained for review.', file=sys.stderr)
        raise


def resume_recovery(home):
    if os.getuid() <= 0 or home != Path.home():
        raise RuntimeError('Recover as the normal desktop user, without sudo')
    state = home / JOURNAL
    journal = json.loads(regular(state, private=True, limit=200000))
    if journal.get('schema_version') != 1 or journal.get('uid') != os.getuid():
        raise RuntimeError('Recovery journal identity needs review')
    old_pid = journal.get('pid')
    try:
        alive = process_start(old_pid) == journal.get('process_start')
    except (FileNotFoundError, ProcessLookupError):
        alive = False
    if alive:
        raise RuntimeError('The installation coordinator is still running. Wait or cancel it first.')
    # The generated native templates are the only acceptable policy, even when
    # the previous coordinator was killed and its source changed.
    if type(journal.get('was_active')) is not bool or not isinstance(journal.get('previous_desired'), list):
        raise ValueError('Recovery state needs review')
    if any(unit not in LOGICAL for unit in journal['previous_desired']):
        raise ValueError('Recovery cannot start an unreviewed service')
    model.verify_executable(journal['binary'])
    journal.update(pid=os.getpid(), process_start=process_start(os.getpid()),
                   token=secrets.token_urlsafe(32), phase='recovering')
    atomic(state, journal)
    os.environ.update(JARVIS_ISOLATION_TRANSACTION=str(state), JARVIS_ISOLATION_TOKEN=journal['token'])
    authorised_transaction('rollback', home)
    recover_transaction(home, journal, Native())
    print('Previous Jarvis deployment and isolation choice restored.')
    return 0


def run_install(arguments, home):
    if os.getuid() <= 0 or os.getuid() != os.geteuid():
        raise RuntimeError('Run the installer as the desktop user, never with sudo')
    if home != Path.home() or pwd.getpwuid(os.getuid()).pw_dir != str(home):
        raise RuntimeError('Native isolation setup must use the current desktop account home')
    account = pwd.getpwuid(os.getuid())
    existing = any((home / name).exists() for name in (
        '.local/src/ovos-skill-jarvis-dispatcher', '.config/jarvis/capabilities.json',
        '.config/jarvis/profile.json'))
    explicit = None
    forwarded = []
    for arg in arguments:
        if arg in {'--isolation', '--no-isolation'}:
            value = arg == '--isolation'
            if explicit is not None and explicit != value:
                raise ValueError('Choose one isolation option')
            explicit = value
        else:
            forwarded.append(arg)
    enabled, saved = select(home, existing, explicit)
    if (home / JOURNAL).exists() or (home / JOURNAL).is_symlink():
        raise RuntimeError('An interrupted installation journal remains. Use the recorded recovery transaction; do not delete the guard.')
    if not enabled:
        from isolation_services import guard_deployment
        guard_deployment('install', home)
        environment = {**os.environ, 'JARVIS_ISOLATION_COORDINATED': '1'}
        status = subprocess.run(['bash', str(ROOT / 'scripts/install.sh'), *forwarded], env=environment).returncode
        if status == 0:
            atomic(home / CHOICE, saved)
        return status
    deployment = home / '.local/src/ovos-skill-jarvis-dispatcher'
    originals, old_rule, original_binary = native_snapshot(account, home, deployment, saved, enabled)
    was_active = active(home)
    if not was_active:
        from isolation_services import guard_deployment
        guard_deployment('install', home)
    binary = model.verify_executable(original_binary) if original_binary else model.executable()
    # Preparing the model is the only online step, before policy activation.
    # An already private model is verified locally without consulting general Ollama.
    if not (model.private_root(home) / 'models' / model.MANIFEST).exists():
        subprocess.run([sys.executable, str(ROOT / 'scripts/qwen-setup.py'), '--prepare'], check=True)
    model.prepare_models(home)
    units, rule, _ = render(account.pw_uid, account.pw_gid, account.pw_name, home, deployment, binary)
    native = Native()
    if originals != units or old_rule != rule:
        print('Setting up the dedicated offline model requires administrator approval for fixed service data.')
        native.approve()
        verify_rule(native, old_rule if originals else None)
    state = home / JOURNAL
    state.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = state.parent / 'operation.lock'
    if lock_path.is_symlink():
        raise ValueError('Installation lock must be regular')
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        old_router = home / '.config/jarvis/router.json'
        old_router_text = regular(old_router, private=True) if old_router.exists() else None
        token = secrets.token_urlsafe(32)
        journal = {'schema_version': 1, 'uid': os.getuid(), 'pid': os.getpid(),
                   'process_start': process_start(os.getpid()), 'token': token,
                   'phase': 'updating', 'was_active': was_active,
                   'binary': binary, 'original_binary': original_binary,
                   'original_tree': tree_identity(deployment)}
        desired = stop_workers(home, was_active)
        previous_desired = desired[:]
        journal.update(original_router=old_router_text, original_choice=read_choice(home),
                       previous_desired=previous_desired, native_started=False)
        if not existing and '--no-restart' not in forwarded:
            desired = list(LOGICAL)
        if '--no-restart' in forwarded:
            desired = []
        if original_binary:
            subprocess.run(['/usr/bin/systemctl', '--system', '--no-ask-password',
                            'stop', model.unit_name()], check=True)
        model.require_free_port()
        atomic(state, journal)
        environment = {**os.environ, 'JARVIS_ISOLATION_COORDINATED': '1',
                       'JARVIS_ISOLATION_TRANSACTION': str(state), 'JARVIS_ISOLATION_TOKEN': token}
        previous_environment = {key: os.environ.get(key) for key in (
            'JARVIS_ISOLATION_TRANSACTION', 'JARVIS_ISOLATION_TOKEN')}
        os.environ.update({key: environment[key] for key in previous_environment})
        native_started = False
        backup = None
        try:
            print('Updating managed Jarvis files while network policies remain installed…')
            status = run_child(['bash', str(ROOT / 'scripts/install.sh'), *forwarded], environment)
            if status:
                raise RuntimeError('Managed installation failed; previous deployment recovery is required')
            current = json.loads(regular(home / '.local/state/jarvis/current.json', private=True))
            backup = Path(current['rollback'])
            base = home / '.local/state/jarvis/backups'
            if base not in backup.parents or any(p.is_symlink() for p in (backup, *backup.parents)):
                raise RuntimeError('Deployment backup identity needs review')
            journal['backup'] = str(backup)
            atomic(state, journal)
            # Mark before the first native write so partial writes also roll back.
            native_started = originals != units or old_rule != rule
            journal['native_started'] = native_started
            atomic(state, journal)
            apply_native(native, units, rule, originals, old_rule, state.parent / ('native-' + token[:12]))
            if not was_active:
                from prepare_core_isolation import activate
                candidate = home / 'Downloads/jarvis-v4-isolation-candidates' / secrets.token_hex(8)
                subprocess.run([str(home / '.venvs/ovos/bin/python'),
                                str(deployment / 'scripts/prepare_core_isolation.py'), 'prepare',
                                '--output', str(candidate), '--model-binary', binary], check=True)
                verify_rule(native, rule)
                activate(candidate,verify_rule=False)
            # Select only the private instance; keep every other router setting.
            router = json.loads(regular(old_router, private=True)) if old_router.exists() else {}
            atomic(old_router, dict(router, backend='jarvis'))
            journal['phase'] = 'checking'
            atomic(state, journal)
            subprocess.run(['/usr/bin/systemctl', '--system', '--no-ask-password',
                            'start', model.unit_name()], check=True)
            model.wait_model()
            subprocess.run([sys.executable, str(deployment / 'scripts/qwen-setup.py'), '--enable'], check=True)
            restore_running(desired)
            if '--no-restart' in forwarded or not desired:
                subprocess.run(['/usr/bin/systemctl', '--system', '--no-ask-password',
                                'stop', model.unit_name()], check=True)
            atomic(home / CHOICE, dict(saved, enabled=True, model_binary=binary))
            state.unlink()
            print('Jarvis network isolation is enabled. General Ollama was not modified.')
            return 0
        except BaseException:
            # A second cancellation must not interrupt native-file restoration.
            previous_signal = signal.signal(signal.SIGTERM, signal.SIG_IGN)
            print('Restoring the previous deployment and its isolation policy…', file=sys.stderr)
            persisted = json.loads(regular(state, private=True, limit=200000))
            if persisted.get('backup'):
                journal['backup'] = persisted['backup']
                backup = Path(persisted['backup'])
            journal['phase'] = 'recovering'
            atomic(state, journal)
            try:
                recover_transaction(home, journal, native)
            finally:
                signal.signal(signal.SIGTERM, previous_signal)
            raise
        finally:
            for key, value in previous_environment.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    arguments = args.arguments
    if arguments[:1] == ['--']:
        arguments = arguments[1:]
    if arguments[:1] == ['--record-backup']:
        if len(arguments) != 2:
            parser.error('Expected one managed backup path')
        record_backup(Path(os.environ.get('JARVIS_HOME', Path.home())), Path(arguments[1]))
        return 0
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(InterruptedError('Installation cancelled')))
    try:
        if arguments == ['--recover']:
            return resume_recovery(Path(os.environ.get('JARVIS_HOME', Path.home())))
        return run_install(arguments, Path(os.environ.get('JARVIS_HOME', Path.home())))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print('Jarvis installation stopped: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
