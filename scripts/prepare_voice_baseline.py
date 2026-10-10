#!/usr/bin/env python3
"""Prepare only an absent ordinary-user OVOS baseline. Never start services."""
import argparse
import json
import os
from pathlib import Path
import pwd
import shutil
import stat
import subprocess
import tempfile

from install_prerequisites import reviewed_python
from prepare_core_isolation import unit_string

WORKERS = {'ovos-messagebus.service': ('ovos-messagebus', []),
           'ovos-phal.service': ('ovos_PHAL', ['ovos-messagebus.service']),
           'ovos-audio.service': ('ovos-audio', ['ovos-messagebus.service', 'ovos-phal.service']),
           'ovos-core.service': ('ovos-core', ['ovos-messagebus.service', 'ovos-phal.service', 'ovos-audio.service']),
           'ovos-listener.service': ('ovos-dinkum-listener', ['ovos-messagebus.service', 'ovos-core.service', 'ovos-phal.service'])}


def status(unit):
    value = subprocess.run(['/usr/bin/systemctl', '--user', 'show', unit,
                            '--property=LoadState,ActiveState,MainPID,ControlPID,FragmentPath,DropInPaths'],
                           capture_output=True, text=True, timeout=10, check=True)
    return dict(line.split('=', 1) for line in value.stdout.splitlines() if '=' in line)


def absent(value):
    return (value.get('LoadState') == 'not-found' and value.get('ActiveState') == 'inactive'
            and value.get('MainPID') == '0' and value.get('ControlPID') == '0'
            and value.get('FragmentPath') == '' and value.get('DropInPaths') == '')


def paths(home):
    base = home / '.config/systemd/user'
    return [home / '.venvs/ovos', home / '.config/mycroft/mycroft.conf',
            *[base / unit for unit in ('ovos.service', *WORKERS)]]


def check(home):
    if os.getuid() <= 0 or os.getuid() != os.geteuid():
        raise RuntimeError('Prepare OVOS as the desktop user, without sudo')
    if home != Path.home() or pwd.getpwuid(os.getuid()).pw_dir != str(home):
        raise RuntimeError('Use the current desktop account home')
    for path in paths(home):
        if path.exists() or path.is_symlink():
            raise RuntimeError('A partial or existing OVOS baseline needs review; no files changed')
        for parent in path.parents:
            if parent == home.parent:
                break
            if parent.is_symlink():
                raise ValueError('OVOS baseline paths must not follow symbolic links')
            if parent.exists() and (not parent.is_dir() or parent.stat().st_uid != os.getuid()
                                    or parent.stat().st_mode & stat.S_IWOTH):
                raise ValueError('OVOS baseline directory ownership needs review')
    for unit in ('ovos.service', *WORKERS):
        if not absent(status(unit)):
            raise RuntimeError('Existing OVOS user services need review; no files changed')
    if shutil.disk_usage(home).free < 8589934592:
        raise RuntimeError('Keep at least 8 GiB free for OVOS staging and rollback, plus model storage')
    for dependency in ('pulseaudio.socket', 'pipewire-pulse.service'):
        value = status(dependency)
        if value.get('LoadState') == 'loaded':
            return reviewed_python(home), dependency
    raise RuntimeError('A supported desktop audio service is required before OVOS setup')


def units(home, audio):
    python_dir = home / '.venvs/ovos/bin'
    meta = ('[Unit]\nDescription=Open Voice OS - Meta service\nRequires=' + audio +
            '\nWants=' + ' '.join(WORKERS) + '\n[Service]\nType=oneshot\n'
            'ExecStart=/bin/true\nRemainAfterExit=yes\n[Install]\nWantedBy=default.target\n')
    result = {'ovos.service': meta}
    for name, (command, dependencies) in WORKERS.items():
        result[name] = ('[Unit]\nDescription=Open Voice OS user worker\nPartOf=ovos.service\n'
                        'Requires=ovos.service ' + ' '.join(dependencies) + '\nAfter=' +
                        ' '.join(dependencies) + '\n[Service]\nType=simple\n'
                        'WorkingDirectory=' + unit_string(home / '.venvs/ovos') + '\n'
                        'ExecStart=' + unit_string(python_dir / command) + '\n'
                        'Restart=on-failure\nRestartSec=5\nTimeoutStartSec=300\n'
                        'StandardOutput=null\nStandardError=null\n[Install]\nWantedBy=ovos.service\n')
    return result


def create(path, text):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        stream.write(text)


def prepare(home):
    interpreter, audio = check(home)
    created = {}
    venv = home / '.venvs/ovos'
    state = home / '.local/state/jarvis'
    if any(path.is_symlink() for path in (state, *state.parents)):
        raise ValueError('OVOS staging must not follow symbolic links')
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    published = False
    with tempfile.TemporaryDirectory(prefix='voice-baseline-', dir=state) as temporary:
        stage = Path(temporary) / 'ovos'
        subprocess.run([str(interpreter), '-m', 'venv', '--copies', str(stage)], check=True)
        # Recheck all destinations and service identities after venv preparation.
        check(home)
        venv.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            os.rename(stage, venv)
            published = True
            config = home / '.config/mycroft/mycroft.conf'
            text = json.dumps({'websocket': {'host': '127.0.0.1', 'port': 8181,
                                            'route': '/core', 'ssl': False}}, indent=2) + '\n'
            create(config, text)
            created[config] = text
            for name, text in units(home, audio).items():
                path = home / '.config/systemd/user' / name
                create(path, text)
                created[path] = text
            subprocess.run(['/usr/bin/systemctl', '--user', 'daemon-reload'], check=True)
        except BaseException:
            for path, text in created.items():
                if not path.is_symlink() and path.is_file() and path.read_text() == text:
                    path.unlink()
            if published:
                # Retain a failed baseline for review rather than deleting a possibly changed venv.
                print('Prepared OVOS interpreter retained for review; no services were started.')
            raise
    print('Ordinary-user OVOS baseline prepared. Reviewed packages are installed by the staged Jarvis installer.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        (check if args.check else prepare)(Path.home())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, str(error) + '\n')
