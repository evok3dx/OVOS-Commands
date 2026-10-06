#!/usr/bin/env python3
"""Verify privacy readiness against the exact retained upstream runtime wheels."""
import configparser
import hashlib
import importlib.util
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
import types
from unittest.mock import patch
import zipfile
import privacy_logging as privacy
from privacy_worker import LAUNCHERS

if os.getuid() == 0:
    raise RuntimeError('Review runtime as the ordinary user')
root = Path(__file__).resolve().parents[1]
records = json.loads((root/'voice/runtime-wheels-linux-x86_64-py311.artifacts.json').read_text())['packages']
wheels = Path(sys.argv[1])

def verified(name):
    record = records[name]
    wheel = wheels / record['file']
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() == record['sha256']
    return wheel

for role, package in {'core':'ovos-core','listener':'ovos-dinkum-listener',
                      'audio':'ovos-audio','bus':'ovos-messagebus'}.items():
    with zipfile.ZipFile(verified(package)) as archive:
        entries = [name for name in archive.namelist() if name.endswith('.dist-info/entry_points.txt')]
        assert len(entries) == 1
        config = configparser.ConfigParser();config.read_string(archive.read(entries[0]).decode())
        assert LAUNCHERS[role] in config['console_scripts'], (role, config.sections())

with tempfile.TemporaryDirectory() as folder:
    home = Path(folder)
    with zipfile.ZipFile(verified('ovos-utils')) as archive:
        source = archive.read('ovos_utils/process_utils.py')
    path = home/'upstream.py';path.write_bytes(source)
    dependencies = {'ovos_utils':types.ModuleType('ovos_utils'),
                    'ovos_utils.file_utils':types.SimpleNamespace(get_temp_path=lambda *a:str(home)),
                    'ovos_utils.log':types.SimpleNamespace(LOG=logging.getLogger('upstream'))}
    spec = importlib.util.spec_from_file_location('ovos_utils.process_utils',path)
    upstream = importlib.util.module_from_spec(spec)
    dependencies['ovos_utils.process_utils'] = upstream
    with patch.dict(sys.modules,dependencies),patch.dict(os.environ,INVOCATION_ID='runtime-fixture'):
        spec.loader.exec_module(upstream)
        privacy.install_process_status()
        for role, name in (('listener','voice'),('audio','audio'),('core','skills')):
            capture = privacy.Capture(role,home)
            calls = []
            callbacks = upstream.StatusCallbackMap(on_ready=lambda:calls.append('ready'),
                         on_error=lambda error:calls.append('error'),on_stopping=lambda:calls.append('stop'))
            status = upstream.ProcessStatus(name,callback_map=callbacks)
            with patch.object(privacy,'_capture',capture):
                status.set_ready()
                assert status.check_ready() and calls == ['ready']
                assert privacy.readiness(role,'runtime-fixture',home) is (role != 'core')
                if role == 'core':privacy.mark_ready(role)
                assert privacy.readiness(role,'runtime-fixture',home) is True
                status.set_error('PRIVATE-CONTENT-SENTINEL')
                assert not status.check_ready() and calls == ['ready','error']
                assert privacy.readiness(role,'runtime-fixture',home) is False
                status.set_stopping();assert calls[-1] == 'stop'
        assert all(b'PRIVATE-CONTENT-SENTINEL' not in p.read_bytes()
                   for p in privacy.directory(home).glob('*'))
print('PASS: exact hash-locked console names and actual upstream readiness callbacks/state without raw logs')
