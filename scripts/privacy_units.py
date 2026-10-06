#!/usr/bin/env python3
"""Ordinary-user logging wrappers; native isolation relays keep precedence."""
import os
from pathlib import Path
import sys
import subprocess
from startup_settings import read_file, write_file
from prepare_core_isolation import unit_string

UNITS = {'ovos-core.service': 'core', 'ovos-listener.service': 'listener',
         'ovos-audio.service': 'audio', 'ovos-messagebus.service': 'bus'}
NAME = '10-jarvis-privacy.conf'
MARKER = '# Managed Jarvis application privacy\n'


def render(home, role):
    home = Path(home)
    return (MARKER + '[Service]\nExecStart=\n' +
            'ExecStart=' + unit_string(home / '.venvs/ovos/bin/python') + ' -I ' +
            unit_string(home / '.local/src/ovos-skill-jarvis-dispatcher/scripts/privacy_worker.py') +
            ' ' + role + '\n')


def install(home):
    if os.getuid() == 0:
        raise RuntimeError('Prepare user services without sudo')
    targets = [(Path(home) / '.config/systemd/user' / (unit + '.d') / NAME,
                render(home, role)) for unit, role in UNITS.items()]
    for path, text in targets:
        previous = read_file(path)
        if previous is not None and previous != text:
            raise ValueError('Existing privacy service data needs review')
    for path, text in targets:
        write_file(path, text, 0o600)


def verify(home):
    """Refuse a later override that bypasses the managed wrapper."""
    if os.getuid() == 0:
        raise RuntimeError('Inspect user services without sudo')
    from isolation_services import active
    isolated = active()
    for unit, role in UNITS.items():
        if isolated and role != 'bus':
            continue  # Actual native workers initialise privacy themselves.
        result = subprocess.run(['/usr/bin/systemctl', '--user', 'show', unit,
                                 '--property=ExecStart', '--value'],
                                capture_output=True, text=True, timeout=10, check=True)
        expected = str(Path(home) / '.local/src/ovos-skill-jarvis-dispatcher/scripts/privacy_worker.py') + ' ' + role
        if expected not in result.stdout:
            raise RuntimeError('A user service override bypasses Jarvis privacy; review it before startup')


if __name__ == '__main__':
    if len(sys.argv) not in (2, 3):
        raise SystemExit('Usage: privacy_units.py HOME [--verify]')
    if len(sys.argv) == 3:
        if sys.argv[2] != '--verify':raise SystemExit('Unknown privacy action')
        verify(Path(sys.argv[1]))
    else:
        install(Path(sys.argv[1]))
