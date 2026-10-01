#!/usr/bin/env python3
"""Apply the reviewed V4 Media result timing correction with voice stopped, without sudo."""
import ast
import fcntl
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from urllib.request import urlopen
from urllib.parse import urlparse,unquote

COMMIT='6dd4283e080160a640aa358d61a44b1d40772412'
FILES = [{'path': 'plugins/ovos-skill-jarvis-media/ovos_skill_jarvis_media/__init__.py', 'before': ['fea8b323541827590cc04a6fed1db985e06127edbad4cc6fb61d951f82a5e989'], 'after': '586faebcb9e001358cd5ff599dfe8ca6df27b23e1752a83d00680b5b691d75ca'}, {'path': 'plugins/ovos-skill-jarvis-media/pyproject.toml', 'before': ['3da6c7dfab2ee9b38ec123654f08ce2d5d6338e44749684086f038e67b3e5600'], 'after': 'd17c83883a16f7bbbd9e81f1701d26d3a86eca60d7116f2a930ab0d6d4868bde'}]


def safe(path,private=False):
    if any(p.is_symlink() for p in (path,*path.parents)):
        raise RuntimeError('A source or backup path is a symbolic link; nothing changed.')
    info=path.stat()
    if (info.st_uid!=os.getuid() or info.st_mode & (0o077 if private else 0o022)
            or not stat.S_ISREG(info.st_mode)):
        raise RuntimeError('Source ownership/type needs review; nothing changed.')
    return path.read_bytes()


def current(path, allow_missing=False):
    if any(p.is_symlink() for p in (path,*path.parents)):
        raise RuntimeError('A source path is a symbolic link; nothing changed.')
    if not path.exists():
        parent=path.parent.stat()
        if not allow_missing or not stat.S_ISDIR(parent.st_mode) or parent.st_uid!=os.getuid() or parent.st_mode & 0o022:
            raise RuntimeError('Missing source needs review; nothing changed.')
        return None
    return safe(path)


def stopped():
    for name in ('core','listener','audio','weather','media'):
        result=subprocess.run(['/usr/bin/systemctl','--system','--no-pager','--no-ask-password',
                               'show',f'jarvis-v4-{os.getuid()}-{name}.service',
                               '--property=LoadState,ActiveState,MainPID'],
                              capture_output=True,text=True,timeout=10,check=True)
        values=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
        if values.get('LoadState')!='loaded' or values.get('ActiveState') not in {'inactive','failed'} or values.get('MainPID')!='0':
            raise RuntimeError('Stop Jarvis first. All five native workers must be stopped; no service was changed.')


def atomic(path,data,mode):
    descriptor,name=tempfile.mkstemp(prefix='.v4-fix-',dir=path.parent)
    try:
        with os.fdopen(descriptor,'wb') as output:
            output.write(data);os.fchmod(output.fileno(),mode);output.flush();os.fsync(output.fileno())
        os.replace(name,path)
    finally:Path(name).unlink(missing_ok=True)


def editable(name,expected):
    dist=metadata.distribution(name)
    value=json.loads(dist.read_text('direct_url.json') or '{}')
    url=urlparse(value.get('url',''))
    if (url.scheme!='file' or url.netloc or value.get('dir_info',{}).get('editable') is not True
            or Path(unquote(url.path)).resolve()!=expected.resolve()):
        raise RuntimeError('Installed package is not the reviewed editable deployment; nothing changed.')


def install_media(root,log):
    project=root/'plugins/ovos-skill-jarvis-media'
    probe=subprocess.run([sys.executable,'-m','pip','--version'],capture_output=True,timeout=15)
    flags=['--no-index','--no-deps','--no-build-isolation','--editable',str(project)]
    if probe.returncode==0:
        args=[sys.executable,'-m','pip','install','--disable-pip-version-check',*flags]
    else:
        uv=shutil.which('uv')
        if not uv:raise RuntimeError('Neither existing pip nor uv is available; no dependency will be installed.')
        args=[uv,'pip','install','--python',sys.executable,*flags]
    with log.open('ab') as output:
        result=subprocess.run(args,stdout=output,stderr=subprocess.STDOUT,timeout=120,
                              env={**os.environ,'PIP_NO_INDEX':'1','UV_OFFLINE':'1'})
    if result.returncode:raise RuntimeError('Local Media registration failed; see the private backup log.')


def main():
    if os.getuid()<=0 or os.getuid()!=os.geteuid():raise RuntimeError('Run as your normal desktop user, without sudo.')
    if len(sys.argv)!=1:raise RuntimeError('This bounded hotfix takes no arguments.')
    home=Path.home();root=home/'.local/src/ovos-skill-jarvis-dispatcher'
    if Path(sys.prefix).resolve()!=(home/'.venvs/ovos').resolve():
        raise RuntimeError('Run with $HOME/.venvs/ovos/bin/python -I.')
    lockdir=home/'.local/state/jarvis-ui'
    lockdir.mkdir(parents=True,exist_ok=True)
    lockpath=lockdir/'controls.lock'
    if any(p.is_symlink() for p in (lockpath,*lockpath.parents)):raise RuntimeError('Control lock path needs review.')
    with lockpath.open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        stopped()
        editable('ovos-skill-jarvis-dispatcher',root)
        editable('ovos-skill-jarvis-media',root/'plugins/ovos-skill-jarvis-media')
        previous=[];downloads=[]
        print('Checking installed sources and downloading 2 small verified files…',flush=True)
        for entry in FILES:
            target=root/entry['path'];old=current(target,allow_missing=None in entry['before'])
            identity=hashlib.sha256(old).hexdigest() if old is not None else None
            if identity not in [*entry['before'],entry['after']]:
                raise RuntimeError('Installed source differs from the reviewed release; nothing changed: '+entry['path'])
            url=f'https://raw.githubusercontent.com/evok3dx/OVOS-Commands/{COMMIT}/'+entry['path']
            with urlopen(url,timeout=30) as response:new=response.read(100000)
            if hashlib.sha256(new).hexdigest()!=entry['after']:raise RuntimeError('Download checksum failed; nothing changed.')
            if target.suffix=='.py':ast.parse(new)
            if target.suffix=='.toml':
                import tomllib
                tomllib.loads(new.decode())
            previous.append((target,old,stat.S_IMODE(target.stat().st_mode) if old is not None else 0o755))
            downloads.append(new)
        stopped()
        for target,old,mode in previous:
            if current(target,allow_missing=old is None)!=old:raise RuntimeError('Source changed during review; nothing changed.')
        downloads_dir=home/'Downloads'
        if any(p.is_symlink() for p in (downloads_dir,*downloads_dir.parents)):
            raise RuntimeError('Downloads path needs review; nothing changed.')
        downloads_dir.mkdir(exist_ok=True)
        if downloads_dir.stat().st_uid!=os.getuid():raise RuntimeError('Downloads ownership needs review.')
        folder=Path(tempfile.mkdtemp(prefix='jarvis-v4-media-timing-fix.',dir=downloads_dir))
        os.chmod(folder,0o700)
        for entry,(_,old,_) in zip(FILES,previous):
            backup=folder/entry['path'];backup.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            if old is not None:backup.write_bytes(old);backup.chmod(0o600)
        log=folder/'media-registration.log';log.touch(mode=0o600)
        print('Applying verified source patch and registering Media locally…',flush=True)
        try:
            for (target,old,mode),new in zip(previous,downloads):atomic(target,new,mode)
            install_media(root,log)
            if metadata.version('ovos-skill-jarvis-media')!='0.3.5':raise RuntimeError('Media registration version was not updated.')
        except BaseException:
            for target,old,mode in previous:
                if old is None:target.unlink(missing_ok=True)
                else:atomic(target,old,mode)
            try:install_media(root,log)
            except Exception:print('Source files restored; Media registration needs review. Keep voice stopped.',file=sys.stderr)
            raise
        print('Installed. Settings, models and native network policy are preserved.')
        print('Backup:',folder)
        print('Close/reopen the Control Centre, refresh the tray, then choose Run Jarvis.')
        print('Test a song: immediate acknowledgement, lookup, then three seconds before opening. Test Stop during the pause.')


if __name__=='__main__':
    try:main()
    except Exception as error:
        print(str(error),file=sys.stderr);raise SystemExit(1)
