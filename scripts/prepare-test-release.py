#!/usr/bin/env python3
"""Prepare only the reviewed V4 test assets from the exact retained build.

Runs without publication credentials. Refuses stale first-party wheel content.
"""
import argparse
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import shutil
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / 'compatibility.json').read_text())['release_version']
RUNTIME_SHA = '03cbba7effa9046d9ce7a63b26d9a0b886eebf4f58f445dda2ae37af07e8c288'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def prepare(retained, output, plugin_directory=None):
    if os.getuid() == 0:
        raise RuntimeError('Prepare releases as an ordinary user')
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    candidate = retained / 'candidate'
    for name, local in {
        'runtime-bundle.json': 'voice/runtime-bundle.json',
        'runtime.txt': 'voice/runtime-wheels-linux-x86_64-py311.txt',
        'runtime.artifacts.json': 'voice/runtime-wheels-linux-x86_64-py311.artifacts.json',
    }.items():
        if (candidate / name).read_bytes() != (ROOT / local).read_bytes():
            raise ValueError('Retained policy differs: ' + name)
    policy = json.loads((ROOT / 'voice/runtime-bundle.json').read_text())
    archive = candidate / policy['archive_name']
    if (policy['archive_sha256'] != RUNTIME_SHA or digest(archive) != RUNTIME_SHA
            or archive.stat().st_size != policy['archive_bytes']):
        raise ValueError('Exact verified runtime archive required')
    assets = [archive, ROOT / 'dist' / f'ovos-commands-{VERSION}.tar.gz',
              ROOT / 'dist' / f'ovos-commands-{VERSION}.tar.gz.sha256']
    proof = json.loads((retained / 'proof/plugins.json').read_text()) if plugin_directory is None else None
    projects = {
        'ovos-skill-jarvis-dispatcher': (ROOT, 'ovos_skill_jarvis_dispatcher'),
        'ovos-skill-jarvis-media': (ROOT / 'plugins/ovos-skill-jarvis-media', 'ovos_skill_jarvis_media'),
        'jarvis-file-search-skill': (ROOT / 'plugins/jarvis-file-search', 'jarvis_file_search'),
    }
    if proof is not None and set(proof['packages']) != set(projects):
        raise ValueError('Unexpected first-party plugin inventory')
    for name, (project, package) in projects.items():
        metadata = tomllib.loads((project / 'pyproject.toml').read_text())['project']
        if plugin_directory is None:
            record = proof['packages'][name]
            wheel = candidate / 'plugins' / record['file']
        else:
            filename = name.replace('-', '_') + '-' + metadata['version'] + '-py3-none-any.whl'
            wheel = plugin_directory / filename
            record = {'file': filename, 'version': metadata['version'], 'sha256': digest(wheel)}
        if wheel.name != record['file'] or digest(wheel) != record['sha256']:
            raise ValueError('Plugin hash differs: ' + name)
        metadata = tomllib.loads((project / 'pyproject.toml').read_text())['project']
        with zipfile.ZipFile(wheel) as packaged:
            files = packaged.namelist()
            if len(set(files)) != len(files):
                raise ValueError('Duplicate wheel entry')
            meta_names = [n for n in files if n.endswith('.dist-info/METADATA')]
            if len(meta_names) != 1:
                raise ValueError('Unexpected wheel metadata')
            meta = BytesParser().parsebytes(packaged.read(meta_names[0]))
            if (meta['Name'] != metadata['name'] or meta['Version'] != metadata['version']
                    or record['version'] != metadata['version']):
                raise ValueError('Plugin version differs: ' + name)
            source_files = {p.relative_to(project).as_posix(): p for p in
                            (project / package).rglob('*') if p.is_file()
                            and '__pycache__' not in p.parts and p.suffix != '.pyc'}
            wheel_files = {n for n in files if n.startswith(package + '/') and not n.endswith('/')}
            if wheel_files != set(source_files):
                raise ValueError('Plugin source inventory differs: ' + name)
            for relative, source in source_files.items():
                if source.is_symlink() or packaged.read(relative) != source.read_bytes():
                    raise ValueError('Plugin source bytes differ: ' + name)
        assets.append(wheel)
    if plugin_directory is not None and {p.name for p in plugin_directory.iterdir()} != {p.name for p in assets if p.suffix == '.whl'}:
        raise ValueError('Unexpected freshly built plugin file')
    assets.extend([
        retained / 'proof/third-party-licenses.json',
        ROOT / 'extras/runtime-notices/espeak-ng-COPYING',
        ROOT / 'extras/runtime-notices/RUNTIME-NOTICES.md',
    ])
    for source in assets:
        if not source.is_file() or source.is_symlink() or (output / source.name).exists():
            raise ValueError('Unexpected release asset')
        shutil.copyfile(source, output / source.name)
        (output / source.name).chmod(0o644)
    (output / (archive.name + '.sha256')).write_text(RUNTIME_SHA + '  ' + archive.name + '\n')
    sums = ''.join(digest(p) + '  ' + p.name + '\n' for p in sorted(output.iterdir()))
    (output / 'SHA256SUMS').write_text(sums)
    print('Exact runtime, current plugin payloads and fixed public assets verified.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retained', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plugins', type=Path)
    args = parser.parse_args()
    prepare(args.retained, args.output, args.plugins)
