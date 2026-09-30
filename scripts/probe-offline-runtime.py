#!/usr/bin/env python3
"""Verify a captured wheel closure and install it only in a disposable venv.

Supports only a disposable environment or the installer's unpublished stage.
No network fallback or direct live environment mutation.
Run with the captured Python 3.11 interpreter after building the wheelhouse.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import venv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec = importlib.util.spec_from_file_location('jarvis_dependency_lock', ROOT/'scripts/dependency-lock.py')
dependencies = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dependencies)


def prepare(wheelhouse, inventory, lock_path, directory):
    """Copy into private staging, then verify the actual bytes pip will use."""
    wheels = directory/'wheels'
    wheels.mkdir(mode=0o700)
    for source in wheelhouse.iterdir():
        if source.is_symlink() or not source.is_file() or source.suffix != '.whl':
            raise RuntimeError('Wheelhouse must contain only regular wheel files')
        shutil.copyfile(source, wheels/source.name)
    records = dependencies.wheel_records(wheels)
    exceptions = dependencies.verify_closure(records, inventory)
    text = dependencies.lock_text(records, exceptions)
    if lock_path.is_symlink() or lock_path.read_text() != text:
        raise RuntimeError('Lock differs from the verified wheel hashes and captured closure')
    staged_lock = directory/'runtime.txt'
    dependencies.private_write(staged_lock, text)
    return wheels, staged_lock, records, sorted(set(exceptions))


def clean_environment():
    environment = {key:value for key,value in os.environ.items()
                   if not key.startswith(('PIP_', 'UV_'))
                   and key not in {'PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'}}
    environment['PIP_CONFIG_FILE'] = os.devnull
    environment['PYTHONNOUSERSITE'] = '1'
    return environment


def run_probe(wheelhouse, inventory_path, lock_path, output, staged_target=None, home=None):
    inventory = json.loads(inventory_path.read_text())
    if (sys.version_info[:2] != (3,11) or sys.platform != 'linux'
            or platform.machine() != 'x86_64'
            or inventory.get('python') != '3.11'
            or inventory.get('platform') != 'linux-x86_64'
            or inventory.get('python_full_version', platform.python_version()) != platform.python_version()):
        raise RuntimeError('Use the captured Linux x86_64 Python 3.11 patch version')
    if output.exists() or output.is_symlink():
        raise RuntimeError('Output already exists; refusing overwrite')
    if staged_target is not None:
        # Only the installer's unpublished stage may be modified. An ordinary
        # live ~/.venvs/ovos target, symlink or arbitrary directory is refused.
        state = Path(home or Path.home())/'.local/state/jarvis'
        stage = staged_target.parent
        if (stage.parent != state or not stage.name.startswith('stage.')
                or staged_target.name != 'ovos-venv'
                or any(path.is_symlink() for path in (staged_target,*staged_target.parents))
                or staged_target.stat().st_uid != os.getuid()):
            raise RuntimeError('Only a regular user-owned Jarvis staging target is allowed')
        raw = subprocess.check_output([str(staged_target/'bin/python'),'-I','-c',
            "import sys,importlib.metadata as m,json; print(json.dumps({'prefix':sys.prefix,'packages':[d.metadata['Name'].lower() for d in m.distributions()]}))"],
            text=True,env=clean_environment())
        initial = json.loads(raw)
        if Path(initial['prefix']) != staged_target or set(initial['packages'])-{'pip','setuptools','wheel'}:
            raise RuntimeError('The staging environment must contain only bootstrap tools')
    with tempfile.TemporaryDirectory(prefix='jarvis-offline-probe-',dir=stage if staged_target else None) as temporary:
        directory = Path(temporary)
        wheels, staged_lock, records, exceptions = prepare(wheelhouse, inventory, lock_path, directory)
        target = staged_target or directory/'venv'
        if staged_target is None:venv.EnvBuilder(with_pip=True).create(target)
        interpreter = target/'bin/python'
        environment = clean_environment()
        subprocess.run([str(interpreter), '-I', '-m', 'pip', '--isolated',
                        '--disable-pip-version-check', 'install', '--no-index',
                        '--no-deps', '--only-binary=:all:', '--no-cache-dir',
                        '--require-hashes', '--find-links', str(wheels),
                        '-r', str(staged_lock)], check=True, env=environment)
        raw = subprocess.check_output([str(interpreter), '-I', '-c',
            "import importlib.metadata as m,json,re; print(json.dumps({re.sub(r'[-_.]+','-',d.metadata['Name']).lower():d.version for d in m.distributions()}))"],
            text=True, env=environment)
        installed = json.loads(raw)
        expected = {name:record['version'] for name,record in records.items()}
        # ensurepip is the local bootstrap, distinct from the captured runtime.
        bootstrap = {name:installed.pop(name) for name in ('pip','setuptools')
                     if name not in expected and name in installed}
        if installed != expected:
            raise RuntimeError('Installed package inventory differs from the captured runtime')
        subprocess.run([str(interpreter), '-I', str(ROOT/'scripts/validate-staged-ovos.py'),
                        str(inventory_path)], check=True, env=environment)
        if staged_target is not None:
            from runtime_provenance import NAME,document
            dependencies.private_write(target/NAME,json.dumps(document(inventory_path,lock_path,expected),indent=2)+'\n')
        dependencies.private_write(output, json.dumps({
            'schema_version':1, 'status':'isolated offline install passed; live acceptance required',
            'python_full_version':platform.python_version(), 'package_count':len(expected),
            'metadata_exceptions':exceptions, 'ensurepip_bootstrap':bootstrap,
            'installed_packages':expected, 'network_indexes_enabled':False,
            'live_environment_modified':False, 'model_inference_verified':False,
            'staged_target_modified':staged_target is not None,
        }, indent=2)+'\n')
    print('Offline wheel install and complete inventory parity passed.' +
          (' Unpublished stage validated; live environment untouched.' if staged_target else ' Disposable environment removed.'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--wheelhouse', type=Path, required=True)
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--staged-target',type=Path,
                        help='Installer-only empty ~/.local/state/jarvis/stage.*/ovos-venv')
    args = parser.parse_args()
    try:
        run_probe(args.wheelhouse, args.inventory, args.lock, args.output,args.staged_target)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
        # pip may print its own bounded diagnostics; never serialise exception
        # strings with paths/environment into a report intended for sharing.
        print('Offline candidate rejected. No live environment was modified.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
