#!/usr/bin/env python3
"""Offline private-Python bootstrap refusal, integrity and no-alias regressions."""
import contextlib
import hashlib
import io
import os
from pathlib import Path
import tarfile
import tempfile
from unittest.mock import Mock, patch

import python_bootstrap as bootstrap
import install_prerequisites as prerequisites

if os.getuid() == 0:
    raise SystemExit('Run bootstrap regressions without sudo')


def rejects(function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except (OSError, ValueError, RuntimeError):
        return
    raise AssertionError('Unsafe bootstrap accepted')


with tempfile.TemporaryDirectory() as folder:
    home = Path(folder)
    with patch.object(prerequisites, 'reviewed_python', side_effect=prerequisites.MissingPython('missing')), \
         patch.object(bootstrap, 'prepare') as prepare:
        rejects(prerequisites.check, home, [], False)
        assert not prepare.called  # A read-only check never downloads.
    with patch.object(prerequisites, 'reviewed_python', side_effect=RuntimeError('wrong existing Python')), \
         patch.object(bootstrap, 'prepare') as prepare:
        rejects(prerequisites.check, home, [], False, prepare=True)
        assert not prepare.called
    with patch.object(prerequisites, 'reviewed_python', side_effect=[prerequisites.MissingPython('missing'), Path('/reviewed/python')]), \
         patch.object(bootstrap, 'prepare') as prepare:
        assert prerequisites.check(home, [], False, prepare=True) == Path('/reviewed/python')
        prepare.assert_called_once_with(home, '3.11.16')

    payload = b'not an executable fixture'
    with patch.object(bootstrap.urllib.request, 'build_opener', return_value=Mock(
            open=Mock(return_value=contextlib.closing(io.BytesIO(payload))))):
        rejects(bootstrap.download, home / 'bad-download')
    with patch.object(bootstrap.urllib.request, 'build_opener', return_value=Mock(
            open=Mock(return_value=contextlib.closing(io.BytesIO(payload))))), \
         patch.object(bootstrap, 'UV_SHA256', hashlib.sha256(payload).hexdigest()):
        bootstrap.download(home / 'verified-download')
    rejects(bootstrap.SecureRedirect().redirect_request, None, None, 302, '', {}, 'http://invalid.test/')

    for kind in ('file', 'link', 'duplicate', 'oversized'):
        archive = home / (kind + '.tar.gz')
        with tarfile.open(archive, 'w:gz') as package:
            record = tarfile.TarInfo('uv-x86_64-unknown-linux-gnu/uv')
            record.size = len(payload)
            if kind == 'link':
                record.type, record.linkname = tarfile.SYMTYPE, '/unreviewed'
            if kind == 'oversized':
                record.size = 129 * 1024 * 1024
                record.type = tarfile.SYMTYPE
            package.addfile(record, io.BytesIO(payload) if kind in {'file', 'duplicate'} else None)
            if kind == 'duplicate':
                package.addfile(record, io.BytesIO(payload))
            # Other paths are never extracted.
            extra = tarfile.TarInfo('../../outside')
            package.addfile(extra, io.BytesIO())
        target = home / ('uv-' + kind)
        if kind == 'file':
            bootstrap.extract_uv(archive, target)
            assert target.read_bytes() == payload and target.stat().st_mode & 0o777 == 0o700
        else:
            rejects(bootstrap.extract_uv, archive, target)
        assert not (home.parent / 'outside').exists()

with tempfile.TemporaryDirectory() as folder:
    home = Path(folder)
    interpreter = home / '.local/share/jarvis/python/cpython-3.11.16-linux-x86_64-gnu/bin/python3.11'
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if 'python' in command and 'install' in command:
            assert command[-2:] == ['--no-bin', 'cpython@3.11.16']
            assert command[1:3] == ['--no-config', '--no-progress']
            assert kwargs['env']['UV_PYTHON_INSTALL_DIR'] == str(home / '.local/share/jarvis/python')
            assert 'UV_PYTHON_BIN_DIR' not in kwargs['env']
            interpreter.parent.mkdir(parents=True)
            interpreter.write_text('fixture')
            return Mock(returncode=0)
        assert command == [str(interpreter), '-I', '-c', 'import platform; print(platform.python_version())']
        return Mock(stdout='3.11.16\n')

    with patch.object(Path, 'home', return_value=home), \
         patch.object(bootstrap.platform, 'system', return_value='Linux'), \
         patch.object(bootstrap.platform, 'machine', return_value='x86_64'), \
         patch.object(bootstrap, 'download'), \
         patch.object(bootstrap, 'extract_uv'), \
         patch.object(bootstrap.subprocess, 'run', side_effect=run), \
         patch.dict(os.environ, {'UV_PYTHON_BIN_DIR': '/must-not-use'}):
        assert bootstrap.prepare(home, '3.11.16', lambda _: None) == interpreter
        rejects(bootstrap.prepare, home, '3.11.16', lambda _: None)
        rejects(bootstrap.prepare, home, '3.12.0', lambda _: None)
    assert len(calls) == 2 and not (home / '.local/bin').exists()
    assert not list((home / '.local/state/jarvis/python-bootstrap').iterdir())

with tempfile.TemporaryDirectory() as folder:
    home = Path(folder)
    (home / 'outside').mkdir()
    (home / 'link').symlink_to(home / 'outside')
    rejects(bootstrap.private_directory, home / 'link/child', home)
    shared = home / 'shared'
    shared.mkdir(mode=0o755)
    rejects(bootstrap.private_directory, shared, home)

with tempfile.TemporaryDirectory() as folder:
    home = Path(folder)
    with patch.object(Path, 'home', return_value=home), \
         patch.object(bootstrap.platform, 'system', return_value='Linux'), \
         patch.object(bootstrap.platform, 'machine', return_value='x86_64'), \
         patch.object(bootstrap, 'download'), patch.object(bootstrap, 'extract_uv'), \
         patch.object(bootstrap.subprocess, 'run', side_effect=KeyboardInterrupt()):
        try:
            bootstrap.prepare(home, '3.11.16', lambda _: None)
        except KeyboardInterrupt:
            pass
        else:
            raise AssertionError('Cancelled bootstrap continued')
    assert not list((home / '.local/state/jarvis/python-bootstrap').iterdir())
    assert not (home / '.local/bin').exists()
print('PASS: read-only and wrong-existing-Python refusal, pinned download, bounded extraction, private exact interpreter and no system aliases')
