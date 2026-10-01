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
import shutil
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

    install.atomic(home / install.CHOICE, {'schema_version': 1, 'enabled': True, 'model_binary': '/usr/bin/ollama'})
    rejects(endpoint.model_port, home)
    install.atomic(router, {'backend': 'general'})
    rejects(endpoint.model_port, home)
    (home / install.CHOICE).unlink()
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

# Exercise the complete coordinator around an installation that changes source.
# Native system operations are replaced at the boundary; all private files,
# transaction records, source identity and preference restoration are real.
import control_runtime
for failure in (None, 'ready', 'port', 'stop'):
    with tempfile.TemporaryDirectory() as folder:
        home = Path(folder)
        account = Mock(pw_uid=os.getuid(), pw_gid=os.getgid(), pw_name='fixture', pw_dir=str(home))
        deployment = home / '.local/src/ovos-skill-jarvis-dispatcher'
        deployment.mkdir(parents=True)
        code = deployment / 'managed.py'
        code.write_text('old source\n')
        capabilities = home / '.config/jarvis/capabilities.json'
        install.atomic(capabilities, {'future': 'preserve'})
        router = home / '.config/jarvis/router.json'
        install.atomic(router, {'backend': 'jarvis', 'model': model.MODEL, 'future': 'preserve'})
        old_router = router.read_bytes()
        preference = {'schema_version': 1, 'enabled': True, 'model_binary': '/usr/bin/ollama', 'future': 9}
        install.atomic(home / install.CHOICE, preference)
        store = model.private_root(home) / 'models' / model.MANIFEST
        store.parent.mkdir(parents=True)
        store.write_text('fixture model store already exists')
        original_tree = install.tree_identity(deployment)
        units, rule, _ = prepare.render(os.getuid(), os.getgid(), 'fixture', home, deployment, '/usr/bin/ollama')
        backup = home / '.local/state/jarvis/backups/fixture'
        calls = []

        def child(command, environment):
            assert environment['JARVIS_ISOLATION_TRANSACTION'] == str(home / install.JOURNAL)
            assert install.installation_blocked(home)
            backup.mkdir(parents=True)
            shutil.copytree(deployment, backup / 'target-root')
            value = json.loads((home / install.JOURNAL).read_text())
            install.atomic(home / install.JOURNAL, dict(value, backup=str(backup)))
            code.write_text('new source\n')
            install.atomic(home / '.local/state/jarvis/current.json', {'rollback': str(backup)})
            return 0

        def stop(home, was_active, record=None):
            desired = ['ovos-audio.service', 'ovos-core.service']
            if record is not None:
                record(desired)
                if failure == 'stop':
                    raise RuntimeError('injected service stop failure')
            return desired

        def native_process(command, **kwargs):
            calls.append(command)
            assert 'ollama.service' not in command  # Never control the general daemon.
            if command[0] == 'bash':
                assert command[2:] == [str(backup), '--no-restart']
                code.write_bytes((backup / 'target-root/managed.py').read_bytes())
            return Mock(returncode=0)

        with patch.object(Path, 'home', return_value=home), \
             patch.object(install.pwd, 'getpwuid', return_value=account), \
             patch.object(install, 'active', return_value=True), \
             patch.object(install, 'native_snapshot', return_value=(units, rule, '/usr/bin/ollama')), \
             patch.object(install, 'stop_workers', side_effect=stop), \
             patch.object(install, 'run_child', side_effect=child), \
             patch.object(install, 'restore_running') as restarted, \
             patch.object(install.Native, 'approve', side_effect=AssertionError('Routine upgrade must not authenticate')), \
             patch.object(install.subprocess, 'run', side_effect=native_process), \
             patch.object(model, 'verify_executable', return_value='/usr/bin/ollama'), \
             patch.object(model, 'prepare_models'), \
             patch.object(model, 'require_free_port', side_effect=RuntimeError('injected occupied port') if failure == 'port' else None), \
             patch.object(model, 'wait_model', side_effect=[RuntimeError('injected readiness failure'), None] if failure == 'ready' else [None]), \
             patch.object(control_runtime, 'service_action'), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            if failure:
                rejects(install.run_install, [], home)
                assert install.tree_identity(deployment) == original_tree
                assert router.read_bytes() == old_router
            else:
                assert install.run_install([], home) == 0
                assert code.read_text() == 'new source\n'
            assert not (home / install.JOURNAL).exists()
            assert json.loads((home / install.CHOICE).read_text()) == preference
            assert json.loads(capabilities.read_text()) == {'future': 'preserve'}
            assert restarted.call_args.args[0] == ['ovos-audio.service', 'ovos-core.service']
            assert 'ovos-listener.service' not in restarted.call_args.args[0]

# Crash recovery revalidates native identity before stopping, then validates
# stopped state before rollback. The same lock excludes concurrent recovery.
with tempfile.TemporaryDirectory() as folder:
    home = Path(folder)
    account = Mock(pw_uid=os.getuid(), pw_gid=os.getgid(), pw_name='fixture', pw_dir=str(home))
    state = home / install.JOURNAL
    install.atomic(state, {'schema_version': 1, 'uid': os.getuid(), 'pid': 0,
                          'process_start': 'dead', 'token': 'x' * 40, 'phase': 'checking',
                          'was_active': True, 'binary': '/usr/bin/ollama',
                          'original_binary': '/usr/bin/ollama', 'native_started': False,
                          'previous_desired': ['ovos-core.service', 'ovos-audio.service']})
    order = []

    def authorised(operation, target, **kwargs):
        assert operation == 'rollback' and target == home
        order.append('identity' if kwargs.get('require_stopped') is False else 'stopped')

    def recovered(target, journal, native):
        assert order == ['identity', 'stop', 'stopped']
        assert journal['pid'] == os.getpid() and journal['token'] != 'x' * 40
        def competing():
            with install.installation_lock(home):
                raise AssertionError('Concurrent recovery acquired the installation lock')
        rejects(competing)
        state.unlink()

    with patch.object(Path, 'home', return_value=home), \
         patch.object(install.pwd, 'getpwuid', return_value=account), \
         patch.object(model, 'verify_executable', return_value='/usr/bin/ollama'), \
         patch.object(install, 'active', return_value=True), \
         patch.object(install, 'authorised_transaction', side_effect=authorised), \
         patch.object(install, 'stop_workers', side_effect=lambda *_: order.append('stop')), \
         patch.object(install, 'recover_transaction', side_effect=recovered), \
         patch.object(install.subprocess, 'run', return_value=Mock(returncode=0)), \
         patch.dict(os.environ):
        assert install.resume_recovery(home) == 0
        assert order == ['identity', 'stop', 'stopped']
        assert not state.exists()

print('PASS: full coordinator success, readiness/port/stop recovery, muted-state retention and exclusive crash recovery')

print('PASS: complete steady upgrade and failed-readiness recovery preserve source, native policy, private settings and muted microphone without administrator prompts')
