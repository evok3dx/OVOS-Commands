#!/usr/bin/env python3
"""Remove only abandoned, marked Jarvis deployment staging directories.

Unmarked legacy folders, backups, recovery journals, models and shared caches
are never swept. The default is a read-only report.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import stat

MARKER = '.jarvis-stage.json'


def identity(pid):
    if type(pid) is not int or pid <= 0:
        raise ValueError('Invalid staging process')
    value = Path(f'/proc/{pid}/stat').read_text()
    return value.rsplit(')', 1)[1].split()[19]


def boot():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def check_path(path, home):
    base = home / '.local/state/jarvis'
    if (path.parent != base or not re.fullmatch(r'stage\.[0-9-]+\.[A-Za-z0-9]+', path.name)
            or any(p.is_symlink() for p in (path, *path.parents))):
        raise ValueError('Unexpected Jarvis staging path')
    info = path.stat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077):
        raise ValueError('Jarvis staging ownership or permissions need review')


def mark(path, home, pid):
    check_path(path, home)
    data = {'schema_version': 1, 'purpose': 'jarvis-deployment-stage',
            'uid': os.getuid(), 'pid': pid, 'process_start': identity(pid), 'boot': boot()}
    fd = os.open(path / MARKER, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(data, stream)


def abandoned(path, home):
    check_path(path, home)
    marker = path / MARKER
    info = marker.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077 or info.st_size > 1024):
        return False
    data = json.loads(marker.read_text())
    if (set(data) != {'schema_version', 'purpose', 'uid', 'pid', 'process_start', 'boot'}
            or data['schema_version'] != 1 or data['purpose'] != 'jarvis-deployment-stage'
            or data['uid'] != os.getuid() or type(data['pid']) is not int
            or not isinstance(data['process_start'], str) or not data['process_start'].isdigit()
            or not isinstance(data['boot'], str)
            or not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', data['boot'])):
        return False
    if data['boot'] == boot():
        try:
            if identity(data['pid']) == data['process_start']:
                return False
        except (FileNotFoundError, ProcessLookupError):
            pass
    device = path.stat().st_dev
    for child in path.rglob('*'):
        entry = child.lstat()
        if (entry.st_uid != os.getuid() or entry.st_dev != device
                or not (stat.S_ISREG(entry.st_mode) or stat.S_ISDIR(entry.st_mode)
                        or stat.S_ISLNK(entry.st_mode))):
            return False
    return True


def clean(home, apply=False):
    if os.getuid() == 0:
        raise RuntimeError('Review staging as the desktop user, without sudo')
    base = home / '.local/state/jarvis'
    if any(p.is_symlink() for p in (base, *base.parents)):
        raise ValueError('Jarvis state path must not use symbolic links')
    # An interrupted installation may need its stage. Do not infer otherwise
    # from its age, or silently discard the recovery guard.
    journal = base / 'isolation-install/current.json'
    if journal.exists() or journal.is_symlink():
        return []
    removed = []
    for path in sorted(base.glob('stage.*')):
        try:
            if not abandoned(path, home):
                continue
            if apply:
                if not shutil.rmtree.avoids_symlink_attacks:
                    raise RuntimeError('Safe directory removal is unavailable')
                shutil.rmtree(path)
            removed.append(path.name)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return removed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--mark', type=Path)
    parser.add_argument('--pid', type=int)
    args = parser.parse_args()
    if args.mark:
        if args.pid is None or args.apply:
            parser.error('Mark requires a process ID and cannot remove files')
        mark(args.mark, args.home, args.pid)
    else:
        names = clean(args.home, args.apply)
        print(('Removed' if args.apply else 'Removable') + f' abandoned marked staging folders: {len(names)}')
        print('\n'.join(names) if names else 'No eligible staging leftovers.')


if __name__ == '__main__':
    main()
