#!/usr/bin/env python3
"""Apply the reviewed V4 lifecycle/music hotfix with voice stopped, without sudo."""
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

COMMIT='36e9fc7a9abd8be10992d1a8b3466f51761c4129'
FILES = [{'path': 'scripts/control_runtime.py', 'before': ['827827ec55aeebaa3ef0232f5aa55ef2f7829dc8b82cb3978231cc68b53c76f7', '4b8f9cac1b18e5b36da36b0eaf2be20aefb6152cc7d7d18c57ea7ee5d9ccc1e2'], 'after': 'c07810507dfdcce0ce940ad0233604715c5315064aaab46826021bb71cf54adc'}, {'path': 'scripts/isolation_worker.py', 'before': ['d2ea52c1240b7c571f78fde50348351eaa287ba8fce6e58e33f3f87aeb75678e'], 'after': 'a87c945513d81524cad61076514bf1b6541116b8d60977081c217c2995f8fe38'}, {'path': 'ovos_skill_jarvis_dispatcher/browser.py', 'before': ['be3c06d235b5bd1cd2199cdd401bb9a3520c90552a72c2e90416ca3bfd36e047'], 'after': '4718ae61340fffbeb6895dd439d83bac7b46f7c7fd534d98d8d7e6639496b612'}, {'path': 'ovos_skill_jarvis_dispatcher/search_pacing.py', 'before': ['39fc4ab37260ac64ffdcd79107c6746236398ab952b93ad6afcb909eaceb6756'], 'after': '06a9f2ea3d1aa3c24cb3510e1a78ce1b84918155f04e58ef56b0acd256236d99'}, {'path': 'plugins/ovos-skill-jarvis-media/ovos_skill_jarvis_media/__init__.py', 'before': ['812b419bbd70d6c0e6becba5cbe93814e789865a42762701b93d77e4466b816b'], 'after': '5849339c9ebab23a461c27a46112886dfbf65fd09aa0c4babf6684a1185ac47d'}, {'path': 'plugins/ovos-skill-jarvis-media/pyproject.toml', 'before': ['08f3ac531583df20598ee3f749bd34859e2326273870494101bb4d07fe26666b'], 'after': 'b900ff83ac096d655487e636485253adc48be73a72ab0c408b923d8974cd5b28'}]


def safe(path,private=False):
    if any(p.is_symlink() for p in (path,*path.parents)):
        raise RuntimeError('A source or backup path is a symbolic link; nothing changed.')
    info=path.stat()
    if (info.st_uid!=os.getuid() or info.st_mode & (0o077 if private else 0o022)
            or not stat.S_ISREG(info.st_mode)):
        raise RuntimeError('Source ownership/type needs review; nothing changed.')
    return path.read_bytes()


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
        print('Checking installed sources and downloading six small verified files…',flush=True)
        for entry in FILES:
            target=root/entry['path'];old=safe(target)
            if hashlib.sha256(old).hexdigest() not in [*entry['before'],entry['after']]:
                raise RuntimeError('Installed source differs from the reviewed release; nothing changed: '+entry['path'])
            url=f'https://raw.githubusercontent.com/evok3dx/OVOS-Commands/{COMMIT}/'+entry['path']
            with urlopen(url,timeout=30) as response:new=response.read(100000)
            if hashlib.sha256(new).hexdigest()!=entry['after']:raise RuntimeError('Download checksum failed; nothing changed.')
            if target.suffix=='.py':ast.parse(new)
            if target.suffix=='.toml':
                import tomllib
                tomllib.loads(new.decode())
            previous.append((target,old,stat.S_IMODE(target.stat().st_mode)))
            downloads.append(new)
        stopped()
        for target,old,mode in previous:
            if safe(target)!=old:raise RuntimeError('Source changed during review; nothing changed.')
        folder=Path(tempfile.mkdtemp(prefix='jarvis-v4-final-fix.',dir=home/'Downloads'))
        os.chmod(folder,0o700)
        for entry,(_,old,_) in zip(FILES,previous):
            backup=folder/entry['path'];backup.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            backup.write_bytes(old);backup.chmod(0o600)
        log=folder/'media-registration.log';log.touch(mode=0o600)
        print('Applying verified source patch and registering Media locally…',flush=True)
        try:
            for (target,old,mode),new in zip(previous,downloads):atomic(target,new,mode)
            install_media(root,log)
            if metadata.version('ovos-skill-jarvis-media')!='0.3.2':raise RuntimeError('Media registration version was not updated.')
        except BaseException:
            for target,old,mode in previous:atomic(target,old,mode)
            try:install_media(root,log)
            except Exception:print('Source files restored; Media registration needs review. Keep voice stopped.',file=sys.stderr)
            raise
        print('Installed. Settings, models and native network policy are preserved.')
        print('Backup:',folder)
        print('Close/reopen the Control Centre, refresh the tray, then choose Run Jarvis.')
        print('Test one ready announcement, microphone active, reading, music and a clean Stop.')


if __name__=='__main__':
    try:main()
    except Exception as error:
        print(str(error),file=sys.stderr);raise SystemExit(1)
