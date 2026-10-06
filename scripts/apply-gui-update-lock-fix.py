#!/usr/bin/env python3
"""Repair only reviewed 4.0.1/4.2.0 GUI update locks, as the desktop user."""
import argparse
import ast
from contextlib import ExitStack
from datetime import datetime
import fcntl
import hashlib
import os
from pathlib import Path
import stat
import tempfile

REVIEWED = {"772f2cf04961863de126f8e058733568b422ee5d69122f350dead5c2ccae2a4b":"7d6d34cb83798d900a38787754f754c933068d171fdcb090ca89303e96ec5b9f","b7e4578807a08b415471a4dbf2d9995bd6777518eeea204f058a52398110f707":"99cad525a8d3b507f84ba3cb69f6a23af85eda9b0cafc11c8e8a25678ed3277f"}
HELPER = "@contextlib.contextmanager\ndef update_lock():\n    \"\"\"Serialize GUI updates without holding the installer's service lock.\"\"\"\n    directory=Path.home()/'.local/state/jarvis-ui'\n    directory.mkdir(parents=True,exist_ok=True)\n    with (directory/'updates.lock').open('a') as lock:\n        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)\n        except BlockingIOError:\n            raise RuntimeError('Another Jarvis update is running. Please wait.')\n        try:yield\n        finally:fcntl.flock(lock,fcntl.LOCK_UN)\n\n\n"
BEFORE = "    if action=='install':\n        with operation_lock():\n            result="
AFTER = "    if action=='install':\n        with update_lock():\n            # Refuse a control action already in progress, then release its\n            # lock before starting the updater. The isolated coordinator uses\n            # that lock itself for Stop and recovery; its transaction journal\n            # prevents unsafe starts during installation.\n            with operation_lock():\n                pass\n            result="


def regular(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise RuntimeError('A source or lock path is a symbolic link; nothing changed.')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise RuntimeError('Source ownership or permissions need review; nothing changed.')
    return path.read_bytes(), info


def directory(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise RuntimeError('A backup or lock directory is a symbolic link; nothing changed.')
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise RuntimeError('Directory ownership or permissions need review; nothing changed.')


def reviewed(path):
    data, info = regular(path)
    identity = hashlib.sha256(data).hexdigest()
    if identity in REVIEWED.values():
        return data, info, None
    expected = REVIEWED.get(identity)
    if expected is None:
        raise RuntimeError('Installed updater is not an exact reviewed 4.0.1/4.2.0 file; nothing changed.')
    text = data.decode()
    anchor = 'def exclusive(function):'
    if text.count(BEFORE) != 1 or text.count(anchor) != 1:
        raise RuntimeError('Updater structure needs review; nothing changed.')
    result = text.replace(anchor, HELPER + anchor, 1).replace(BEFORE, AFTER, 1).encode()
    ast.parse(result, filename=str(path))
    if hashlib.sha256(result).hexdigest() != expected:
        raise RuntimeError('Patched updater checksum did not match; nothing changed.')
    return data, info, result


def repair(apply=False):
    if os.getuid() <= 0 or os.getuid() != os.geteuid():
        raise RuntimeError('Run as the desktop user, without sudo.')
    home = Path.home()
    target = home / '.local/src/ovos-skill-jarvis-dispatcher/scripts/control_runtime.py'
    original, info, result = reviewed(target)
    if result is None:
        print('GUI update lock correction is already installed. Reopen the Control Centre.')
        return
    if not apply:
        print('Exact reviewed updater found. Close the Control Centre, then use --apply.')
        return
    locks = home / '.local/state/jarvis-ui'
    directory(locks)
    with ExitStack() as stack:
        for name in ('updates.lock', 'controls.lock'):
            path = locks / name
            if any(p.is_symlink() for p in (path, *path.parents)):
                raise RuntimeError('Lock path needs review; nothing changed.')
            descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            handle = stack.enter_context(os.fdopen(descriptor, 'a'))
            regular(path)
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('A Jarvis update or control action is running. Wait for it to finish.')
        if regular(target)[0] != original:
            raise RuntimeError('Updater changed during review; nothing changed.')
        downloads = home / 'Downloads'
        directory(downloads)
        label = 'Jarvis-GUI-Update-Fix-' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        for number in range(1000):
            backup = downloads / (label + (('-' + str(number)) if number else ''))
            try:
                backup.mkdir(mode=0o700)
                break
            except FileExistsError:
                continue
        else:
            raise RuntimeError('Backup folder allocation failed; nothing changed.')
        saved = backup / 'control_runtime.py'
        with saved.open('xb') as output:
            os.chmod(saved, 0o600)
            output.write(original)
            output.flush()
            os.fsync(output.fileno())
        descriptor, temporary = tempfile.mkstemp(prefix='.gui-update-fix-', dir=target.parent)
        try:
            with os.fdopen(descriptor, 'wb') as output:
                output.write(result)
                output.flush()
                os.fsync(output.fileno())
            os.chmod(temporary, stat.S_IMODE(info.st_mode))
            if regular(target)[0] != original:
                raise RuntimeError('Updater changed before replacement; nothing changed.')
            os.replace(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)
        print('GUI update lock correction installed. Backup:', backup)
        print('Settings, services and isolation policy were not changed. Reopen the Control Centre.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    arguments = parser.parse_args()
    try:
        repair(arguments.apply)
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()

