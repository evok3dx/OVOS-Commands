#!/usr/bin/env python3
"""Leak, expiry, readiness and user-service isolation-precedence regressions."""
import importlib.util
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import types
from unittest.mock import patch

if os.getuid() == 0:
    raise RuntimeError('Run privacy regressions as the ordinary user')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import privacy_logging as privacy
import privacy_units as units
import control_runtime as control


def rejected(call):
    try:
        call()
    except (ValueError, RuntimeError, OSError):
        return
    raise AssertionError('Unsafe privacy data was accepted')


with tempfile.TemporaryDirectory() as temporary:
    home = Path(temporary)
    clock = [10.0]
    with patch.object(privacy.time, 'monotonic', side_effect=lambda: clock[0]):
        assert privacy.mode(home)['enabled'] is False
        privacy.set_mode(True, home)
        start = privacy.mode(home)['start']
        assert privacy.mode(home)['remaining'] == 300
        capture = privacy.Capture('core', home)
        record = logging.LogRecord('private-user-data', logging.ERROR, '/private/path', 123,
                                   'Write this: %s', ('PRIVATE-CONTENT-SENTINEL',),
                                   (RuntimeError, RuntimeError('PRIVATE-CONTENT-SENTINEL'), None))
        capture.handle(record)
        value = capture.snapshot()
        assert value['rows'] == [{'component': 'core', 'level': 'ERROR', 'event': 'error', 'source': 'runtime', 'line': 123}]
        assert 'PRIVATE' not in json.dumps(value)
        assert privacy.display(value) == ['core: error · error · runtime:123']
        for _ in range(1000): capture.handle(record)
        assert len(capture.snapshot()['rows']) == privacy.LIMIT
        clock[0] = 100
        privacy.set_mode(True, home)
        assert privacy.mode(home)['start'] == start
        clock[0] = 309.9
        assert privacy.mode(home)['enabled']
        clock[0] = 310
        assert not privacy.mode(home)['enabled']
        assert capture.snapshot()['rows'] == []
        privacy.set_mode(True, home)
        capture.handle(record)
        assert capture.snapshot()['rows']
        privacy.set_mode(False, home)
        assert capture.snapshot()['rows'] == []
        privacy.set_mode(True, home)
        with patch.object(privacy, 'boot', return_value='another-boot'):
            assert not privacy.mode(home)['enabled']
        path = privacy.directory(home) / 'capture.json'
        path.write_text('not valid json')
        assert not privacy.mode(home)['enabled']
        path.write_text(json.dumps({'schema_version': 1, 'boot': privacy.boot(), 'start': 0, 'end': 999999999}))
        assert not privacy.mode(home)['enabled']
        path.unlink();path.symlink_to(home / 'outside')
        assert not privacy.mode(home)['enabled']
        rejected(lambda: privacy.set_mode(True, home))
        path.unlink()
        assert (privacy.directory(home) / 'core-ready.json').stat().st_mode & 0o777 == 0o600

    bad = {'schema_version': 1, 'component': 'core', 'rows': [
        {'component': 'core', 'level': 'ERROR', 'event': 'error', 'source': 'runtime', 'line': 2, 'message': 'private text'}]}
    rejected(lambda: privacy.display(bad))
    bad['rows'][0].pop('message');bad['rows'][0]['event'] = 'private text'
    rejected(lambda: privacy.display(bad))
    rejected(lambda: privacy.display({'schema_version': 1, 'component': 'private text', 'rows': []}))

    # Real child: no speech, exception, direct print, native child output or
    # FileHandler content reaches stdout/stderr/files, in either mode.
    code = '''
import json, logging, os, subprocess, sys, types
sys.path.insert(0, sys.argv[1])
class Status:
    def __init__(self): self.name='voice'
    def set_ready(self): self.original_called=True
    def set_stopping(self): pass
    def set_error(self, error=''): pass
sys.modules['ovos_utils']=types.ModuleType('ovos_utils')
sys.modules['ovos_utils.process_utils']=types.SimpleNamespace(ProcessStatus=Status)
import privacy_logging as privacy
capture=privacy.bootstrap('listener')
logger=logging.getLogger('test');logger.setLevel(logging.DEBUG)
logger.addHandler(logging.FileHandler(os.path.join(os.environ['HOME'],'application.log')))
print('PRIVATE-CONTENT-SENTINEL')
os.write(2,b'PRIVATE-CONTENT-SENTINEL')
subprocess.run([sys.executable,'-c','print("PRIVATE-CONTENT-SENTINEL")'],check=True)
logger.info('Raw transcription: %s','PRIVATE-CONTENT-SENTINEL')
try: raise RuntimeError('PRIVATE-CONTENT-SENTINEL')
except RuntimeError: logger.exception('PRIVATE-CONTENT-SENTINEL')
status=Status();status.set_ready();assert status.original_called
assert privacy.readiness('listener','test-invocation') is True
assert privacy.readiness('listener','other-invocation') is None
assert 'PRIVATE' not in json.dumps(capture.snapshot())
status.set_error('PRIVATE-CONTENT-SENTINEL')
assert privacy.readiness('listener','test-invocation') is False
'''
    for enabled in (False, True):
        privacy.set_mode(enabled, home)
        result = subprocess.run([sys.executable, '-c', code, str(ROOT / 'scripts')],
                                env=dict(os.environ, HOME=str(home), INVOCATION_ID='test-invocation'),
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
        assert result.stdout == result.stderr == ''
        assert not (home / 'application.log').exists()
        assert all(b'PRIVATE-CONTENT-SENTINEL' not in path.read_bytes()
                   for path in home.rglob('*') if path.is_file())

    # The new worker state avoids journal dependency; legacy current-invocation
    # markers remain available solely for migration/recovery.
    with patch.object(privacy, 'readiness', return_value=True), \
         patch.object(control, 'run', side_effect=AssertionError('Readiness read raw journal')):
        assert control.worker_ready(control.CORE, 'invocation')
    with patch.object(privacy, 'readiness', return_value=False), \
         patch.object(control, 'run', side_effect=AssertionError('Readiness read raw journal')):
        assert not control.worker_ready(control.LISTENER, 'invocation')
    with patch.object(privacy, 'mode', return_value={'enabled': False}), \
         patch.object(control, 'run', side_effect=AssertionError('No logs mode queried journal')):
        assert control.maintenance('logs').startswith('No logs.')

    # The expiry sweeper clears rows without a snapshot query or a GUI.
    privacy.set_mode(True, home)
    running = privacy.Capture('audio', home)
    running.handle(record)
    assert running.rows
    cleared = threading.Event()
    prune = running.prune
    def watched():
        result = prune()
        if not running.rows: cleared.set()
        return result
    running.prune = watched
    thread = threading.Thread(target=running.sweep)
    thread.start()
    try:
        privacy.set_mode(False, home)
        assert cleared.wait(3), 'The worker depended on a GUI query to clear capture'
        assert not running.rows
    finally:
        running.stopped.set();thread.join(2)
    assert not thread.is_alive()

    # User-space drop-ins sort before native isolation's 90-* relay, and
    # installation refuses an unknown file rather than replacing it.
    units.install(home)
    assert units.NAME < '90-jarvis-isolation.conf'
    for unit, role in units.UNITS.items():
        path = home / '.config/systemd/user' / (unit + '.d') / units.NAME
        assert path.read_text() == units.render(home, role)
        assert path.stat().st_mode & 0o777 == 0o600
    changed = home / '.config/systemd/user/ovos-core.service.d' / units.NAME
    changed.write_text('unreviewed override')
    rejected(lambda: units.install(home))
    assert changed.read_text() == 'unreviewed override'

print('PASS: content exclusion, actual quiet child/file output, five-minute expiry, reboot/off/corrupt fail-closed, readiness without logs and isolated relay precedence')
