#!/usr/bin/env python3
"""Read-only runtime and native-authorisation checks before deployment."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def expected_python():
    return json.loads((ROOT / 'voice/runtime-linux-x86_64-py311.json').read_text())['python_full_version']


def python_version(executable):
    result = subprocess.run([str(executable), '-I', '-c',
                             'import platform; print(platform.python_version())'],
                            capture_output=True, text=True, timeout=15, check=True)
    return result.stdout.strip()


def reviewed_python(home, ovos_python=None):
    expected = expected_python()
    ovos = Path(ovos_python or home / '.venvs/ovos/bin/python')
    if ovos.exists():
        if python_version(ovos) != expected:
            raise RuntimeError(f'The reviewed OVOS runtime requires CPython {expected}; prepare that interpreter before installing. System Python must stay unchanged.')
        return ovos
    candidates = [Path('/usr/bin/python3.11'), Path('/usr/local/bin/python3.11')]
    candidates.extend(sorted((home / '.local/share/jarvis/python').glob(
        f'cpython-{expected}-linux-x86_64-gnu/bin/python3.11')))
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            if python_version(candidate) == expected:
                return candidate
    raise RuntimeError(f'Prepare CPython {expected} before Jarvis setup. See README prerequisites; do not replace system Python.')


def isolation_support():
    """The native grant needs JS rules, not a broad legacy PKLA grant."""
    result = subprocess.run(['/usr/bin/pkaction', '--version'], capture_output=True,
                            text=True, timeout=10, check=True)
    match = re.fullmatch(r'pkaction version (\d+)(?:\.(\d+))?\s*', result.stdout)
    if not match or (int(match[1]), int(match[2] or 0)) < (0, 106):
        raise RuntimeError('Native isolation needs Polkit JavaScript rules. Mint 21.3 / Polkit 0.105 is unsupported; upgrade to Mint 22.x. No isolation downgrade was made.')
    directory = Path('/etc/polkit-1/rules.d')
    if not directory.is_dir() or directory.is_symlink():
        raise RuntimeError('The Polkit rules directory is unavailable; review OS authorisation support before isolation setup. No native files changed.')


def check(home, arguments, isolated):
    executable = None
    if '--ovos-python' in arguments:
        index = arguments.index('--ovos-python')
        if index + 1 >= len(arguments):
            raise ValueError('--ovos-python needs a path')
        executable = arguments[index + 1]
    if isolated:
        isolation_support()
    return reviewed_python(home, executable or os.environ.get('OVOS_PYTHON'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isolation', action='store_true')
    args = parser.parse_args()
    try:
        print('Reviewed Python:', check(Path.home(), [], args.isolation))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, str(error) + '\n')
