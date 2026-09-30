#!/usr/bin/env python3
"""Packaging must reject captures even when untracked or renamed with a suffix."""
import json
from pathlib import Path
from release_privacy import check_path

ROOT = Path(__file__).resolve().parents[1]
for name in ('voice/runtime-observed-linux-x86_64-py311.json',
             'voice/runtime-observed-private.json.bak',
             'voice/runtime-observed-backup/report.json',
             'mycroft.conf', 'logs/private.log', '../capture.json'):
    try:
        check_path(name)
    except ValueError:
        pass
    else:
        raise AssertionError('Private capture accepted')
for name in ('voice/runtime-linux-x86_64-py311.json',
             'voice/runtime-wheels-linux-x86_64-py311.txt',
             'extras/ovos-ww-plugin-openwakeword-onnx/LICENSE'):
    check_path(name)
manifest = json.loads((ROOT / 'deployment-manifest.json').read_text())
for files in manifest['optional_components'].values():
    for name in files:
        check_path(name)
policy = json.loads((ROOT / 'voice/runtime-linux-x86_64-py311.json').read_text())
assert set(policy) == {'schema_version', 'status', 'python', 'python_full_version',
                       'platform', 'packages'}
assert len(policy['packages']) == 296
assert 'qwen_observed' not in json.loads((ROOT / 'voice/model-identities.json').read_text())
assert not list((ROOT / 'voice').glob('runtime-observed-*'))
print('PASS: private capture packaging rejection; public policy fields only')
