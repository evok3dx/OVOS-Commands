#!/usr/bin/env python3
"""Prepare hash-verified speech assets in permanent, Jarvis-owned data storage.

Only setup downloads. Workers use the same fixed hub directory offline. The
Hugging Face directory layout is an API compatibility detail, not permission
to place required model bytes in a disposable XDG cache.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import stat
import tempfile

POLICY = Path(__file__).resolve().parents[1] / 'voice/managed-models.json'
REPOSITORIES = {'Systran/faster-whisper-small.en', 'OpenVoiceOS/phoonnx-styletts2',
                'onnx-community/Kokoro-82M-v1.0-ONNX'}


def model_root(home: Path) -> Path:
    return Path(home) / '.local/share/jarvis/models'


def hub_root(home: Path) -> Path:
    return model_root(home) / 'hub'


def configure_environment(home: Path | None = None, component: str | None = None) -> None:
    """Select durable Jarvis storage before any Hugging Face/voice imports."""
    home = home or Path.home()
    if component is not None:
        # A deliberately different voice/model keeps its existing library
        # storage policy. Do not strand custom Hugging Face model identifiers.
        try:
            config = json.loads((home / '.config/mycroft/mycroft.conf').read_text())
            if component == 'audio':
                section = config.get('tts', {})
                selected = (section.get('module') == 'ovos-tts-plugin-phoonnx'
                            and section.get('ovos-tts-plugin-phoonnx', {}).get('voice') == 'kokoro/af_bella')
            elif component == 'listener':
                section = config.get('stt', {})
                selected = (section.get('module') == 'ovos-stt-plugin-fasterwhisper'
                            and section.get('ovos-stt-plugin-fasterwhisper', {}).get('model') in
                            ('small.en', str(model_root(home) / 'faster-whisper-small.en')))
            else:
                return
            if not selected:
                return
        except (OSError, ValueError, AttributeError):
            return  # Let the existing voice configuration report its error.
    os.environ['HF_HUB_CACHE'] = str(hub_root(home))
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'


def policy(path: Path = POLICY) -> dict:
    value = json.loads(path.read_text())
    repositories = value.get('repositories', [])
    if (value.get('schema_version') != 1 or len(repositories) != 3
            or {r['repo'] for r in repositories} != REPOSITORIES):
        raise ValueError('Speech model policy needs review')
    for repo in repositories:
        if not re.fullmatch('[0-9a-f]{40}', repo['revision']):
            raise ValueError('Speech revision must be immutable')
        seen = set()
        for item in repo['files']:
            name = item['path']
            parts = PurePosixPath(name)
            if (not name or parts.is_absolute() or str(parts) != name
                    or '..' in parts.parts or '\\' in name or name in seen
                    or not re.fullmatch(r'[A-Za-z0-9_./-]+', name)
                    or type(item['bytes']) is not int or not 0 < item['bytes'] < 1_000_000_000
                    or not re.fullmatch('[0-9a-f]{64}', item['sha256'])):
                raise ValueError('Speech artifact policy needs review')
            seen.add(name)
        if not seen:
            raise ValueError('Empty speech repository policy')
    return value


def safe_path(path: Path, home: Path) -> None:
    """Refuse links, foreign ownership and writable-by-everyone app paths."""
    if not path.is_relative_to(home) or path == home:
        raise ValueError('Speech storage must be inside the current home')
    for node in (path, *path.parents):
        if node == home.parent:
            break
        if node.is_symlink():
            raise ValueError('Speech storage must not follow symbolic links')
        if node.exists():
            info = node.stat()
            if info.st_uid != os.getuid() or info.st_mode & stat.S_IWOTH:
                raise ValueError('Speech storage ownership or permissions need review')


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as source:
        while chunk := source.read(1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def valid_file(path: Path, item: dict, *, hashed: bool = True) -> bool:
    try:
        info = path.stat()
        return (stat.S_ISREG(info.st_mode) and info.st_size == item['bytes']
                and (not hashed or digest(path) == item['sha256']))
    except OSError:
        return False


def repository_root(hub: Path, repo: dict) -> Path:
    return hub / ('models--' + repo['repo'].replace('/', '--'))


def snapshot_path(hub: Path, repo: dict, item: dict) -> Path:
    return repository_root(hub, repo) / 'snapshots' / repo['revision'] / item['path']


def inspect(home: Path, document: dict | None = None, *, hashed: bool = True) -> list[str]:
    """Read only. A missing required file is a failure, not an empty log."""
    document = document or policy()
    missing = []
    hub = hub_root(home)
    for repo in document['repositories']:
        ref = repository_root(hub, repo) / 'refs/main'
        try:
            safe_path(ref, home)
            if ref.read_text().strip() != repo['revision']:
                missing.append(repo['repo'] + ':revision')
        except (OSError, ValueError):
            missing.append(repo['repo'] + ':revision')
        for item in repo['files']:
            path = snapshot_path(hub, repo, item)
            try:
                safe_path(path, home)
                if not valid_file(path, item, hashed=hashed):
                    missing.append(repo['repo'] + ':' + item['path'])
            except (OSError, ValueError):
                missing.append(repo['repo'] + ':' + item['path'])
    return missing


def legacy_hub(home: Path) -> Path:
    """Use the prior library location only as a read-only migration source."""
    if os.environ.get('HF_HUB_CACHE'):
        return Path(os.environ['HF_HUB_CACHE'])
    if os.environ.get('HUGGINGFACE_HUB_CACHE'):
        return Path(os.environ['HUGGINGFACE_HUB_CACHE'])
    if os.environ.get('HF_HOME'):
        return Path(os.environ['HF_HOME']) / 'hub'
    return Path(os.environ.get('XDG_CACHE_HOME', str(home / '.cache'))) / 'huggingface/hub'


def cached_source(old: Path, repo: dict, item: dict, home: Path) -> Path | None:
    """Accept only matching bytes from this user's hub or known prior repair."""
    if old.is_relative_to(home) and old != hub_root(home):
        root = repository_root(old, repo)
        if root.is_dir() and not any(p.is_symlink() for p in (root, *root.parents)):
            for path in sorted((root / 'snapshots').glob('*/' + item['path'])):
                # Hub snapshots may link only to their own blob directory.
                resolved = path.resolve()
                if (resolved.is_relative_to(root) and resolved.is_file()
                        and resolved.stat().st_uid == os.getuid() and valid_file(resolved, item)):
                    return resolved
    if repo['repo'] == 'Systran/faster-whisper-small.en':
        path = model_root(home) / 'faster-whisper-small.en' / item['path']
        try:
            safe_path(path, home)
            if valid_file(path, item):
                return path
        except (OSError, ValueError):
            pass
    return None


def fetch(repo: dict, item: dict, directory: Path) -> Path:
    # Xet chunks are disposable download work too, not an additional permanent
    # model copy hidden in the account's general cache.
    os.environ['HF_XET_CACHE'] = str(directory.parent / '.download-cache')
    from huggingface_hub import hf_hub_download
    return Path(hf_hub_download(repo_id=repo['repo'], filename=item['path'],
                               revision=repo['revision'], local_dir=str(directory)))


def atomic_text(path: Path, value: str, home: Path) -> None:
    safe_path(path, home)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def prepare(home: Path, document: dict | None = None, downloader=fetch) -> None:
    if os.getuid() == 0:
        raise RuntimeError('Prepare speech models as the desktop user, without sudo')
    home = Path(home)
    document = document or policy()
    old = legacy_hub(home)
    root = model_root(home)
    safe_path(root, home)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = root / 'prepare.lock'
    safe_path(lock, home)
    with lock.open('a') as guard:
        os.chmod(lock, 0o600)
        fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for abandoned in root.glob('.prepare-*'):
            marker = abandoned / '.jarvis-model-stage'
            try:
                safe_path(marker, home)
                if (not marker.is_file() or marker.stat().st_size > 64
                        or marker.read_text() != 'jarvis-speech-download-v1\n'):
                    continue
                # No other model preparation can hold the operation lock here.
                # Refuse links/special/foreign files before a bounded removal.
                for child in abandoned.rglob('*'):
                    safe_path(child, home)
                    if not (child.is_dir() or child.is_file()):
                        raise ValueError('Unexpected staged speech data')
                if not shutil.rmtree.avoids_symlink_attacks:
                    raise ValueError('Safe directory removal unavailable')
                shutil.rmtree(abandoned)
            except (OSError, ValueError):
                continue
        if not inspect(home, document):
            print('Permanent speech models are verified.', flush=True)
            return
        # Never use the disposable system/XDG cache for the final model bytes.
        # The temporary download metadata and incomplete payloads are removed
        # on both success and ordinary failure/cancellation.
        with tempfile.TemporaryDirectory(prefix='.prepare-', dir=root) as name:
            stage = Path(name)
            (stage / '.jarvis-model-stage').write_text('jarvis-speech-download-v1\n')
            pending = []
            for repo in document['repositories']:
                for item in repo['files']:
                    destination = snapshot_path(hub_root(home), repo, item)
                    safe_path(destination, home)
                    if valid_file(destination, item):
                        continue
                    source = cached_source(old, repo, item, home)
                    local = stage / repo['repo'].replace('/', '--') / item['path']
                    local.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                    if source is not None:
                        shutil.copyfile(source, local)
                    else:
                        print('Preparing speech model: ' + repo['repo'] + '/' + item['path'], flush=True)
                        source = downloader(repo, item, stage / repo['repo'].replace('/', '--'))
                        if source != local:
                            shutil.copyfile(source, local)
                    if local.is_symlink() or not valid_file(local, item):
                        raise RuntimeError('Speech model download failed SHA-256/size verification')
                    local.chmod(0o600)
                    pending.append((local, destination))
            # Do not publish a reference to a partial or unverified download.
            for source, destination in pending:
                safe_path(destination, home)
                destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                os.replace(source, destination)
            for repo in document['repositories']:
                atomic_text(repository_root(hub_root(home), repo) / 'refs/main', repo['revision'], home)
        if inspect(home, document):
            raise RuntimeError('Permanent speech model verification failed')
    print('Permanent speech models are verified.', flush=True)


def migrate_config(home: Path) -> None:
    """Adopt only the exact earlier owner repair; retain every other setting."""
    path = home / '.config/mycroft/mycroft.conf'
    safe_path(path, home)
    before = path.read_text()
    value = json.loads(before)
    stt = value.get('stt', {})
    plugin = stt.get('ovos-stt-plugin-fasterwhisper', {})
    if (stt.get('module') != 'ovos-stt-plugin-fasterwhisper'
            or plugin.get('model') != str(model_root(home) / 'faster-whisper-small.en')):
        return
    if inspect(home):
        raise RuntimeError('Verify permanent speech models before migrating the prior repair')
    plugin['model'] = 'small.en'
    if path.read_text() != before:
        raise RuntimeError('Speech settings changed during migration')
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True) + '\n', home)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--prepare', action='store_true')
    actions.add_argument('--migrate-config', action='store_true')
    parser.add_argument('--home', type=Path, default=Path.home())
    args = parser.parse_args()
    if args.prepare:
        signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(InterruptedError('Speech setup cancelled')))
        prepare(args.home)
    elif args.migrate_config:
        migrate_config(args.home)
    else:
        missing = inspect(args.home)
        if missing:
            print('Required permanent speech files are missing or invalid. Run Jarvis setup to repair them.')
            return 1
        print('Permanent speech models are verified.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
