"""Prepare only Jarvis's model data; reuse a trusted Ollama executable.

No daemon modification, root Python, general model deletion or shared store.
"""
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import tempfile
import time

from model_endpoint import PRIVATE_PORT, GENERAL_PORT

MODEL = 'qwen3:4b-instruct-2507-q4_K_M'
MANIFEST = Path('manifests/registry.ollama.ai/library/qwen3/4b-instruct-2507-q4_K_M')


def private_root(home=None):
    return Path(home or Path.home()) / '.local/share/jarvis/ollama'


def unit_name(uid=None):
    return f'jarvis-v4-{os.getuid() if uid is None else uid}-ollama.service'


def executable():
    name = shutil.which('ollama')
    if not name:
        raise RuntimeError('Install Ollama first. Jarvis does not install another AI platform.')
    return verify_executable(name)


def verify_executable(name):
    path = Path(name).resolve(strict=True)
    for item in (path, *path.parents):
        info = item.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise RuntimeError('The Ollama executable must be administrator-owned and not writable by other users.')
    if not path.is_file() or not os.access(path, os.X_OK):
        raise RuntimeError('Ollama executable unavailable')
    return str(path)


def request(port, method='GET', route='/api/tags', payload=None, timeout=3):
    if port not in (GENERAL_PORT, PRIVATE_PORT):
        raise ValueError('Unreviewed model endpoint')
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=timeout)
    try:
        body = None if payload is None else json.dumps(payload).encode()
        connection.request(method, route, body=body,
                           headers={'Content-Type': 'application/json'})
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError('Local model endpoint did not accept the request')
        raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise RuntimeError('Oversized model inventory')
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError('Invalid model response')
        return value
    finally:
        connection.close()


def inventory_digest(port):
    for item in request(port).get('models', []):
        if isinstance(item, dict) and item.get('name') == MODEL:
            digest = item.get('digest', '').removeprefix('sha256:')
            if re.fullmatch('[a-f0-9]{64}', digest):
                return digest
    raise RuntimeError('The reviewed Jarvis model is missing from this instance')


def regular_path(path):
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise ValueError('Model storage must not contain symlinks')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('Model data must be regular files')
    return info


def digest_file(path):
    regular_path(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def model_files(store, expected=None):
    manifest = store / MANIFEST
    info = regular_path(manifest)
    if info.st_size > 65536:
        raise ValueError('Oversized model manifest')
    raw = manifest.read_bytes()
    if expected and hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Model manifest does not match Ollama inventory')
    data = json.loads(raw)
    if (not isinstance(data, dict) or not isinstance(data.get('config'), dict)
            or not isinstance(data.get('layers'), list)
            or any(not isinstance(record, dict) for record in data['layers'])):
        raise ValueError('Invalid model manifest structure')
    records = [data['config'], *data['layers']]
    if not 1 <= len(records) <= 32:
        raise ValueError('Model layer count needs review')
    files = {MANIFEST: (hashlib.sha256(raw).hexdigest(), len(raw))}
    total = 0
    for record in records:
        digest, size = record.get('digest'), record.get('size')
        if not isinstance(digest, str) or not re.fullmatch('sha256:[a-f0-9]{64}', digest):
            raise ValueError('Invalid model layer digest')
        if type(size) is not int or not 0 < size <= 8_000_000_000:
            raise ValueError('Invalid model layer size')
        total += size
        if total > 10_000_000_000:
            raise ValueError('Model exceeds the reviewed storage bound')
        files[Path('blobs') / digest.replace(':', '-')] = (digest[7:], size)
    return files


def source_stores(home):
    roots = [home / '.ollama/models', Path('/usr/share/ollama/.ollama/models')]
    # Read only OLLAMA_MODELS from the existing service's public environment;
    # never print or copy the other environment fields.
    result = subprocess.run(['/usr/bin/systemctl', '--system', '--no-ask-password',
                             'show', 'ollama.service', '--property=Environment', '--value'],
                            capture_output=True, text=True, timeout=5)
    if result.returncode == 0 and len(result.stdout) <= 65536:
        import shlex
        for token in shlex.split(result.stdout):
            if token.startswith('OLLAMA_MODELS='):
                path = Path(token.split('=', 1)[1])
                if path.is_absolute():
                    roots.insert(0, path)
    return roots


def prepare_models(home, report=print):
    """Copy this one content-addressed model without modifying its source."""
    home = Path(home)
    destination = private_root(home) / 'models'
    if any(p.is_symlink() for p in (destination, *destination.parents)):
        raise ValueError('Private model directory must be regular')
    if (destination / MANIFEST).exists():
        files = model_files(destination)
        for name, (digest, size) in files.items():
            path = destination / name
            if regular_path(path).st_size != size or digest_file(path) != digest:
                raise RuntimeError('Private model integrity failed; existing model data was preserved')
        return
    expected = inventory_digest(GENERAL_PORT)
    source = None
    for candidate in source_stores(home):
        try:
            files = model_files(candidate, expected)
            source = candidate
            break
        except FileNotFoundError:
            continue
    if source is None:
        raise RuntimeError('The existing model storage could not be located. No general Ollama settings changed.')
    total = sum(size for _, size in files.values())
    parent = destination.parent
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if parent.stat().st_uid != os.getuid() or parent.stat().st_mode & 0o077:
        raise ValueError('Private model home must belong to this user and be private')
    if shutil.disk_usage(parent).free < total + 100_000_000:
        raise RuntimeError('Not enough space for the private Jarvis model copy')
    report('Preparing the private Jarvis model from existing local files…')
    from installer_progress import Progress
    copied_bytes = 0
    with Progress('Preparing private model') as progress, tempfile.TemporaryDirectory(prefix='.models-', dir=parent) as temporary:
        stage = Path(temporary) / 'models'
        stage.mkdir(mode=0o700)
        for index, (name, (expected_digest, size)) in enumerate(files.items(), 1):
            old, new = source / name, stage / name
            if regular_path(old).st_size != size:
                raise ValueError('Source model size changed')
            new.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            digest = hashlib.sha256()
            with old.open('rb') as read, new.open('xb') as write:
                new.chmod(0o600)
                for chunk in iter(lambda: read.read(1024 * 1024), b''):
                    digest.update(chunk)
                    write.write(chunk)
                    copied_bytes += len(chunk)
                    progress.fraction(copied_bytes, total)
                write.flush()
                os.fsync(write.fileno())
            if new.stat().st_size != size or digest.hexdigest() != expected_digest:
                raise ValueError('Source model hash changed; incomplete private copy discarded')
            report(f'Private model files verified: {index}/{len(files)}')
        if destination.exists():
            raise RuntimeError('Private model destination changed during preparation')
        stage.rename(destination)


def render_unit(uid, gid, home, binary):
    from prepare_core_isolation import unit_string
    root = private_root(home)
    return (f'[Unit]\nDescription=Jarvis private local model\n'
            f'After=user@{uid}.service\nBindsTo=user@{uid}.service\n'
            f'PartOf=jarvis-v4-{uid}-core.service\n'
            '[Service]\nType=exec\n'
            f'User={uid}\nGroup={gid}\nSlice=system.slice\n'
            'NoNewPrivileges=yes\nCapabilityBoundingSet=\nAmbientCapabilities=\n'
            'UMask=0077\nRestart=no\nTimeoutStopSec=20\n'
            f'Environment={unit_string("HOME=" + str(root))}\n'
            f'Environment={unit_string("OLLAMA_MODELS=" + str(root / "models"))}\n'
            f'Environment=OLLAMA_HOST=127.0.0.1:{PRIVATE_PORT} OLLAMA_NO_CLOUD=1\n'
            f'ExecStart={unit_string(binary)} serve\n'
            'IPAddressDeny=any\nIPAddressAllow=127.0.0.1 ::1\nIPAccounting=yes\n')


def remove_private_model(home):
    """Remove only the verified private copy, never the general model store."""
    if os.getuid() <= 0:
        raise RuntimeError('Remove private model data as the desktop user, without sudo')
    destination = private_root(home) / 'models'
    if not destination.exists() and not destination.is_symlink():
        return
    if any(p.is_symlink() for p in (destination, *destination.parents)):
        raise ValueError('Private model path needs review')
    if not destination.is_dir() or destination.stat().st_uid != os.getuid():
        raise ValueError('Private model directory must belong to this user')
    files = model_files(destination)
    expected = set(files)
    observed = set()
    for path in destination.rglob('*'):
        if path.is_symlink() or path.stat().st_uid != os.getuid():
            raise ValueError('Private model data ownership needs review')
        if path.is_file():
            observed.add(path.relative_to(destination))
        elif not path.is_dir():
            raise ValueError('Unexpected private model data')
    if observed != expected:
        raise ValueError('Extra private model data must be reviewed before removal')
    for name, (digest, size) in files.items():
        path = destination / name
        if path.stat().st_size != size or digest_file(path) != digest:
            raise ValueError('Private model data changed; removal stopped')
    shutil.rmtree(destination)


def wait_model(report=print, timeout=60):
    deadline = time.monotonic() + timeout
    last_report = 0
    while time.monotonic() < deadline:
        try:
            from prepare_core_isolation import properties
            before = properties('--system', unit_name(), 'ActiveState', 'MainPID', 'User', 'DropInPaths')
            if (before.get('ActiveState') != 'active' or before.get('User') != str(os.getuid())
                    or before.get('DropInPaths') or not before.get('MainPID', '').isdigit()
                    or int(before['MainPID']) <= 0):
                raise RuntimeError('Private daemon identity is not active')
            inventory_digest(PRIVATE_PORT)
            after = properties('--system', unit_name(), 'ActiveState', 'MainPID', 'User', 'DropInPaths')
            if after != before:
                raise RuntimeError('Private daemon changed during readiness')
            return
        except (OSError, RuntimeError, ValueError, http.client.HTTPException):
            if time.monotonic() - last_report >= 10:
                report('Waiting for the private model service to report its model…')
                last_report = time.monotonic()
            time.sleep(.25)
    raise RuntimeError('Private model service did not become ready. No general-instance fallback was used.')


def require_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        try:
            connection.bind(('127.0.0.1', PRIVATE_PORT))
        except OSError:
            raise RuntimeError('The private Jarvis port is already in use. No existing listener was stopped or replaced.') from None
