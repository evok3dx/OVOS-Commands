"""Prepare the exact private interpreter with a checksum-pinned uv download."""
import hashlib
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import tarfile
import tempfile
import time
import urllib.request

UV_VERSION = '0.12.3'
UV_ARCHIVE = 'uv-x86_64-unknown-linux-gnu.tar.gz'
UV_URL = f'https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/{UV_ARCHIVE}'
UV_SHA256 = '600cf9a742aca00d292673b16b5acffaa7b8c269a364ad0c2e79498dcb1fe101'
MAX_DOWNLOAD = 64 * 1024 * 1024


class SecureRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, url):
        if not url.startswith('https://'):
            raise RuntimeError('Python bootstrap requires HTTPS redirects')
        return super().redirect_request(request, response, code, message, headers, url)


def private_directory(path, home):
    if path != home and home not in path.parents:
        raise ValueError('Private Python preparation must stay inside this account home')
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError('Private Python paths must not contain symbolic links')
        if item == home:
            break
        if item.exists():
            info = item.stat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & stat.S_IWOTH:
                raise ValueError('Private Python directory ownership needs review')
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.stat().st_mode & 0o077:
        raise ValueError('Private Python preparation directory must have mode 700')


def download(path):
    deadline = time.monotonic() + 300
    opener = urllib.request.build_opener(SecureRedirect())
    request = urllib.request.Request(UV_URL, headers={'User-Agent': 'Jarvis-Python-Setup'})
    digest, total = hashlib.sha256(), 0
    with opener.open(request, timeout=30) as response, path.open('xb') as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_DOWNLOAD or time.monotonic() > deadline:
                raise RuntimeError('Python bootstrap download exceeded its limit')
            digest.update(chunk)
            output.write(chunk)
    if digest.hexdigest() != UV_SHA256:
        raise RuntimeError('Python bootstrap checksum mismatch; downloaded code was not executed')


def extract_uv(archive, destination):
    # Read just the reviewed binary; never extract archive paths or links.
    with tarfile.open(archive, 'r:gz') as package:
        matches = [item for item in package.getmembers()
                   if item.name == 'uv-x86_64-unknown-linux-gnu/uv']
        if len(matches) != 1 or not matches[0].isfile() or not 0 < matches[0].size <= 128 * 1024 * 1024:
            raise ValueError('Unexpected Python bootstrap binary')
        with package.extractfile(matches[0]) as source, destination.open('xb') as output:
            shutil.copyfileobj(source, output)
    destination.chmod(0o700)


def prepare(home, expected, report=print):
    if os.getuid() <= 0 or os.getuid() != os.geteuid() or home != Path.home():
        raise RuntimeError('Prepare Python as the normal desktop user, without sudo')
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise RuntimeError('Automatic private Python setup supports Linux x86_64 only')
    if expected != '3.11.16':
        raise RuntimeError('Review the Python bootstrap before changing the managed interpreter')
    state = home / '.local/state/jarvis/python-bootstrap'
    root = home / '.local/share/jarvis/python'
    private_directory(state, home)
    private_directory(root, home)
    interpreter = root / f'cpython-{expected}-linux-x86_64-gnu/bin/python3.11'
    if interpreter.exists() or interpreter.is_symlink():
        raise RuntimeError('Existing private interpreter needs review; it was not overwritten')
    report(f'Preparing private CPython {expected}; system Python stays unchanged…')
    with tempfile.TemporaryDirectory(prefix='prepare-', dir=state) as folder:
        temporary = Path(folder)
        archive, uv = temporary / UV_ARCHIVE, temporary / 'uv'
        download(archive)
        extract_uv(archive, uv)
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith('UV_') and key not in {'VIRTUAL_ENV', 'PYTHONHOME', 'PYTHONPATH'}}
        environment['UV_PYTHON_INSTALL_DIR'] = str(root)
        subprocess.run([str(uv), '--no-config', '--no-progress', 'python', 'install',
                        '--no-bin', f'cpython@{expected}'], env=environment, check=True, timeout=600)
    if not interpreter.is_file() or root not in interpreter.resolve().parents:
        raise RuntimeError('Private Python installation did not produce the reviewed interpreter')
    result = subprocess.run([str(interpreter), '-I', '-c',
                             'import platform; print(platform.python_version())'],
                            capture_output=True, text=True, check=True, timeout=15)
    if result.stdout.strip() != expected:
        raise RuntimeError('Prepared Python version differs from the reviewed runtime')
    report(f'Private CPython {expected} is ready.')
    return interpreter
