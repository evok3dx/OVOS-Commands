"""Private installation receipts for the frozen, hash-enforced V4 wheel path.

Receipts record installation provenance, not rehashing every installed file.
"""
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import re
import stat
import sys

NAME='.jarvis-runtime-install.json'
FIRST_PARTY={'ovos-skill-jarvis-dispatcher','ovos-skill-jarvis-media','jarvis-file-search-skill'}


def document(inventory_path,lock_path,packages):
    expected=json.loads(inventory_path.read_text())['packages']
    if packages!=expected:raise ValueError('Receipt package inventory differs from frozen runtime')
    return {'schema_version':1,'policy':'hash-enforced-wheels-v1',
            'inventory_sha256':hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
            'lock_sha256':hashlib.sha256(lock_path.read_bytes()).hexdigest(),'installed_packages':expected}


def matches(venv,inventory_path,lock_path,installed=None):
    path=venv/NAME
    try:
        if any(p.is_symlink() for p in (path,*path.parents)):return False
        info=path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode & 0o077 or info.st_size>65536:return False
        inventory=json.loads(inventory_path.read_text())
        expected=inventory['packages']
        if (inventory.get('python_full_version',platform.python_version())!=platform.python_version()
                or inventory.get('platform','linux-x86_64')!=sys.platform+'-'+platform.machine()):return False
        if json.loads(path.read_text())!=document(inventory_path,lock_path,expected):return False
        if installed is None:
            installed={re.sub(r'[-_.]+','-',d.metadata['Name']).lower():d.version for d in metadata.distributions()}
        installed=dict(installed)
        for name in FIRST_PARTY:installed.pop(name,None)
        for name in ('pip','setuptools'):
            if name not in expected:installed.pop(name,None)
        return installed==expected
    except (OSError,ValueError,KeyError,TypeError):return False


if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Use the reviewed inventory and lock paths')
    raise SystemExit(0 if matches(Path(sys.prefix),Path(sys.argv[1]),Path(sys.argv[2])) else 1)
