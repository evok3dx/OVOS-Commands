"""Readable local-time names with private, exclusive directory creation."""
from datetime import datetime
import os
from pathlib import Path
import re


def candidates(root, label, stamp=None):
    root = Path(root)
    if not re.fullmatch(r'Jarvis-[A-Za-z-]+', label):
        raise ValueError('Invalid report label')
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('Report directory must not use symbolic links')
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not root.is_dir() or root.stat().st_uid != os.getuid():
        raise ValueError('Report directory must be owned by this user')
    stamp = stamp or datetime.now()
    name = label + '-' + stamp.strftime('%Y-%m-%d_%H-%M-%S')
    for index in range(100):
        yield root / (name + (f'-{index + 1:02d}' if index else ''))


def next_path(root, label, stamp=None):
    for path in candidates(root, label, stamp):
        if not path.exists() and not path.is_symlink():
            return path
    raise RuntimeError('Could not allocate a new report name')


def new_directory(root, label, stamp=None):
    for path in candidates(root, label, stamp):
        try:
            path.mkdir(mode=0o700)
        except FileExistsError:
            continue
        return path
    raise RuntimeError('Could not allocate a new report directory')
