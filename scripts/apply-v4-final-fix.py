#!/usr/bin/env python3
"""Apply the reviewed V4 final music/UI/CLI hotfix with voice stopped, without sudo."""
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

COMMIT='2df1de58bdd09520606cbaa2ee2aa89ef839dc8f'
FILES = [{'path': 'scripts/control_center.py', 'before': ['4183c3671191944880daa21d3b8f8d162845a3fc0a931f0dd3dddb32888b0b6d'], 'after': '1494ede7393fd0a2ebbc28af5a93c336bc807a208e8320a776781b038ddf4f7c'}, {'path': 'scripts/install.sh', 'before': ['e8f8e4bac96426b401a5465c8a8f26713f5d33cda3f9db5652c5bb6892701af4'], 'after': '9229bb8d4cc3749557aef41101f801407262d17a0088b2e71c88f8674a911be5'}, {'path': 'scripts/isolation_worker.py', 'before': ['a87c945513d81524cad61076514bf1b6541116b8d60977081c217c2995f8fe38'], 'after': '52c5c985480632aa02c0f68a7fc89b2c884c9c119d14cfc71d3705c0bdc058d4'}, {'path': 'scripts/runtime_bundle.py', 'before': ['c49fc4609f03a802f158ccf133084608eff76a998ea3bc2d7fe88241d8f70fb4'], 'after': 'b5f03dc273d3a03da1b7e3c0ac8d515365c51ccf8cf628090b97241fa79da7a5'}, {'path': 'scripts/update.py', 'before': ['95929f8b12c1c470377661adf9ac04916ee0af759b8e2d9aa6d262c6af9d9ba6'], 'after': '5b462e983004ecd5b7617d19966fb96b9504f4b53cb03459d61fbbb104c3ca2e'}, {'path': 'deployment-manifest.json', 'before': ['446a9280eb927abd9b0e2645dfb4734035091ba0a63a66e08309c573f8bba58f'], 'after': '71ca068dde784e3fbf45108a1ca46ce4ca7f3280d872625ecbfab9effd0ebfc7'}, {'path': 'ovos_skill_jarvis_dispatcher/browser.py', 'before': ['4718ae61340fffbeb6895dd439d83bac7b46f7c7fd534d98d8d7e6639496b612'], 'after': '59f6e26866d1bc07eab182e17379a60f32865c5de920ba73129f0d7db5ecc70b'}, {'path': 'ovos_skill_jarvis_dispatcher/search_pacing.py', 'before': ['06a9f2ea3d1aa3c24cb3510e1a78ce1b84918155f04e58ef56b0acd256236d99'], 'after': '8b29a6234a24b95df186d33c0d6836012896b1b716053768bd31b162f63a9c65'}, {'path': 'plugins/ovos-skill-jarvis-media/ovos_skill_jarvis_media/__init__.py', 'before': ['5849339c9ebab23a461c27a46112886dfbf65fd09aa0c4babf6684a1185ac47d'], 'after': '8af0ac7ccf7930ca15772cd9dc6d2dd9759321705132b41c4f1ec35f30d1e261'}, {'path': 'plugins/ovos-skill-jarvis-media/ovos_skill_jarvis_media/bridge.py', 'before': ['33e1936f4f3fd44456d9a784490664f68e12dce621388b2e1e7409e43e20a0a7'], 'after': 'c5fc2668590fbac598bf51a71ea5f0d241a524f5b89a5ba1d9630c3703d471b0'}, {'path': 'plugins/ovos-skill-jarvis-media/ovos_skill_jarvis_media/pipeline.py', 'before': ['1995935f06c1e31a437c71c3ccc9af3814a6ac71f8af0c65ec83fd2a24ada993'], 'after': '3cc00c34407659141acfe1723178b8059c6007279a0c367522baa8d9618c36ca'}, {'path': 'plugins/ovos-skill-jarvis-media/pyproject.toml', 'before': ['b900ff83ac096d655487e636485253adc48be73a72ab0c408b923d8974cd5b28'], 'after': '6257618e4dc5673f9c08eebe8be5dce961dba9055ca5fdd071f000a9920def51'}, {'path': 'scripts/installer_progress.py', 'before': [None], 'after': '9516bff1f6e4bffdf87501acda215ec2fa1de00fe5219e86c650aff489f0c25b'}]


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
        print('Checking installed sources and downloading 13 small verified files…',flush=True)
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
        folder=Path(tempfile.mkdtemp(prefix='jarvis-v4-music-fix.',dir=downloads_dir))
        os.chmod(folder,0o700)
        for entry,(_,old,_) in zip(FILES,previous):
            backup=folder/entry['path'];backup.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            if old is not None:backup.write_bytes(old);backup.chmod(0o600)
        log=folder/'media-registration.log';log.touch(mode=0o600)
        print('Applying verified source patch and registering Media locally…',flush=True)
        try:
            for (target,old,mode),new in zip(previous,downloads):atomic(target,new,mode)
            install_media(root,log)
            if metadata.version('ovos-skill-jarvis-media')!='0.3.3':raise RuntimeError('Media registration version was not updated.')
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
        print('Test one ready announcement, microphone active, reading, music and a clean Stop.')


if __name__=='__main__':
    try:main()
    except Exception as error:
        print(str(error),file=sys.stderr);raise SystemExit(1)
