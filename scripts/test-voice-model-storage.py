#!/usr/bin/env python3
"""Regression: cache cleanup cannot remove the required Jarvis speech assets."""
import contextlib
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

import voice_models as models
import cleanup_artifacts as cleanup
import isolation_install as installation

if os.getuid() == 0:
    raise SystemExit('Run speech storage tests as the ordinary user, without sudo.')

real_policy = models.policy()
assert sum(len(r['files']) for r in real_policy['repositories']) == 7
fixture = deepcopy(real_policy)
payloads = {}
for repo in fixture['repositories']:
    for item in repo['files']:
        data = ('fixture:' + repo['repo'] + '/' + item['path']).encode()
        payloads[repo['repo'], item['path']] = data
        item.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def rejected(call):
    try:
        call()
    except (ValueError, RuntimeError, OSError):
        return
    raise AssertionError('Unsafe speech operation was accepted')


def download(repo, item, directory):
    path = directory / item['path']
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payloads[repo['repo'], item['path']])
    return path


with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
    home = Path(folder)
    assert models.inspect(home, fixture)
    models.prepare(home, fixture, download)
    assert not models.inspect(home, fixture)
    original = {p: p.read_bytes() for p in models.hub_root(home).rglob('*') if p.is_file()}
    (home / '.cache/huggingface').mkdir(parents=True)
    (home / '.cache/huggingface/disposable').write_text('fixture')
    shutil.rmtree(home / '.cache')
    assert not models.inspect(home, fixture)
    models.prepare(home, fixture, lambda *_: (_ for _ in ()).throw(AssertionError('Repeated download')))
    assert all(p.read_bytes() == data for p, data in original.items())
    assert not list(models.model_root(home).glob('.prepare-*'))
    # A killed preparation is cleaned only while holding the model lock.
    abandoned = models.model_root(home) / '.prepare-fixture'
    abandoned.mkdir()
    (abandoned / '.jarvis-model-stage').write_text('jarvis-speech-download-v1\n')
    (abandoned / 'partial').write_text('incomplete')
    unmarked = models.model_root(home) / '.prepare-owner-data'
    unmarked.mkdir()
    models.prepare(home, fixture, download)
    assert not abandoned.exists() and unmarked.exists()
    # Restore only a deleted required file. Corruption is also detectable.
    item = fixture['repositories'][0]['files'][0]
    path = models.snapshot_path(models.hub_root(home), fixture['repositories'][0], item)
    path.unlink()
    assert models.inspect(home, fixture)
    models.prepare(home, fixture, download)
    path.write_bytes(b'x' * item['bytes'])
    assert models.inspect(home, fixture)
    models.prepare(home, fixture, download)
    assert not models.inspect(home, fixture)
print('PASS: permanent model bytes survive cache deletion; repair, hashes, idempotence and staged-file cleanup')

with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
    home = Path(folder)
    old = home / '.cache/huggingface/hub'
    for repo in fixture['repositories']:
        base = models.repository_root(old, repo)
        for item in repo['files']:
            data = payloads[repo['repo'], item['path']]
            blob = base / 'blobs' / item['sha256']
            blob.parent.mkdir(parents=True, exist_ok=True)
            blob.write_bytes(data)
            snapshot = base / 'snapshots' / ('f' * 40) / item['path']
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.symlink_to(blob)
    before = {p: p.read_bytes() for p in old.rglob('*') if p.is_file()}
    with patch.dict(os.environ, HF_HUB_CACHE=str(old)):
        models.prepare(home, fixture, lambda *_: (_ for _ in ()).throw(AssertionError('Migration downloaded')))
    assert not models.inspect(home, fixture)
    assert all(p.read_bytes() == data for p, data in before.items())
    shutil.rmtree(home / '.cache')
    assert not models.inspect(home, fixture)
print('PASS: verified legacy hub migration copies real bytes and leaves shared cache data untouched')

with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
    home = Path(folder)
    def corrupt(repo, item, directory):
        path = download(repo, item, directory)
        if repo == fixture['repositories'][-1]:
            path.write_bytes(b'corrupt')
        return path
    rejected(lambda: models.prepare(home, fixture, corrupt))
    assert not models.hub_root(home).exists()
    assert not list(models.model_root(home).glob('.prepare-*'))
    rejected(lambda: models.prepare(home, fixture,
        lambda *_: (_ for _ in ()).throw(InterruptedError('Fixture cancellation'))))
    assert not list(models.model_root(home).glob('.prepare-*'))
    outside = home / 'owner-data'
    outside.mkdir()
    models.hub_root(home).symlink_to(outside, target_is_directory=True)
    rejected(lambda: models.prepare(home, fixture, download))
    assert not list(outside.iterdir())
print('PASS: corrupt/cancelled downloads publish no model references; symlink destinations are refused')

with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
    home = Path(folder)
    models.prepare(home, fixture, download)
    config = home / '.config/mycroft/mycroft.conf'
    config.parent.mkdir(parents=True)
    value = {'stt': {'module': 'ovos-stt-plugin-fasterwhisper',
                    'ovos-stt-plugin-fasterwhisper': {
                        'model': str(models.model_root(home) / 'faster-whisper-small.en'),
                        'initial_prompt': 'fixture', 'cpu_threads': 3}},
             'listener': {'microphone': {'device': 'owner-choice'}}, 'future': {'keep': 1}}
    config.write_text(json.dumps(value))
    with patch.object(models, 'policy', return_value=fixture):
        models.migrate_config(home)
    expected = deepcopy(value)
    expected['stt']['ovos-stt-plugin-fasterwhisper']['model'] = 'small.en'
    assert json.loads(config.read_text()) == expected
    value['stt']['ovos-stt-plugin-fasterwhisper']['model'] = '/owner/custom-model'
    config.write_text(json.dumps(value))
    before = config.read_bytes()
    models.migrate_config(home)
    assert config.read_bytes() == before
    with patch.dict(os.environ, HF_HUB_CACHE='/disposable/fixture'):
        models.configure_environment(home)
        assert os.environ['HF_HUB_CACHE'] == str(models.hub_root(home))
        assert os.environ['HF_HUB_OFFLINE'] == '1'
    with patch.dict(os.environ, HF_HUB_CACHE='/owner/custom-hub'):
        models.configure_environment(home, 'listener')
        assert os.environ['HF_HUB_CACHE'] == '/owner/custom-hub'
    config.write_text(json.dumps(expected))
    with patch.dict(os.environ, HF_HUB_CACHE='/disposable/fixture'):
        models.configure_environment(home, 'listener')
        assert os.environ['HF_HUB_CACHE'] == str(models.hub_root(home))
print('PASS: prior repair adoption preserves hints/hardware/unknown fields; custom model settings stay unchanged')

with tempfile.TemporaryDirectory() as folder:
    home = Path(folder)
    base = home / '.local/state/jarvis'
    base.mkdir(parents=True)
    live = base / 'stage.20260101-120000-000001.ABC123'
    live.mkdir(mode=0o700)
    cleanup.mark(live, home, os.getpid())
    stale = base / 'stage.20260101-120000-000002.ABC123'
    stale.mkdir(mode=0o700)
    cleanup.mark(stale, home, os.getpid())
    entry = json.loads((stale / cleanup.MARKER).read_text())
    entry['boot'] = '00000000-0000-0000-0000-000000000000'
    (stale / cleanup.MARKER).write_text(json.dumps(entry))
    owner = home / 'owner-file'
    owner.write_text('preserve')
    (stale / 'link').symlink_to(owner)
    legacy = base / 'stage.20260101-120000-000003.ABC123'
    legacy.mkdir(mode=0o700)
    (base / 'backups').mkdir()
    (base / 'backups/preserve').write_text('rollback')
    assert cleanup.clean(home) == [stale.name] and stale.exists()
    journal = base / 'isolation-install/current.json'
    journal.parent.mkdir()
    journal.write_text('{}')
    assert cleanup.clean(home, True) == [] and stale.exists()
    journal.unlink()
    assert cleanup.clean(home, True) == [stale.name]
    assert not stale.exists() and live.exists() and legacy.exists()
    assert owner.read_text() == 'preserve' and (base / 'backups/preserve').read_text() == 'rollback'
print('PASS: staging cleanup is read-only by default and preserves live, unmarked, backup and recovery data')

with tempfile.TemporaryDirectory() as folder:
    root = Path(folder)
    for failed in (False, True):
        directory = root / ('native-failed' if failed else 'native-success')
        try:
            with installation.native_files(directory):
                (directory / 'reviewed-unit.service').write_text('fixture')
                if failed:
                    raise InterruptedError('Fixture cancellation')
        except InterruptedError:
            pass
        assert not directory.exists()
    owner = root / 'owner'
    owner.mkdir()
    linked = root / 'native-link'
    linked.symlink_to(owner, target_is_directory=True)
    rejected(lambda: installation.native_files(linked).__enter__())
    assert owner.exists()
print('PASS: native installation/recovery scratch is removed on success and cancellation without following links')

with tempfile.TemporaryDirectory() as folder:
    home = Path(folder)
    base = (home / installation.JOURNAL).parent
    base.mkdir(parents=True)
    stale = base / 'native-ABCDEF123456'
    stale.mkdir(mode=0o700)
    path = stale / 'reviewed.service'
    path.write_text('exact generated fixture')
    path.chmod(0o600)
    unknown = base / 'restore-0123456789abcdef'
    unknown.mkdir(mode=0o700)
    (unknown / 'owner-data').write_text('preserve')
    with patch.object(installation, 'render', return_value=({'reviewed.service': 'exact generated fixture'}, 'rule', {})), \
         patch.object(installation, 'read_choice', return_value=None):
        journal = home / installation.JOURNAL
        journal.write_text('{}')
        assert installation.cleanup_native_artifacts(home) == []
        journal.unlink()
        assert installation.cleanup_native_artifacts(home) == [stale.name]
        assert not stale.exists() and (unknown / 'owner-data').read_text() == 'preserve'
print('PASS: exact legacy native-text leftovers are cleaned only after recovery; unknown content is preserved')
