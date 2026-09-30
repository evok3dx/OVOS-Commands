#!/usr/bin/env python3
"""Capture runtime pins and validate a fully hashed, offline wheel candidate.

This tool never modifies the live environment or promotes a candidate lock.
Run capture with the supported laptop's OVOS interpreter, not system Python.
"""
import argparse
import hashlib
import importlib.metadata
import json
import platform
import re
import sys
import zipfile
from email.parser import BytesParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = {'ovos-skill-jarvis-dispatcher','ovos-skill-jarvis-media','jarvis-file-search-skill'}

def normalise(name): return re.sub(r'[-_.]+','-',name).lower()

def validate_pin(name, version):
    if (not isinstance(name,str) or not isinstance(version,str)
            or not re.fullmatch(r'[a-z0-9-]+',name)
            or not re.fullmatch(r'[a-zA-Z0-9.!+_-]+',version)):
        raise RuntimeError('Invalid package pin; URLs, options and injected requirements are forbidden')

def private_write(path, text):
    # Refuse accidental overwrite and give candidates private permissions.
    import os
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as stream: stream.write(text)

def runtime_inventory():
    if sys.version_info[:2] != (3,11) or platform.machine() != 'x86_64' or sys.platform!='linux':
        raise RuntimeError('Capture requires the supported Linux x86_64 Python 3.11 OVOS interpreter')
    packages={}
    sources={}
    for dist in importlib.metadata.distributions():
        name=normalise(dist.metadata['Name'])
        if name in LOCAL: continue
        if name in packages: raise RuntimeError('Duplicate installed distribution: '+name)
        validate_pin(name,dist.version)
        packages[name]=dist.version
        raw=dist.read_text('direct_url.json')
        if raw:
            direct=json.loads(raw)
            # Never export URLs: local paths and credentials may appear there.
            source={'kind':'direct artifact','editable':bool(direct.get('dir_info',{}).get('editable'))}
            vcs=direct.get('vcs_info',{})
            commit=vcs.get('commit_id')
            if vcs: source['kind']='vcs'
            if isinstance(commit,str) and re.fullmatch(r'[a-fA-F0-9]{40,64}',commit):
                source['commit']=commit.lower()
            archive=direct.get('archive_info',{})
            digest=archive.get('hashes',{}).get('sha256')
            if not digest and isinstance(archive.get('hash'),str):
                digest=archive['hash'].removeprefix('sha256=')
            if isinstance(digest,str) and re.fullmatch(r'[a-fA-F0-9]{64}',digest):
                source['sha256']=digest.lower()
            source['identity_recorded']='commit' in source or 'sha256' in source
            sources[name]=source
    return {'schema_version':1,'status':'candidate; not release-approved',
            'python':'3.11','python_full_version':platform.python_version(),
            'platform':'linux-x86_64','packages':dict(sorted(packages.items())),
            'non_index_sources':dict(sorted(sources.items()))}

def capture(output):
    value=runtime_inventory()
    packages=value['packages']
    reviewed=json.loads((ROOT/'voice/reviewed-stack.json').read_text())['packages']
    for name,version in reviewed.items():
        if packages.get(normalise(name))!=version:
            raise RuntimeError('Capture differs from reviewed runtime: '+name)
    if 'yt-dlp' not in packages:
        raise RuntimeError('Install/capture the tested yt-dlp version before freezing')
    private_write(output,json.dumps(value,indent=2)+'\n')

def inputs(output, inventory=None):
    reviewed=json.loads((ROOT/'voice/reviewed-stack.json').read_text())
    captured=json.loads(inventory.read_text()) if inventory else {}
    for name,source in captured.get('non_index_sources',{}).items():
        if name not in {'phoonnx','en-core-web-sm'} or source.get('editable'):
            raise RuntimeError('Non-index source requires review before generating inputs: '+name)
    packages=(captured['packages'] if inventory else reviewed['packages'])
    policy=json.loads((ROOT/'compatibility.json').read_text())['ovos']
    tts=policy['tts']
    packages=dict(packages)
    if packages.get('ovos-ww-plugin-openwakeword') != policy['wakeword']['validated_version']:
        raise RuntimeError('Wake plugin differs from the reviewed candidate; retain the observed inventory separately')
    for name,version in packages.items(): validate_pin(name,version)
    packages.update({'openwakeword':policy['wakeword']['engine_version'],
                     'espeakng-loader':tts['espeakng_loader_version'],
                     'phonemizer-fork':tts['phonemizer_fork_version'],
                     'num2words':tts['num2words_version'],'spacy':tts['spacy_version']})
    lines=[f'{name}=={version}' for name,version in sorted(packages.items())
           if name not in {'phoonnx','en-core-web-sm','ovos-ww-plugin-openwakeword'}]
    # The reviewed downstream plugin is built from repository source with the
    # hashed build toolchain, then included in the complete wheel hash lock.
    # Never resolve its local version from an index or hide it in an upstream pin.
    lines.append('# Build the reviewed ONNX-only wake plugin separately from ovos.runtime_candidate.wake_plugin_source; verify its provenance and wheel hash.')
    lines += [f"phoonnx @ {tts['repository'].removesuffix('.git')}/archive/{tts['reference_commit']}.tar.gz#sha256={tts['archive_sha256']}",
              f"en-core-web-sm @ {tts['spacy_model_url']}#sha256={tts['spacy_model_sha256']}"]
    private_write(output,'\n'.join(lines)+'\n')

def wheel_records(directory):
    records={}
    for path in sorted(directory.iterdir()):
        if path.is_symlink() or not path.is_file() or path.suffix!='.whl':
            raise RuntimeError('Wheelhouse must contain only regular wheel files')
        with zipfile.ZipFile(path) as wheel:
            # Vendored libraries can carry nested dist-info (e.g. setuptools).
            # Only the wheel's top-level distribution metadata identifies it.
            names=[name for name in wheel.namelist()
                   if name.endswith('.dist-info/METADATA') and len(Path(name).parts)==2]
            if len(names)!=1: raise RuntimeError('Ambiguous wheel metadata')
            metadata=BytesParser().parsebytes(wheel.read(names[0]))
        name=normalise(metadata['Name']);version=metadata['Version']
        if name in records: raise RuntimeError('Duplicate wheel package: '+name)
        if not re.fullmatch(r'[a-z0-9-]+',name) or not re.fullmatch(r'[a-zA-Z0-9.!+_-]+',version):
            raise RuntimeError('Invalid wheel identity')
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''): digest.update(chunk)
        records[name]={'version':version,'file':path.name,
                       'sha256':digest.hexdigest(),
                       'requires':metadata.get_all('Requires-Dist',[])}
    if not records: raise RuntimeError('Empty wheelhouse')
    return records

def verify_closure(records, inventory):
    try:
        from packaging.requirements import Requirement
        from packaging.markers import default_environment
        from packaging.utils import parse_wheel_filename
    except ImportError as error:
        try:
            from pip._vendor.packaging.requirements import Requirement
            from pip._vendor.packaging.markers import default_environment
            from pip._vendor.packaging.utils import parse_wheel_filename
        except ImportError:
            raise RuntimeError('The reviewed packaging library or pip is needed for wheel verification') from error
    environment=default_environment()
    full_version=inventory.get('python_full_version','3.11.0')
    if not re.fullmatch(r'3\.11\.\d+',full_version):
        raise RuntimeError('Unsupported Python patch version')
    environment.update({'python_version':'3.11','python_full_version':full_version,
                        'sys_platform':'linux','platform_system':'Linux',
                        'platform_machine':'x86_64','os_name':'posix','extra':''})
    expected={normalise(k):v for k,v in inventory['packages'].items() if normalise(k) not in LOCAL}
    if expected != {k:v['version'] for k,v in records.items()}:
        raise RuntimeError('Wheel inventory differs from the complete captured runtime')
    reviewed=json.loads((ROOT/'voice/reviewed-stack.json').read_text())
    for name,version in reviewed['packages'].items():
        if expected.get(normalise(name))!=version: raise RuntimeError('Reviewed pin changed: '+name)
    exceptions=[]
    for name,record in records.items():
        filename_name,version,_,tags=parse_wheel_filename(record['file'])
        if normalise(filename_name)!=name: raise RuntimeError('Wheel filename/metadata name mismatch')
        if str(version)!=record['version']: raise RuntimeError('Wheel filename/metadata version mismatch')
        # Binary compatibility is also checked by pip in the isolated probe.
        if not any(tag.platform=='any' or ('x86_64' in tag.platform and ('linux' in tag.platform)) for tag in tags):
            raise RuntimeError('Unsupported wheel platform: '+name)
    # Propagate requested extras through transitive edges. Otherwise a marker
    # such as extra == 'socks' could hide a missing runtime dependency.
    queue=[(name,'') for name in records]
    visited=set()
    while queue:
        name,extra=queue.pop()
        if (name,extra) in visited: continue
        visited.add((name,extra))
        record=records[name]
        environment['extra']=extra
        for text in record['requires']:
            requirement=Requirement(text)
            if requirement.marker and not requirement.marker.evaluate(environment): continue
            target=normalise(requirement.name)
            if target not in records: raise RuntimeError('Missing transitive dependency: '+name+' -> '+target)
            queue.extend((target,item) for item in requirement.extras)
            if requirement.url: raise RuntimeError('Unreviewed direct dependency URL: '+name)
            # The inventory already selects exact reviewed versions, including
            # the OVOS alpha stack. Older host packaging rejects prereleases by
            # default; that resolver preference is not a version conflict here.
            # Explicit handling keeps every actual bound/exclusion enforced.
            if requirement.specifier and not requirement.specifier.contains(records[target]['version'],prereleases=True):
                raise RuntimeError('Dependency version conflict: '+name+' -> '+text)
    return exceptions

def lock_text(records, exceptions):
    lines=['# Candidate only. Isolated and live acceptance are required.']
    lines += ['# Reviewed metadata exception: '+item for item in sorted(set(exceptions))]
    lines += [f"{name}=={record['version']} --hash=sha256:{record['sha256']}" for name,record in sorted(records.items())]
    return '\n'.join(lines)+'\n'

def lock(wheelhouse, inventory_path, output):
    inventory=json.loads(inventory_path.read_text())
    if inventory.get('python')!='3.11' or inventory.get('platform')!='linux-x86_64':
        raise RuntimeError('Unsupported capture target')
    records=wheel_records(wheelhouse)
    exceptions=verify_closure(records,inventory)
    private_write(output,lock_text(records,exceptions))
    private_write(output.with_suffix('.artifacts.json'),json.dumps({'schema_version':1,'status':'candidate',
                  'metadata_exceptions':exceptions,'packages':records},indent=2)+'\n')
    print('Complete captured wheel closure verified; candidate lock created. No live installation performed.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    command=commands.add_parser('capture');command.add_argument('--output',type=Path,required=True)
    command=commands.add_parser('inputs');command.add_argument('--output',type=Path,required=True);command.add_argument('--inventory',type=Path)
    command=commands.add_parser('wheel-lock');command.add_argument('--wheelhouse',type=Path,required=True)
    command.add_argument('--inventory',type=Path,required=True);command.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='capture': capture(args.output)
    elif args.command=='inputs': inputs(args.output,args.inventory)
    else: lock(args.wheelhouse,args.inventory,args.output)

if __name__=='__main__':
    try: main()
    except (OSError,RuntimeError,ValueError) as error:
        print('Dependency candidate rejected: '+str(error),file=sys.stderr);sys.exit(1)
