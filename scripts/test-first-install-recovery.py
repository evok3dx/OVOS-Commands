#!/usr/bin/env python3
"""Verify first-install recovery without touching host service state."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import Mock, patch

import control_runtime as runtime
import isolation_install as install

if os.getuid() == 0:
    raise SystemExit('Run as a normal user, without sudo.')


def state(load='not-found', **changes):
    value = {'LoadState': load, 'ActiveState': 'inactive', 'SubState': 'dead',
             'MainPID': '0', 'ControlPID': '0', 'FragmentPath': '', 'DropInPaths': ''}
    if load == 'loaded':
        value['FragmentPath'] = '/reviewed/unit.service'
    value.update(changes)
    return value


def rejected(function):
    try:
        function()
    except (RuntimeError, subprocess.SubprocessError):
        return
    raise AssertionError('Unverified recovery state was accepted')


for present in ((), ('ovos-audio.service',), tuple(install.LOGICAL)):
    observed = {name: state('loaded' if name in present else 'not-found')
                for name in install.LOGICAL}
    with patch.object(install, 'properties', side_effect=lambda scope, name, *keys: observed[name]), \
         patch.object(runtime, 'operation_lock', side_effect=contextlib.nullcontext), \
         patch.object(runtime, 'run') as run:
        assert install.stop_workers(Path('/reviewed/home'), False, recovery=True) == []
        expected = [name for name in reversed(runtime.UNITS) if name in present]
        if expected:
            run.assert_called_once_with(['systemctl', '--user', 'stop', *expected], timeout=45)
        else:
            run.assert_not_called()
print('PASS: absent first-install units are skipped; only present fixed voice units are stopped')

for change in ({'MainPID': '1'}, {'ControlPID': '1'}, {'ActiveState': 'active'},
               {'SubState': 'running'}, {'FragmentPath': '/unexpected/unit'},
               {'DropInPaths': '/unexpected/override'}, {'MainPID': None},
               {'LoadState': 'error'}, {'LoadState': None}):
    observed = {name: state() for name in install.LOGICAL}
    observed[runtime.CORE] = state(**change)
    with patch.object(install, 'properties', side_effect=lambda scope, name, *keys: observed[name]), \
         patch.object(runtime, 'operation_lock', side_effect=contextlib.nullcontext), \
         patch.object(runtime, 'run') as run:
        rejected(lambda: install.stop_workers(Path('/reviewed/home'), False, recovery=True))
        run.assert_not_called()
print('PASS: missing, contradictory or process-bearing absence evidence blocks recovery')

# A stop failure must still be fatal. A successful stop with a live process is
# also rejected by the original post-stop checks.
for failed_stop in (True, False):
    observed = {name: state('loaded') for name in install.LOGICAL}
    def inspect(scope, name, *keys):
        value = dict(observed[name])
        if len(keys) == 1 and keys[0] == 'ActiveState,SubState,MainPID,ControlPID':
            value['MainPID'] = '7'
        return value
    with patch.object(install, 'properties', side_effect=inspect), \
         patch.object(runtime, 'operation_lock', side_effect=contextlib.nullcontext), \
         patch.object(runtime, 'run', side_effect=RuntimeError('Stop failed') if failed_stop else None) as run:
        rejected(lambda: install.stop_workers(Path('/reviewed/home'), False, recovery=True))
        assert run.call_count == 1
print('PASS: failed stops and surviving worker processes retain recovery failure')

# Reproduce failure before any first-install source/native files were written.
# Exercise the real recovery cleanup and retain the journal on invalid state.
for invalid in (False, True):
    with tempfile.TemporaryDirectory() as folder:
        home = Path(folder)
        observed = {name: state() for name in install.LOGICAL}
        if invalid:
            observed[runtime.CORE]['MainPID'] = '7'
        journal = {'schema_version': 1, 'uid': os.getuid(), 'binary': '/usr/bin/ollama',
                   'original_binary': None, 'was_active': False, 'native_started': False,
                   'previous_desired': [], 'token': 'x' * 40, 'original_router': None,
                   'original_choice': None, 'original_tree': None}
        record = home / install.JOURNAL
        install.atomic(record, journal)
        with patch.object(install, 'properties', side_effect=lambda scope, name, *keys: observed[name]), \
             patch.object(install, 'active', return_value=False), \
             patch.object(install, 'restore_running') as restore, \
             patch.object(runtime, 'operation_lock', side_effect=contextlib.nullcontext), \
             patch.object(runtime, 'run') as run, \
             contextlib.redirect_stderr(io.StringIO()):
            if invalid:
                rejected(lambda: install.recover_transaction(home, journal, Mock()))
                assert record.exists() and journal['phase'] == 'blocked'
                restore.assert_not_called()
            else:
                install.recover_transaction(home, journal, Mock())
                assert not record.exists()
                restore.assert_called_once_with([])
            run.assert_not_called()
print('PASS: fresh-install recovery completes only with verified absent workers; invalid state retains the journal')
