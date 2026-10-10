#!/usr/bin/env python3
"""Installer regressions: early refusal, user baseline and terminal handoff."""
import errno
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import sys
import tempfile
import time
from unittest.mock import Mock, patch

import install_prerequisites as prerequisites
import prepare_voice_baseline as baseline
import isolation_install as install

if os.getuid() == 0:
    raise SystemExit('Run installer regressions without sudo')


def rejects(function, *args):
    try:
        function(*args)
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError):
        return
    raise AssertionError('Unsafe baseline accepted')


for version, permitted in (('0.105', False), ('0.106', True), ('124', True), ('unknown', False)):
    # Modern Polkit uses integer versions, so both documented formats are exercised.
    output = 'pkaction version ' + version + '\n'
    with patch.object(prerequisites.subprocess, 'run', return_value=Mock(stdout=output)), \
         patch.object(Path, 'is_dir', return_value=True), \
         patch.object(Path, 'is_symlink', return_value=False):
        if permitted:
            prerequisites.isolation_support()
        else:
            rejects(prerequisites.isolation_support)

with patch.object(prerequisites.subprocess, 'run', return_value=Mock(stdout='pkaction version 124\n')), \
     patch.object(Path, 'is_dir', return_value=False):
    rejects(prerequisites.isolation_support)

for version in ('3.10.12', '3.11.15', '3.12.3'):
    with patch.object(Path, 'exists', return_value=True), \
         patch.object(prerequisites, 'python_version', return_value=version):
        rejects(prerequisites.reviewed_python, Path.home())

with tempfile.TemporaryDirectory() as directory:
    home = Path(directory)
    account = Mock(pw_dir=str(home))
    with patch.object(Path, 'home', return_value=home), \
         patch.object(install.pwd, 'getpwuid', return_value=account), \
         patch.object(install, 'select', return_value=(True, {'schema_version': 1, 'enabled': True})), \
         patch.object(install, 'check_prerequisites', side_effect=RuntimeError('unsupported host')), \
         patch.object(install, 'native_snapshot') as native, \
         patch.object(install.model, 'prepare_models') as model:
        rejects(install.run_install, ['--isolation'], home)
        assert not native.called and not model.called
        assert not (home / install.JOURNAL).exists()

absent = {'LoadState': 'not-found', 'ActiveState': 'inactive', 'MainPID': '0',
          'ControlPID': '0', 'FragmentPath': '', 'DropInPaths': ''}
for key, value in (('MainPID', '7'), ('ControlPID', '8'), ('FragmentPath', '/fixture'),
                   ('DropInPaths', '/fixture'), ('LoadState', 'loaded'), ('ActiveState', 'active')):
    assert not baseline.absent(dict(absent, **{key: value}))

for problem in (None, 'partial', 'link', 'loaded', 'space', 'reload'):
    with tempfile.TemporaryDirectory() as directory:
        home = Path(directory)
        if problem == 'partial':
            (home / '.config/mycroft').mkdir(parents=True)
            (home / '.config/mycroft/mycroft.conf').write_text('keep me')
        if problem == 'link':
            (home / '.venvs').symlink_to(home / 'elsewhere')
        def state(unit):
            if unit == 'pulseaudio.socket':
                return {'LoadState': 'loaded'}
            return dict(absent, LoadState='loaded') if problem == 'loaded' else dict(absent)

        def run(command, **kwargs):
            if '-m' in command and 'venv' in command:
                assert '--copies' in command
                stage = Path(command[-1])
                (stage / 'bin').mkdir(parents=True)
                (stage / 'bin/python').write_text('fixture interpreter')
            elif command[-1] == 'daemon-reload':
                if problem == 'reload':
                    raise subprocess.CalledProcessError(1, command)
            else:
                raise AssertionError(command)
            return Mock(returncode=0)

        with patch.object(Path, 'home', return_value=home), \
             patch.object(baseline.pwd, 'getpwuid', return_value=Mock(pw_dir=str(home))), \
             patch.object(baseline, 'status', side_effect=state), \
             patch.object(baseline, 'reviewed_python', return_value=Path(sys.executable)), \
             patch.object(baseline.shutil, 'disk_usage', return_value=Mock(free=1 if problem == 'space' else 20_000_000_000)), \
             patch.object(baseline.subprocess, 'run', side_effect=run):
            if problem:
                rejects(baseline.prepare, home)
                assert not (home / '.config/systemd/user/ovos.service').exists()
                if problem == 'partial':
                    assert (home / '.config/mycroft/mycroft.conf').read_text() == 'keep me'
            else:
                baseline.prepare(home)
                assert (home / '.venvs/ovos/bin/python').is_file()
                assert '127.0.0.1' in (home / '.config/mycroft/mycroft.conf').read_text()
                assert 'StandardOutput=null' in (home / '.config/systemd/user/ovos-core.service').read_text()
                assert not (home / '.config/systemd/user/default.target.wants').exists()
                rejects(baseline.prepare, home)

# An actual PTY verifies /dev/tty access in the foreground and restoration to
# the coordinator. No sudo command, password or desktop service is involved.
pid, descriptor = pty.fork()
if pid == 0:
    try:
        group = os.tcgetpgrp(0)
        command = [sys.executable, '-c',
                   'import os; f=open("/dev/tty","r+"); '
                   'assert os.tcgetpgrp(f.fileno()) == os.getpgrp(); '
                   'print("TTY_READY", flush=True); '
                   'assert f.readline().strip() == "fixture"']
        assert install.run_child(command, dict(os.environ)) == 0
        assert os.tcgetpgrp(0) == group
        print('TTY_RESTORED', flush=True)
        os._exit(0)
    except BaseException:
        os._exit(1)
output = b''
deadline = time.monotonic() + 15
try:
    while b'TTY_RESTORED' not in output and time.monotonic() < deadline:
        if select.select([descriptor], [], [], 0.2)[0]:
            try:
                chunk = os.read(descriptor, 4096)
            except OSError as error:
                if error.errno == errno.EIO:
                    break
                raise
            if not chunk:
                break
            previous = output
            output += chunk
            if b'TTY_READY' in output and b'TTY_READY' not in previous:
                os.write(descriptor, b'fixture\n')
    assert b'TTY_RESTORED' in output, 'Controlling terminal handoff failed'
finally:
    os.close(descriptor)
    completed, status = os.waitpid(pid, 0 if b'TTY_RESTORED' in output else os.WNOHANG)
    if not completed:
        os.kill(pid, signal.SIGKILL)
        _, status = os.waitpid(pid, 0)
assert os.waitstatus_to_exitcode(status) == 0

# Cancel the real coordinator while its installer and grandchild are alive.
# An unrelated process outside that group must remain running.
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    marker = root / 'children.json'
    sentinel = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
    coordinator = os.fork()
    if coordinator == 0:
        def cancel(*_):
            raise InterruptedError('fixture cancellation')
        signal.signal(signal.SIGTERM, cancel)
        try:
            install.run_child([sys.executable, '-c',
                'import json, os, subprocess, sys, time; '
                'from pathlib import Path; '
                'p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"]); '
                'Path(sys.argv[1]).write_text(json.dumps([os.getpid(),p.pid])); '
                'time.sleep(30)', str(marker)], dict(os.environ))
            os._exit(1)
        except InterruptedError:
            os._exit(0)
        except BaseException:
            os._exit(1)
    children = []
    completed = 0
    try:
        deadline = time.monotonic() + 10
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        import json
        children = json.loads(marker.read_text())
        os.kill(coordinator, signal.SIGTERM)
        completed = 0
        while time.monotonic() < deadline:
            completed, status = os.waitpid(coordinator, os.WNOHANG)
            if completed:
                break
            time.sleep(0.02)
        assert completed and os.waitstatus_to_exitcode(status) == 0
        for child in children:
            state = Path(f'/proc/{child}/stat')
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                try:
                    alive = state.read_text().split(') ', 1)[1].split()[0] != 'Z'
                except (FileNotFoundError, ProcessLookupError):
                    alive = False
                if not alive:
                    break
                time.sleep(0.02)
            assert not alive, 'Installer descendant survived cancellation'
        assert sentinel.poll() is None, 'Cancellation reached an unrelated process'
    finally:
        sentinel.terminate()
        sentinel.wait(timeout=3)
        if not completed:
            os.kill(coordinator, signal.SIGKILL)
            os.waitpid(coordinator, 0)
        for child in children:
            try:
                os.kill(child, signal.SIGKILL)
            except ProcessLookupError:
                pass
print('PASS: isolation/Python preflight, absent-only quiet baseline, refusal/recovery, terminal handoff and bounded group cancellation')
