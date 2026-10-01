#!/usr/bin/env python3
"""Offline tests of selection, private model integrity and transaction boundaries."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

import isolation_install as install
import private_ollama as model
import model_endpoint as endpoint
import prepare_core_isolation as prepare
import isolation_services as services


def rejects(function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except (ValueError, RuntimeError, OSError):
        return
    raise AssertionError('Unsafe input accepted')


with tempfile.TemporaryDirectory() as folder:
    home = Path(folder)
    with patch.object(install, 'active', return_value=False), contextlib.redirect_stdout(io.StringIO()):
        assert install.select(home, True)[0] is False
        assert install.select(home, False, True)[0] is True
        with patch.object(install.sys.stdin, 'isatty', return_value=True), \
             patch.object(install.sys.stdout, 'isatty', return_value=True), patch('builtins.input', return_value=''):
            assert install.select(home, False)[0] is True
        install.atomic(home / install.CHOICE, {'schema_version': 1, 'enabled': False, 'future': 7})
        assert install.select(home, True)[1]['future'] == 7
        rejects(install.select, home, True, True)
    with patch.object(install, 'active', return_value=True):
        rejects(install.select, home, True)
    (home / install.CHOICE).unlink()
    with patch.object(install, 'active', return_value=True), patch('builtins.input', side_effect=AssertionError('Upgrade must not prompt')):
        assert install.select(home, True)[0] is True
    router = home / '.config/jarvis/router.json'
    assert endpoint.model_port(home) == 11434
    install.atomic(router, {'backend': 'jarvis'})
    assert endpoint.model_port(home) == 11435
    install.atomic(router, {'backend': 'remote'})
    rejects(endpoint.model_port, home)
    router.unlink()
    router.symlink_to(home / 'missing')
    rejects(endpoint.model_port, home)
    router.unlink()

    # Only the exact reviewed model is copied, all content hashes are checked,
    # source data is unchanged, and a corrupt layer never commits a new store.
    source = home / 'general-models'
    blob = b'local model fixture'
    digest = hashlib.sha256(blob).hexdigest()
    blob_name = Path('blobs') / ('sha256-' + digest)
    (source / blob_name).parent.mkdir(parents=True)
    (source / blob_name).write_bytes(blob)
    manifest = {'config': {'digest': 'sha256:' + digest, 'size': len(blob)}, 'layers': []}
    manifest_path = source / model.MANIFEST
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(manifest))
    identity = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    with patch.object(model, 'inventory_digest', return_value=identity), \
         patch.object(model, 'source_stores', return_value=[source]):
        model.prepare_models(home, lambda _: None)
        copied = model.private_root(home) / 'models'
        assert (copied / blob_name).read_bytes() == blob
        assert (source / blob_name).read_bytes() == blob
        assert (copied / blob_name).stat().st_ino != (source / blob_name).stat().st_ino
        with patch.object(model, 'inventory_digest', side_effect=AssertionError('No general endpoint on upgrade')):
            model.prepare_models(home, lambda _: None)
        (copied / blob_name).write_bytes(b'corrupt')
        rejects(model.prepare_models, home, lambda _: None)
    units, rule, _ = prepare.render(os.getuid(), os.getgid(), 'fixture', home,
                                    home / 'deployment', '/usr/bin/ollama')
    assert len(units) == 6
    private = units[model.unit_name()]
    assert 'OLLAMA_HOST=127.0.0.1:11435' in private and 'OLLAMA_NO_CLOUD=1' in private
    assert 'IPAddressDeny=any' in private and 'IPAddressAllow=127.0.0.1 ::1' in private
    assert 'NoNewPrivileges=yes' in private and f'User={os.getuid()}' in private
    assert '11434' not in private and '"ollama.service"' not in rule
    assert model.unit_name() in rule and 'set-property' not in rule

    # Missing, stale, cross-operation and forged transaction tickets fail.
    state = home / install.JOURNAL
    payload = {'schema_version': 1, 'uid': os.getuid(), 'pid': os.getpid(),
               'process_start': install.process_start(os.getpid()), 'token': 'x' * 40,
               'phase': 'updating', 'was_active': False, 'binary': '/usr/bin/ollama',
               'original_binary': None}
    install.atomic(state, payload)
    assert install.installation_blocked(home)
    environment = {'JARVIS_ISOLATION_TRANSACTION': str(state), 'JARVIS_ISOLATION_TOKEN': 'x' * 40}
    with patch.dict(os.environ, environment), patch.object(Path, 'home', return_value=home), \
         patch.object(install, 'regular', side_effect=lambda path, **kw: state.read_text() if path == state else 'foreign'), \
         patch.object(Path, 'exists', return_value=False), patch.object(Path, 'is_symlink', return_value=False):
        install.authorised_transaction('install', home)
        rejects(install.authorised_transaction, 'uninstall', home)
        with patch.dict(os.environ, {'JARVIS_ISOLATION_TOKEN': 'wrong'}):
            rejects(install.authorised_transaction, 'install', home)
        with patch.object(install, 'ancestor', return_value=False):
            rejects(install.authorised_transaction, 'install', home)
    for phase, blocked in [('checking', False), ('recovering-ready', False), ('blocked', True)]:
        install.atomic(state, dict(payload, phase=phase))
        assert install.installation_blocked(home) is blocked
    state.unlink()
    assert not install.installation_blocked(home)

    # Bound privilege to native data operations, never Python, a shell or pip.
    native = install.Native()
    rejects(native.run, 'python3', 'installer.py')
    rejects(native.run, 'bash', 'review.sh')
    rejects(native.run, 'pip', 'install')

print('PASS: default recommendation, upgrade preservation, no endpoint fallback, private model hash/copy and process-bound transaction guards')
