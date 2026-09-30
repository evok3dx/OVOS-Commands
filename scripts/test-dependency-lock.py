#!/usr/bin/env python3
"""Reject missing, conflicting, altered or ambiguous wheel candidates."""
import importlib.util
import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('lock',ROOT/'scripts/dependency-lock.py')
lock=importlib.util.module_from_spec(spec);spec.loader.exec_module(lock)

for name,version in [('example','1.0\n--index-url=https://invalid.example'),
                     ('example @ https://invalid.example','1.0'),('example','>=1.0')]:
    try:lock.validate_pin(name,version)
    except RuntimeError:pass
    else:raise AssertionError('Injected requirement accepted')

def wheel(directory,name,requires=()):
    path=directory/(name+'-1.0-py3-none-any.whl')
    metadata='Metadata-Version: 2.1\nName: '+name+'\nVersion: 1.0\n'
    metadata+=''.join('Requires-Dist: '+item+'\n' for item in requires)
    with zipfile.ZipFile(path,'w') as archive:
        archive.writestr(name+'-1.0.dist-info/METADATA',metadata)
    return path

with tempfile.TemporaryDirectory() as directory:
    root=Path(directory);voice=root/'voice';voice.mkdir()
    (voice/'reviewed-stack.json').write_text(json.dumps({'packages':{},'verified_runtime_exceptions':[]}))
    wheels=root/'wheels';wheels.mkdir()
    wheel(wheels,'parent',('child[socks]>=1.0',))
    child=wheel(wheels,'child',('optional>=1.0; extra == "socks"',))
    inventory={'packages':{'parent':'1.0','child':'1.0'}}
    with patch.object(lock,'ROOT',root):
        try:lock.verify_closure(lock.wheel_records(wheels),inventory)
        except RuntimeError as error:assert 'Missing transitive' in str(error)
        else:raise AssertionError('Missing extra dependency accepted')
        optional=wheel(wheels,'optional');inventory['packages']['optional']='1.0'
        records=lock.wheel_records(wheels)
        assert lock.verify_closure(records,inventory)==[]
        with zipfile.ZipFile(optional,'a') as archive:
            archive.writestr('optional/_vendor/library-2.0.dist-info/METADATA','Name: library\nVersion: 2.0\n')
        assert lock.wheel_records(wheels)['optional']['version']=='1.0'
        # Python patch markers must use the captured interpreter, not 3.11.0.
        records['parent']['requires']=['patch-only>=1.0; python_full_version >= "3.11.8"']
        inventory['python_full_version']='3.11.16'
        try:lock.verify_closure(records,inventory)
        except RuntimeError as error:assert 'Missing transitive' in str(error)
        else:raise AssertionError('Captured patch-level dependency omitted')
        inventory.pop('python_full_version')
        records=lock.wheel_records(wheels)
        child.write_bytes(child.read_bytes()+b'changed')
        assert lock.wheel_records(wheels)['child']['sha256']!=records['child']['sha256']
        inventory['packages']['child']='2.0'
        try:lock.verify_closure(lock.wheel_records(wheels),inventory)
        except RuntimeError as error:assert 'inventory differs' in str(error)
        else:raise AssertionError('Changed version accepted')
    (wheels/'alias.whl').symlink_to(optional)
    try:lock.wheel_records(wheels)
    except RuntimeError:pass
    else:raise AssertionError('Symlink wheel accepted')
    capture=root/'capture.json'
    capture.write_text(json.dumps({'packages':{},'non_index_sources':{'private-package':{'editable':True}}}))
    try:lock.inputs(root/'bad-inputs.txt',capture)
    except RuntimeError as error:assert 'Non-index source requires review' in str(error)
    else:raise AssertionError('Unknown editable source converted into an index pin')
    pins={'numpy':'2.4.6','ovos-ww-plugin-openwakeword':'0.4.5a2'}
    (voice/'reviewed-stack.json').write_text(json.dumps({'packages':pins,'verified_runtime_exceptions':[{'packages':list(pins)}]}))
    records={name:{'version':version,'file':name.replace('-','_')+'-'+version+'-py3-none-any.whl','requires':[]}
             for name,version in pins.items()}
    records['ovos-ww-plugin-openwakeword']['requires']=['numpy<2']
    with patch.object(lock,'ROOT',root):
        try:lock.verify_closure(records,{'packages':pins})
        except RuntimeError as error:assert 'Dependency version conflict' in str(error)
        else:raise AssertionError('NumPy conflict silently exempted')
        records['ovos-ww-plugin-openwakeword']['requires']=['numpy<1']
        try:lock.verify_closure(records,{'packages':pins})
        except RuntimeError as error:assert 'Dependency version conflict' in str(error)
        else:raise AssertionError('Unreviewed NumPy requirement silently exempted')

print('PASS: dependency closure includes extras and rejects missing/changed/ambiguous artifacts')
