#!/usr/bin/env python3
"""Recover pinned upstream wheels and build a separately validated candidate.

Never promote repository locks, install on a laptop, or execute as root.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from email.parser import BytesParser
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[1]
HOSTS = {'pypi.org', 'files.pythonhosted.org', 'github.com', 'codeload.github.com',
         'release-assets.githubusercontent.com', 'objects.githubusercontent.com',
         'archive.ubuntu.com'}


def checked_url(url):
    parts = urllib.parse.urlsplit(url)
    if (parts.scheme != 'https' or parts.hostname not in HOSTS
            or parts.username or parts.password or parts.port not in (None, 443)
            or parts.fragment):
        raise ValueError('Unreviewed artifact transport')
    return url


class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, checked_url(newurl))


def reply(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), Redirect())
    return opener.open(checked_url(url), timeout=90)


def metadata(url):
    with reply(url) as source:
        data = source.read(8 * 1024**2 + 1)
    if len(data) > 8 * 1024**2:
        raise ValueError('Metadata bounds exceeded')
    return json.loads(data)


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        while data := stream.read(1024**2):
            result.update(data)
    return result.hexdigest()


def fetch(url, expected, target):
    if not re.fullmatch(r'[a-f0-9]{64}', expected):
        raise ValueError('Missing reviewed source hash')
    if target.exists() or target.is_symlink():
        raise ValueError('Recovery never overwrites existing inputs')
    temporary = target.with_name(target.name + '.partial')
    count = 0
    try:
        with reply(url) as stream, temporary.open('xb') as output:
            while data := stream.read(1024**2):
                count += len(data)
                if count > 1024**3:
                    raise ValueError('Artifact bounds exceeded')
                output.write(data)
        if digest(temporary) != expected:
            raise ValueError('Reviewed artifact bytes changed')
        temporary.rename(target)
    finally:
        temporary.unlink(missing_ok=True)


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def environment(work):
    # Build backends receive no action tokens, user config or inherited proxies.
    return {'PATH': os.environ['PATH'], 'LANG': 'C.UTF-8',
            'TMPDIR': str(work / 'temporary'), 'SOURCE_DATE_EPOCH': '315532800',
            'PYTHONNOUSERSITE': '1', 'PIP_CONFIG_FILE': os.devnull,
            'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'}


def rebuild(output):
    if (os.getuid() == 0 or os.geteuid() != os.getuid()
            or platform.python_version() != '3.11.16'
            or platform.machine() != 'x86_64' or sys.platform != 'linux'):
        raise RuntimeError('Use ordinary-user Linux x86_64 Python 3.11.16')
    output = output.absolute()
    if output.exists() or any(path.is_symlink() for path in (output, *output.parents)):
        raise RuntimeError('Choose a new regular output beside user-owned staging')
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.parent.stat().st_uid != os.getuid():
        raise RuntimeError('Output parent must belong to the build user')
    output.mkdir(mode=0o700)
    for name in ('wheels', 'sources', 'tools', 'temporary', 'candidate', 'proof'):
        (output / name).mkdir(mode=0o700)
    canonical = json.loads((ROOT / 'voice/runtime-wheels-linux-x86_64-py311.artifacts.json').read_text())['packages']
    inputs = json.loads((ROOT / 'voice/runtime-rebuild-inputs.json').read_text())
    sources = inputs['sources']
    compat = json.loads((ROOT / 'compatibility.json').read_text())
    downstream = 'ovos-ww-plugin-openwakeword'
    source_lock = (ROOT / 'voice/runtime-sources-linux-x86_64-py311.txt').read_text()
    if len(canonical) != 296 or len(sources) != 9:
        raise RuntimeError('Unexpected reviewed closure')
    for record in sources.values():
        if record['sha256'] not in source_lock or Path(record['filename']).name != record['filename']:
            raise RuntimeError('Rebuild source differs from reviewed source lock')

    def recover(item):
        name, record = item
        if name in sources or name == downstream:
            return
        if name == 'en-core-web-sm':
            url = compat['ovos']['tts']['spacy_model_url']
        else:
            values = metadata(f"https://pypi.org/pypi/{name}/{record['version']}/json")['urls']
            exact = [v for v in values if v['filename'] == record['file']
                     and v['digests']['sha256'] == record['sha256']]
            if len(exact) != 1:
                raise RuntimeError('Exact reviewed upstream wheel unavailable: ' + name)
            url = exact[0]['url']
        fetch(url, record['sha256'], output / 'wheels' / record['file'])

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(recover, canonical.items()))
    print('286 exact upstream wheels recovered and hash checked.', flush=True)
    for record in sources.values():
        fetch(record['url'], record['sha256'], output / 'sources' / record['filename'])
    tools_lock = ROOT / 'voice/runtime-build-tools.txt'
    pins = re.split(r'\n(?=[a-z])', tools_lock.read_text())
    for pin in pins:
        match = re.search(r'(?m)^([a-z-]+)==([^\s]+)', pin)
        if not match:
            continue
        name, version = match.groups()
        allowed = set(re.findall(r'--hash=sha256:([a-f0-9]{64})', pin))
        wheels = [v for v in metadata(f'https://pypi.org/pypi/{name}/{version}/json')['urls']
                  if v['filename'].endswith('-py3-none-any.whl') and v['digests']['sha256'] in allowed]
        if len(wheels) != 1:
            raise RuntimeError('Hashed build tool unavailable')
        record = wheels[0]
        fetch(record['url'], record['digests']['sha256'], output / 'tools' / record['filename'])
    env = environment(output)
    build_env = output / 'build-venv'
    venv.EnvBuilder(with_pip=True).create(build_env)
    python = str(build_env / 'bin/python')
    subprocess.run([python, '-I', '-m', 'pip', '--isolated', 'install', '--no-index',
                    '--no-deps', '--require-hashes', '--find-links', str(output / 'tools'),
                    '-r', str(tools_lock)], check=True, env=env)
    headers = inputs['alsa_headers']
    header_package = output / 'sources' / headers['filename']
    fetch(headers['url'], headers['sha256'], header_package)
    subprocess.run(['dpkg-deb', '-x', str(header_package), str(output / 'alsa')], check=True, env=env)
    # The headers package's relative development link points at a library that
    # remains an OS package. Replace only that private link with the fixed ABI
    # library, rather than installing development files as administrator.
    native = next((path for path in (Path('/usr/lib/x86_64-linux-gnu/libasound.so.2'),
                                    Path('/lib/x86_64-linux-gnu/libasound.so.2'))
                   if path.is_file()), None)
    if native is None:
        raise RuntimeError('Install the native ALSA runtime OS package first')
    link = output / 'alsa/usr/lib/x86_64-linux-gnu/libasound.so'
    if not link.is_symlink():
        raise RuntimeError('Unexpected reviewed ALSA development link')
    link.unlink()
    link.symlink_to(native.resolve())
    env['CPATH'] = str(output / 'alsa/usr/include')
    env['LIBRARY_PATH'] = str(output / 'alsa/usr/lib/x86_64-linux-gnu')
    wheel_command = [python, '-I', '-m', 'pip', '--isolated', 'wheel', '--no-index',
                     '--no-deps', '--no-build-isolation', '--no-cache-dir',
                     '--wheel-dir', str(output / 'wheels')]
    for name, record in sources.items():
        subprocess.run(wheel_command + [str(output / 'sources' / record['filename'])], check=True, env=env)
        print('Built reviewed source:', name, flush=True)
    patch_source = ROOT / 'extras/ovos-ww-plugin-openwakeword-onnx'
    provenance = json.loads((patch_source / 'PROVENANCE.json').read_text())
    for file, expected in provenance['source_files_sha256'].items():
        if digest(patch_source / file) != expected:
            raise RuntimeError('Downstream wake plugin source changed')
    patch_copy = output / 'sources/onnx-wake'
    shutil.copytree(patch_source, patch_copy)
    subprocess.run(wheel_command + [str(patch_copy)], check=True, env=env)
    dep = module('rebuild_dependencies', 'scripts/dependency-lock.py')
    candidate_lock = output / 'candidate/runtime.txt'
    inventory = ROOT / 'voice/runtime-linux-x86_64-py311.json'
    dep.lock(output / 'wheels', inventory, candidate_lock)
    records = dep.wheel_records(output / 'wheels')
    if any(records[name]['requires'] != canonical[name]['requires'] for name in records):
        raise RuntimeError('Rebuilt dependency metadata changed; stop for review')
    changes = {name: {'previous': canonical[name]['sha256'], 'rebuilt': record['sha256']}
               for name, record in records.items() if record['sha256'] != canonical[name]['sha256']}
    if set(changes) - set(sources) - {downstream}:
        raise RuntimeError('Indexed wheel identities changed')
    dep.private_write(output / 'proof/hash-differences.json', json.dumps(changes, indent=2) + '\n')
    probe = module('rebuild_probe', 'scripts/probe-offline-runtime.py')
    probe.run_probe(output / 'wheels', inventory, candidate_lock, output / 'proof/offline-install.json')
    home = output / 'synthetic-home'
    target = home / '.local/state/jarvis/stage.rebuild/ovos-venv'
    target.parent.mkdir(parents=True, mode=0o700)
    venv.EnvBuilder(with_pip=True).create(target)
    probe.run_probe(output / 'wheels', inventory, candidate_lock,
                    output / 'proof/staged-install.json', target, home)
    plugins = output / 'candidate/plugins'
    plugins.mkdir(mode=0o700)
    for source in (ROOT, ROOT / 'plugins/ovos-skill-jarvis-media', ROOT / 'plugins/jarvis-file-search'):
        # Copy only reviewed build inputs; no Git credentials, diagnostic
        # snapshots, dependency wheelhouse or runner environment enter a wheel.
        copied = output / 'sources' / ('first-party-' + source.name)
        copied.mkdir(mode=0o700)
        for name in ('pyproject.toml', 'README.md', 'LICENSE'):
            path = source / name
            if path.is_file():
                shutil.copyfile(path, copied / name)
        for name in ('ovos_skill_jarvis_dispatcher', 'ovos_skill_jarvis_media', 'jarvis_file_search'):
            path = source / name
            if path.is_dir():
                shutil.copytree(path, copied / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        command = wheel_command.copy()
        command[command.index('--wheel-dir') + 1] = str(plugins)
        subprocess.run(command + [str(copied)], check=True, env=env)
    plugin_records = dep.wheel_records(plugins)
    if set(plugin_records) != dep.LOCAL:
        raise RuntimeError('First-party plugin inventory changed')
    plugin_lock = output / 'candidate/plugins.txt'
    dep.private_write(plugin_lock, dep.lock_text(plugin_records, []))
    subprocess.run([str(target / 'bin/python'), '-I', '-m', 'pip', '--isolated',
                    'install', '--no-index', '--no-deps', '--require-hashes',
                    '--find-links', str(plugins), '-r', str(plugin_lock)], check=True, env=env)
    subprocess.run([str(target / 'bin/python'), '-I', '-c',
                    'import ovos_skill_jarvis_dispatcher,ovos_skill_jarvis_media,jarvis_file_search; '
                    'import numpy,onnxruntime,faster_whisper; '
                    'from ovos_config import Configuration; '
                    'from ovos_workshop.skill_launcher import SkillContainer; '
                    'assert callable(Configuration.filter_and_merge); '
                    'assert callable(Configuration.load_all_configs); '
                    'assert callable(SkillContainer.run); '
                    'assert numpy.__version__=="2.4.6"; '
                    'print("Three first-party plugins, NumPy 2, inference imports and overlay APIs verified.")'],
                   check=True, env=env)
    dep.private_write(output / 'proof/plugins.json', json.dumps({
        'status': 'three plugin builds, hash-enforced staged installs and imports passed',
        'packages': plugin_records, 'live_desktop_tested': False,
    }, indent=2) + '\n')
    models = json.loads((ROOT / 'voice/model-identities.json').read_text())['wake_artifacts']
    raw = subprocess.check_output([str(target / 'bin/python'), '-I', '-c',
                                   'import importlib.util;print(next(iter(importlib.util.find_spec("openwakeword").submodule_search_locations)))'],
                                  text=True, env=env)
    resource = Path(raw.strip()) / 'resources/models'
    if target not in resource.parents:
        raise RuntimeError('Wake test resource path escaped the disposable stage')
    resource.mkdir(parents=True, exist_ok=True)
    for record in models:
        if record['name'].endswith('.onnx'):
            model = resource / record['name']
            if model.exists():
                if digest(model) != record['sha256']:
                    raise RuntimeError('Unexpected packaged wake model')
            else:
                fetch(record['url'], record['sha256'], model)
            if model.stat().st_size != record['bytes']:
                raise RuntimeError('Wake test model bounds changed')
    subprocess.run([str(target / 'bin/python'), '-I', '-c',
                    'import socket,sys,numpy as np; '
                    'from unittest.mock import patch; '
                    'with_guard=patch.object(socket.socket,"connect",side_effect=AssertionError("Network connection forbidden")); '
                    'with_guard.start(); '
                    'from ovos_ww_plugin_openwakeword import OwwHotwordPlugin; '
                    'wake=OwwHotwordPlugin("hey jarvis",{"inference_framework":"onnx","models":[sys.argv[1]]}); '
                    'frame=np.zeros(1280,dtype=np.int16).tobytes(); '
                    '[(wake.update(frame),None) for _ in range(50)]; '
                    'assert not wake.found_wake_word(); '
                    'assert not any(n.startswith("tflite_runtime") for n in sys.modules); '
                    'print("Real ONNX wake inference passed on 50 silent frames with network connects forbidden.")',
                    str(resource / 'hey_jarvis_v0.1.onnx')], check=True, env=env)
    dep.private_write(output / 'proof/wake-inference.json', json.dumps({
        'status': 'real ONNX silent-frame inference passed', 'numpy': '2.4.6',
        'plugin': '0.4.5a2+jarvis.1', 'silent_frames': 50,
        'network_connect_forbidden': True, 'tflite_not_imported': True,
        'microphone_or_positive_recognition_tested': False,
    }, indent=2) + '\n')
    licensing = {}
    for name, record in records.items():
        with zipfile.ZipFile(output / 'wheels' / record['file']) as wheel:
            entry = next(path for path in wheel.namelist()
                         if path.endswith('.dist-info/METADATA') and len(Path(path).parts) == 2)
            info = BytesParser().parsebytes(wheel.read(entry))
            licensing[name] = {'version': record['version'],
                               'declared_license': info.get('License-Expression') or info.get('License') or '',
                               'license_classifiers': [v for v in info.get_all('Classifier', []) if v.startswith('License ::')],
                               'packaged_notices': [v for v in wheel.namelist()
                                                   if re.search(r'(?:^|/)(?:licenses?|copying|notice)(?:[./_-]|$)', v, re.I)]}
    dep.private_write(output / 'proof/third-party-licenses.json', json.dumps({
        'status': 'declared licenses and packaged notices collected; redistribution review still required',
        'packages': licensing,
    }, indent=2) + '\n')
    bundle = module('rebuild_bundle', 'scripts/runtime_bundle.py')
    bundle.build(output / 'wheels', inventory, candidate_lock,
                 candidate_lock.with_suffix('.artifacts.json'),
                 output / 'candidate/jarvis-runtime-linux-x86_64-py311.zip',
                 output / 'candidate/runtime-bundle.json')
    dep.private_write(output / 'proof/rebuild.json', json.dumps({
        'schema_version': 1, 'status': 'candidate byte verification and offline staging passed',
        'package_count': len(records), 'metadata_exceptions': [],
        'python_full_version': platform.python_version(),
        'source_build_count': len(sources) + 1, 'hash_changes_require_review': sorted(changes),
        'locks_promoted': False, 'live_environment_modified': False,
        'live_isolation_verified': False,
        'inventory_sha256': digest(inventory), 'build_tools_sha256': digest(tools_lock),
    }, indent=2) + '\n')
    print('Complete bundle verified; repository locks unchanged; live gates remain.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rebuild(args.output)
