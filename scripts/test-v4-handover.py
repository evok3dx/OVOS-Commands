#!/usr/bin/env python3
"""Exercise offline-install rejection and bounded laptop evidence with hostile inputs."""
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec=importlib.util.spec_from_file_location(name.replace('-','_'),ROOT/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


probe=load('probe-offline-runtime')
check=load('v4-laptop-check')
isolation=load('core-isolation-preflight')
with tempfile.TemporaryDirectory() as temporary:
    root=Path(temporary)
    (root/'voice').mkdir();(root/'scripts').mkdir()
    (root/'voice/reviewed-stack.json').write_text(json.dumps({'packages':{},'verified_runtime_exceptions':[]}))
    # A real local fixture wheel supplies import/installed-metadata evidence.
    wheels=root/'wheels';wheels.mkdir()
    wheel=wheels/'jarvis_probe_fixture-1.0-py3-none-any.whl'
    with zipfile.ZipFile(wheel,'w') as archive:
        entries={
            'jarvis_probe_fixture.py':'VALUE = "offline fixture"\n',
            'jarvis_probe_fixture-1.0.dist-info/METADATA':'Metadata-Version: 2.1\nName: jarvis-probe-fixture\nVersion: 1.0\n',
            'jarvis_probe_fixture-1.0.dist-info/WHEEL':'Wheel-Version: 1.0\nGenerator: Jarvis regression fixture\nRoot-Is-Purelib: true\nTag: py3-none-any\n',
        }
        entries['jarvis_probe_fixture-1.0.dist-info/RECORD']=''.join(name+',,\n' for name in entries)+'jarvis_probe_fixture-1.0.dist-info/RECORD,,\n'
        for name,text in entries.items():archive.writestr(name,text)
    inventory={'python':'3.11','python_full_version':platform.python_version() if sys.version_info[:2]==(3,11) else '3.11.16',
               'platform':'linux-x86_64','packages':{'jarvis-probe-fixture':'1.0'}}
    capture=root/'inventory.json';capture.write_text(json.dumps(inventory))
    lock=root/'runtime.txt'
    with patch.object(probe.dependencies,'ROOT',root):
        records=probe.dependencies.wheel_records(wheels)
        lock.write_text(probe.dependencies.lock_text(records,[]))
        stage=root/'stage';stage.mkdir()
        copied,_,_,_=probe.prepare(wheels,inventory,lock,stage)
        original=wheel.read_bytes()
        wheel.write_bytes(original+b'tamper')
        assert (copied/wheel.name).read_bytes()==original, 'Shared input changed staged bytes'
        tampered=root/'tampered';tampered.mkdir()
        try:probe.prepare(wheels,inventory,lock,tampered)
        except RuntimeError as error:assert 'Lock differs' in str(error)
        else:raise AssertionError('Tampered wheel accepted')
        wheel.write_bytes(original)
        lock.write_text(lock.read_text()+'--index-url https://invalid.example\n')
        injected=root/'injected';injected.mkdir()
        try:probe.prepare(wheels,inventory,lock,injected)
        except RuntimeError:pass
        else:raise AssertionError('Injected lock accepted')
        lock.write_text(probe.dependencies.lock_text(records,[]))
        if sys.version_info[:2]==(3,11):
            validator=root/'scripts/validate-staged-ovos.py'
            validator.write_text('import jarvis_probe_fixture as f\nassert f.VALUE == "offline fixture"\n')
            output=root/'result.json'
            with patch.object(probe,'ROOT',root),patch.dict('os.environ',{'PIP_INDEX_URL':'https://invalid.example','PYTHONPATH':'/invalid'},clear=False):
                probe.run_probe(wheels,capture,lock,output)
            result=json.loads(output.read_text())
            assert result['installed_packages']==inventory['packages']
            assert result['live_environment_modified'] is False
            assert output.stat().st_mode & 0o777 == 0o600
            stage=root/'.local/state/jarvis/stage.fixture/ovos-venv'
            probe.venv.EnvBuilder(with_pip=True).create(stage)
            stage_output=root/'staged-result.json'
            with patch.object(probe,'ROOT',root):
                probe.run_probe(wheels,capture,lock,stage_output,staged_target=stage,home=root)
            assert json.loads(stage_output.read_text())['staged_target_modified'] is True
            assert (stage/'lib').is_dir()
            live=root/'.venvs/ovos';live.mkdir(parents=True)
            with patch.object(probe,'ROOT',root):
                try:probe.run_probe(wheels,capture,lock,root/'must-not-exist.json',staged_target=live,home=root)
                except RuntimeError:pass
                else:raise AssertionError('Live target accepted for staged install')
            assert not (root/'must-not-exist.json').exists()
        else:print('Python 3.11 install fixture pending on this interpreter; rejection checks passed')
    config=root/'.config/mycroft';config.mkdir(parents=True)
    (config/'mycroft.conf').write_text(json.dumps({'api_key':'SECRET-SENTINEL','websocket':{'host':'private-host-SENTINEL'},'stt':{'module':'PRIVATE-SENTINEL'}}))
    text=json.dumps(check.settings(root))
    assert 'SENTINEL' not in text and not check.settings(root)['bus_host_explicitly_loopback']
    response=subprocess.CompletedProcess([],0,'LoadState=loaded\nActiveState=active\nIPAddressDeny=0.0.0.0/0 ::/0\nIPAddressAllow=127.0.0.0/8 ::1/128\nIPAccounting=yes\n')
    with patch.object(isolation.subprocess,'run',return_value=response):
        report=isolation.collect()
        assert any(item['scope']=='system' and item['service']=='ollama.service' for item in report['services'])
        assert all(item['deny_all_families_configured'] for item in report['services'])
        assert '127.0.0.0' not in json.dumps(report) and report['status'].startswith('NOT VERIFIED')
    redirect=check.NoRedirect()
    try:redirect.redirect_request(None,None,302,'',{},'https://invalid.example')
    except ValueError:pass
    else:raise AssertionError('Loopback request redirected outside the host')

print('PASS: tampered/injected lock rejection, private evidence and system/user inventory')
