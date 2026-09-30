#!/usr/bin/env python3
"""Provenance reuse cannot silently replace a verified full-runtime stage."""
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import runtime_provenance as provenance
import prepare_core_isolation as files

with tempfile.TemporaryDirectory(prefix='jarvis-runtime-receipt-') as directory:
    root=Path(directory);venv=root/'venv';venv.mkdir()
    inventory=root/'inventory.json';lock=root/'runtime.txt'
    packages={'fixture-runtime':'1.2.3'}
    inventory.write_text(json.dumps({'packages':packages}))
    lock.write_text('fixture-runtime==1.2.3 --hash=sha256:'+'a'*64+'\n')
    assert not provenance.matches(venv,inventory,lock,packages)
    receipt=venv/provenance.NAME
    document=provenance.document(inventory,lock,packages)
    files.private_file(receipt,json.dumps(document))
    assert provenance.matches(venv,inventory,lock,{**packages,'ovos-skill-jarvis-dispatcher':'4.0.0rc1'})
    assert not provenance.matches(venv,inventory,lock,{**packages,'unreviewed-package':'1'})
    assert not provenance.matches(venv,inventory,lock,{'fixture-runtime':'9.9.9'})
    receipt.chmod(0o644);assert not provenance.matches(venv,inventory,lock,packages);receipt.chmod(0o600)
    previous=lock.read_text();lock.write_text(previous+'# changed\n')
    assert not provenance.matches(venv,inventory,lock,packages);lock.write_text(previous)
    receipt.unlink();receipt.symlink_to(inventory)
    assert not provenance.matches(venv,inventory,lock,packages)
    receipt.unlink();receipt.write_text('not json');receipt.chmod(0o600)
    assert not provenance.matches(venv,inventory,lock,packages)
    try:provenance.document(inventory,lock,{})
    except ValueError:pass
    else:raise AssertionError('Incomplete runtime receipt accepted')

import runtime_bundle as bundle
with tempfile.TemporaryDirectory(prefix='jarvis-missing-runtime-') as directory:
    root=Path(directory);output=root/'stage/wheels';source=Path(__file__).resolve().parents[1]
    policy=json.loads((source/'voice/runtime-bundle.json').read_text())
    if policy['status'].startswith('REBUILD REQUIRED'):
        with patch.object(bundle.importlib.util,'spec_from_file_location') as download:
            try:bundle.obtain(None,policy,source/'voice/runtime-linux-x86_64-py311.json',
                              source/'voice/runtime-wheels-linux-x86_64-py311.txt',
                              source/'voice/runtime-wheels-linux-x86_64-py311.artifacts.json',output)
            except ValueError:pass
            else:raise AssertionError('Missing bundle silently replaced by a download/resolver')
            assert not download.called and not output.parent.exists()
print('PASS: receipt parity/privacy/lock guards and missing verified input fails before staging')
