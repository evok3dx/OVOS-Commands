#!/usr/bin/env python3
"""Build/stage a separate code-pinned wheel bundle, without resolver fallback.

The wheel lock remains canonical. Archive metadata adds bounds and identity.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def dependencies():
    spec=importlib.util.spec_from_file_location('jarvis_bundle_dependencies',ROOT/'scripts/dependency-lock.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


def digest(path):
    result=hashlib.sha256()
    with path.open('rb') as source:
        while data:=source.read(1024*1024):result.update(data)
    return result.hexdigest()


def records(wheelhouse,inventory,lock):
    dep=dependencies()
    result=dep.wheel_records(wheelhouse)
    exceptions=dep.verify_closure(result,json.loads(inventory.read_text()))
    if exceptions or lock.read_text()!=dep.lock_text(result,exceptions):raise ValueError('Bundle must match the complete zero-exception wheel lock')
    return result


def validate_policy(policy,inventory,lock,artifacts):
    if (policy.get('schema_version')!=1 or policy.get('status')!='built and byte-verified; live acceptance required'
            or policy.get('inventory_sha256')!=digest(inventory) or policy.get('lock_sha256')!=digest(lock)
            or type(policy.get('archive_bytes')) is not int or not 0<policy['archive_bytes']<=2*1024**3
            or not isinstance(policy.get('archive_sha256'),str) or len(policy['archive_sha256'])!=64):
        raise ValueError('Reviewed bundle identity is unavailable or changed')
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,160}\.zip',str(policy.get('archive_name',''))):
        raise ValueError('Reviewed bundle filename is invalid')
    packages=json.loads(artifacts.read_text())['packages']
    wheels=policy.get('wheels')
    if not isinstance(wheels,dict) or set(wheels)!={value['file'] for value in packages.values()}:
        raise ValueError('Bundle differs from canonical wheel inventory')
    for record in packages.values():
        value=wheels[record['file']]
        if (not isinstance(value,dict) or set(value)!={'sha256','bytes'} or value['sha256']!=record['sha256']
                or type(value['bytes']) is not int or not 0<value['bytes']<=1024**3
                or Path(record['file']).name!=record['file']):
            raise ValueError('Unreviewed wheel bounds or identity')
    return wheels


def build(wheelhouse,inventory,lock,artifacts,output,policy_path):
    if output.exists() or output.is_symlink() or policy_path.exists() or policy_path.is_symlink():
        raise ValueError('Choose new archive and policy output paths')
    verified=records(wheelhouse,inventory,lock)
    expected=json.loads(artifacts.read_text())['packages']
    if {key:(v['file'],v['sha256']) for key,v in verified.items()}!={key:(v['file'],v['sha256']) for key,v in expected.items()}:
        raise ValueError('Canonical wheel artifact identities changed')
    output.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.runtime-bundle-',dir=output.parent);os.close(fd)
    temporary=Path(name)
    try:
        wheels={}
        with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_STORED,allowZip64=False) as archive:
            items={'runtime.txt':lock,**{'wheels/'+value['file']:wheelhouse/value['file'] for value in verified.values()}}
            for entry,path in sorted(items.items()):
                if path.is_symlink() or not path.is_file():raise ValueError('Regular reviewed bundle inputs required')
                info=zipfile.ZipInfo(entry,date_time=(1980,1,1,0,0,0));info.create_system=3
                info.external_attr=(stat.S_IFREG|0o644)<<16
                result=hashlib.sha256();size=0
                with path.open('rb') as source,archive.open(info,'w') as target:
                    while chunk:=source.read(1024*1024):
                        target.write(chunk);result.update(chunk);size+=len(chunk)
                if entry.startswith('wheels/'):
                    wheels[path.name]={'sha256':result.hexdigest(),'bytes':size}
                elif result.hexdigest()!=digest(lock):raise ValueError('Lock changed while building')
        policy={'schema_version':1,'status':'built and byte-verified; live acceptance required',
                'archive_name':output.name,'archive_bytes':temporary.stat().st_size,'archive_sha256':digest(temporary),
                'inventory_sha256':digest(inventory),'lock_sha256':digest(lock),'wheels':wheels}
        validate_policy(policy,inventory,lock,artifacts)
        with tempfile.TemporaryDirectory(prefix='.runtime-verify-',dir=output.parent) as folder:
            stage(temporary,policy,inventory,lock,artifacts,Path(folder)/'wheels')
        # Atomic publication without replacing an existing file.
        os.link(temporary,output)
        try:dependencies().private_write(policy_path,json.dumps(policy,indent=2,sort_keys=True)+'\n')
        except BaseException:output.unlink();raise
    finally:temporary.unlink(missing_ok=True)
    return policy


def stage(bundle,policy,inventory,lock,artifacts,output):
    wheels=validate_policy(policy,inventory,lock,artifacts)
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in (output,*output.parents)):
        raise ValueError('Choose a new regular staging output')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.runtime-stage-',dir=output.parent) as directory:
        root=Path(directory);copy=root/'runtime.zip'
        result=hashlib.sha256();size=0
        with bundle.open('rb') as source,copy.open('xb') as destination:
            while chunk:=source.read(1024*1024):
                size+=len(chunk)
                if size>policy['archive_bytes']:raise ValueError('Runtime archive exceeds code-pinned size')
                destination.write(chunk);result.update(chunk)
        if size!=policy['archive_bytes'] or result.hexdigest()!=policy['archive_sha256']:
            raise ValueError('Runtime archive identity failed')
        expected={'runtime.txt':{'bytes':lock.stat().st_size,'sha256':digest(lock)},
                  **{'wheels/'+name:value for name,value in wheels.items()}}
        target=root/'wheels';target.mkdir(mode=0o700)
        with zipfile.ZipFile(copy) as archive:
            entries=archive.infolist()
            if len(entries)!=len(expected) or {entry.filename for entry in entries}!=set(expected):
                raise ValueError('Extra, duplicate or missing runtime archive entry')
            for entry in entries:
                mode=entry.external_attr>>16
                value=expected[entry.filename]
                if (entry.flag_bits&1 or entry.is_dir() or entry.compress_type!=zipfile.ZIP_STORED
                        or not stat.S_ISREG(mode) or entry.file_size!=value['bytes']):
                    raise ValueError('Runtime archive type/size changed')
                digest_value=hashlib.sha256();count=0
                file=target/Path(entry.filename).name if entry.filename.startswith('wheels/') else root/'runtime.txt'
                with archive.open(entry) as source,file.open('xb') as destination:
                    while data:=source.read(1024*1024):
                        count+=len(data)
                        if count>value['bytes']:raise ValueError('Wheel bounds failed')
                        destination.write(data);digest_value.update(data)
                if count!=value['bytes'] or digest_value.hexdigest()!=value['sha256']:raise ValueError('Packaged wheel identity failed')
        records(target,inventory,lock)
        target.rename(output)


def obtain(bundle,policy,inventory,lock,artifacts,output):
    validate_policy(policy,inventory,lock,artifacts)
    if bundle is not None:
        stage(bundle,policy,inventory,lock,artifacts,output);return
    version=json.loads((ROOT/'compatibility.json').read_text())['release_version']
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:rc\d+)?',version):raise ValueError('Unreviewed runtime release version')
    url='https://github.com/evok3dx/OVOS-Commands/releases/download/v'+version+'/'+policy['archive_name']
    spec=importlib.util.spec_from_file_location('jarvis_bundle_transport',ROOT/'scripts/update.py')
    transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.runtime-download-',dir=output.parent) as directory:
        file=Path(directory)/'runtime.zip'
        transport.download(url,file,limit=policy['archive_bytes'])
        stage(file,policy,inventory,lock,artifacts,output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('build','stage','obtain'))
    parser.add_argument('--wheelhouse',type=Path);parser.add_argument('--bundle',type=Path)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--policy',type=Path,required=True)
    parser.add_argument('--inventory',type=Path,default=ROOT/'voice/runtime-linux-x86_64-py311.json')
    parser.add_argument('--lock',type=Path,default=ROOT/'voice/runtime-wheels-linux-x86_64-py311.txt')
    parser.add_argument('--artifacts',type=Path,default=ROOT/'voice/runtime-wheels-linux-x86_64-py311.artifacts.json')
    args=parser.parse_args()
    if args.action=='build':
        if not args.wheelhouse or args.bundle:parser.error('build requires --wheelhouse')
        build(args.wheelhouse,args.inventory,args.lock,args.artifacts,args.output,args.policy)
    else:
        if args.wheelhouse or (args.action=='stage' and not args.bundle):parser.error('stage requires --bundle; obtain may use the fixed reviewed release')
        (stage if args.action=='stage' else obtain)(args.bundle,json.loads(args.policy.read_text()),args.inventory,args.lock,args.artifacts,args.output)
    print('Verified separate runtime bundle. No environment or model was installed.')


if __name__=='__main__':main()
