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
import subprocess
import sys
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


# Exercise the real main/guard imports under systemd's Python -I invocation.
# Stub only privileged identity, runtime pins and OVOS execution boundaries;
# do not add the script directory or stub the installer guard in the child.
bootstrap = '''
import os, runpy, sys, types
path, component = sys.argv[1:]
events = []
namespace = runpy.run_path(path)
namespace['main'].__globals__.update(
    worker_identity=lambda *args: events.append('identity'),
    verify_pins=lambda: events.append('pins'),
    install_overlay=lambda component: events.append('overlay'),
    run_component=lambda component: events.append('run'))
boundary = types.ModuleType('verify_core_isolation')
boundary.attach = lambda *args: None
sys.modules['verify_core_isolation'] = boundary
sys.argv = [path, component, '--uid', str(os.getuid()), '--gid', str(os.getgid())]
try:
    namespace['main']()
except RuntimeError as error:
    assert 'Managed installation is incomplete' in str(error), str(error)
    assert events == ['identity'], events
    print('BLOCKED')
else:
    assert events == ['identity', 'pins', 'overlay', 'run'], events
    print('STARTED')
'''
for phase in (None, 'checking', 'recovering-ready', 'blocked'):
    with tempfile.TemporaryDirectory() as folder:
        home = Path(folder)
        if phase is not None:
            install.atomic(home / install.JOURNAL, {'phase': phase})
        for component in ('core', 'listener', 'audio'):
            child = subprocess.run([sys.executable, '-I', '-c', bootstrap,
                                    str(Path(__file__).with_name('isolation_worker.py')), component],
                                   env={**os.environ, 'HOME': str(home)}, cwd=home,
                                   capture_output=True, text=True, timeout=20)
            assert child.returncode == 0, child.stderr
            assert child.stdout.strip() == ('BLOCKED' if phase == 'blocked' else 'STARTED')
print('PASS: actual Python -I worker imports and real interrupted-install guard before runtime startup')

# A failed worker may be restored during recovery only when the actual worker
# and any control process are gone. Missing/unknown state fails closed.
stopped = {'ActiveState': 'failed', 'SubState': 'failed', 'MainPID': '0', 'ControlPID': '0'}
for isolated in (False, True):
    with patch.object(install, 'properties', return_value=stopped), \
         patch.object(install, 'LOGICAL', services.LOGICAL), \
         patch('control_runtime.operation_lock', return_value=contextlib.nullcontext()), \
         patch('control_runtime.run') as command, patch('control_runtime.service_action') as strict:
        install.stop_workers(Path.home(), isolated, recovery=True)
        assert command.call_count == 1 and not strict.called
        install.stop_workers(Path.home(), True)
        strict.assert_called_once_with('stop', print)
        for unsafe in ({}, dict(stopped, MainPID='42'), dict(stopped, ControlPID='42'),
                       dict(stopped, ActiveState='active'), dict(stopped, SubState='stop-sigterm')):
            with patch.object(install, 'properties', return_value=unsafe):
                rejects(install.stop_workers, Path.home(), isolated, recovery=True)
print('PASS: recovery accepts verified stopped failed workers and rejects live, stopping or unknown state')


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
        rejects(model.remove_private_model, home)
        (copied / blob_name).write_bytes(blob)
        (copied / 'unreviewed').write_bytes(b'keep')
        rejects(model.remove_private_model, home)
        (copied / 'unreviewed').unlink()
        model.remove_private_model(home)
        assert not copied.exists() and (source / blob_name).read_bytes() == blob
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

        def stop(home, was_active, record=None, *, recovery=False):
            assert recovery == (record is None)
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
         patch.object(install, 'stop_workers', side_effect=lambda *_, **kw: order.append('stop') if kw == {'recovery': True} else (_ for _ in ()).throw(AssertionError('Recovery mode required'))), \
         patch.object(install, 'recover_transaction', side_effect=recovered), \
         patch.object(install.subprocess, 'run', return_value=Mock(returncode=0)), \
         patch.dict(os.environ):
        assert install.resume_recovery(home) == 0
        assert order == ['identity', 'stop', 'stopped']
        assert not state.exists()

print('PASS: full coordinator success, readiness/port/stop recovery, muted-state retention and exclusive crash recovery')

# A partial first native installation can remove only its exact new data.
# Foreign content stops recovery and retains the startup guard for review.
for foreign in (False, True):
    with tempfile.TemporaryDirectory() as folder:
        home = Path(folder)
        account = Mock(pw_uid=os.getuid(), pw_gid=os.getgid(), pw_name='fixture', pw_dir=str(home))
        units, rule, _ = prepare.render(os.getuid(), os.getgid(), 'fixture', home,
                                       home / '.local/src/ovos-skill-jarvis-dispatcher', '/usr/bin/ollama')
        names = list(units)
        native_files = {Path('/etc/systemd/system') / name: units[name] for name in (names[0], names[-1])}
        if foreign:
            native_files[Path('/etc/systemd/system') / names[0]] = 'unreviewed native content'
        rule_path = Path('/etc/polkit-1/rules.d') / f'90-jarvis-v4-{os.getuid()}.rules'
        native_files[rule_path] = rule
        journal = {'schema_version': 1, 'uid': os.getuid(), 'binary': '/usr/bin/ollama',
                   'original_binary': None, 'was_active': False, 'native_started': True,
                   'previous_desired': [], 'token': 'x' * 40, 'original_router': None,
                   'original_choice': None, 'original_tree': None}
        state = home / install.JOURNAL
        install.atomic(state, journal)
        exists = Path.exists
        original_regular = install.regular
        operations = []

        def present(path):
            if str(path).startswith('/etc/systemd/system/jarvis-v4-') or path == rule_path:
                return path in native_files
            return exists(path)

        def read(path, **kwargs):
            return native_files[path] if path in native_files else original_regular(path, **kwargs)

        def native(tool, *arguments, **kwargs):
            operations.append((tool, arguments))
            if tool == 'rm':
                assert arguments[0] == '--'
                native_files.pop(arguments[1])
            elif tool == 'sha256sum':
                return Mock(returncode=0, stdout=hashlib.sha256(native_files[rule_path].encode()).hexdigest() + ' rule', stderr='')
            elif tool == 'stat':
                return Mock(returncode=0, stdout='0 81a4', stderr='')
            else:
                assert tool == 'systemctl' and arguments[0] in {'stop', 'daemon-reload'}
                if arguments[0] == 'stop':
                    assert set(arguments[1:]) == set(units)
            return Mock(returncode=0)

        with patch.object(install.pwd, 'getpwuid', return_value=account), \
             patch.object(install, 'active', return_value=False), \
             patch.object(install, 'stop_workers', return_value=[]), \
             patch.object(install, 'restore_running') as restarted, \
             patch.object(install, 'regular', side_effect=read), \
             patch.object(Path, 'exists', present), \
             contextlib.redirect_stderr(io.StringIO()):
            if foreign:
                rejects(install.recover_transaction, home, journal, Mock(run=native))
                assert json.loads(state.read_text())['phase'] == 'blocked'
                assert len(native_files) == 3 and not restarted.called
            else:
                install.recover_transaction(home, journal, Mock(run=native))
                assert not native_files and not state.exists()
                restarted.assert_called_once_with([])

print('PASS: partial native installation removal and refusal to overwrite unreviewed recovery data')

print('PASS: complete steady upgrade and failed-readiness recovery preserve source, native policy, private settings and muted microphone without administrator prompts')
