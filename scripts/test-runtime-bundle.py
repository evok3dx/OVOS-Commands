#!/usr/bin/env python3
"""Real ZIP fixtures test bundle identity, bounds and zero-fallback rejection."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch
import zipfile
import runtime_bundle as bundle


def rejected(function,*args):
    try:function(*args)
    except (OSError,ValueError,RuntimeError,zipfile.BadZipFile):return
    raise AssertionError('Unsafe runtime archive accepted')


with tempfile.TemporaryDirectory(prefix='jarvis-runtime-bundle-') as directory:
    root=Path(directory);voice=root/'voice';voice.mkdir()
    (voice/'reviewed-stack.json').write_text(json.dumps({'packages':{},'verified_runtime_exceptions':[]}))
    wheels=root/'input';wheels.mkdir();wheel=wheels/'fixture_runtime-1.0-py3-none-any.whl'
    with zipfile.ZipFile(wheel,'w') as archive:
        archive.writestr('fixture_runtime-1.0.dist-info/METADATA','Metadata-Version: 2.1\nName: fixture-runtime\nVersion: 1.0\n')
    inventory=root/'inventory.json';inventory.write_text(json.dumps({'packages':{'fixture-runtime':'1.0'}}))
    dep=bundle.dependencies();dep.ROOT=root
    records=dep.wheel_records(wheels)
    lock=root/'runtime.txt';lock.write_text(dep.lock_text(records,[]))
    artifacts=root/'artifacts.json';artifacts.write_text(json.dumps({'packages':records}))
    with patch.object(bundle,'dependencies',return_value=dep):
        archive=root/'runtime.zip';policy_path=root/'policy.json'
        policy=bundle.build(wheels,inventory,lock,artifacts,archive,policy_path)
        copy=root/'copy.zip'
        second=bundle.build(wheels,inventory,lock,artifacts,copy,root/'copy-policy.json')
        assert policy['archive_sha256']==second['archive_sha256']
        output=root/'verified-wheels';bundle.stage(archive,policy,inventory,lock,artifacts,output)
        assert (output/wheel.name).read_bytes()==wheel.read_bytes()
        assert output.stat().st_mode & 0o777==0o700
        rejected(bundle.stage,archive,policy,inventory,lock,artifacts,output)
        tampered=root/'tampered.zip';tampered.write_bytes(archive.read_bytes()+b'changed')
        rejected(bundle.stage,tampered,policy,inventory,lock,artifacts,root/'bad')
        assert not(root/'bad').exists()
        tampered.write_bytes(archive.read_bytes()[:-1])
        rejected(bundle.stage,tampered,policy,inventory,lock,artifacts,root/'short')
        # Even a deliberately updated outer identity cannot bypass the internal
        # file allowlist or type checks.
        shutil.copyfile(archive,tampered)
        with zipfile.ZipFile(tampered,'a') as bad:bad.writestr('../outside','fixture')
        changed={**policy,'archive_bytes':tampered.stat().st_size,'archive_sha256':bundle.digest(tampered)}
        rejected(bundle.stage,tampered,changed,inventory,lock,artifacts,root/'traversal')
        assert not(root/'outside').exists() and not(root/'traversal').exists()
        wheel.write_bytes(wheel.read_bytes()+b'changed')
        rejected(bundle.build,wheels,inventory,lock,artifacts,root/'changed.zip',root/'changed.json')
        assert not(root/'changed.zip').exists()
print('PASS: deterministic verified bundle, private staging, tamper/truncation/traversal/bounds and changed-input rejection')
