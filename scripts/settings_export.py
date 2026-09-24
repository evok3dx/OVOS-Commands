"""Private, bounded settings export. Does not apply configuration or call services."""
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import tempfile

MAX_FILE = 4 * 1024 * 1024
MAX_TOTAL = 24 * 1024 * 1024
FIXED = ('.config/mycroft/mycroft.conf', '.config/ovos/ovos.conf',
         '.config/ovos/mycroft.conf', '.local/share/ovos/sounds/jarvis-ready.wav')
FIXED += tuple('.config/jarvis/'+name for name in ('capabilities.json', 'profile.json',
    'custom-commands.json', 'listen-shortcut.json', 'router.json', 'update.json'))
GROUPS = ('.config/ovos/personas', '.local/share/ovos/personas')


def private_bytes(home, relative):
    path=home/relative
    for item in (path,*path.parents):
        if item==home:break
        if item.is_symlink():raise ValueError('symbolic link')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):raise ValueError('not a regular file')
        if before.st_size>MAX_FILE:raise ValueError('larger than 4 MiB')
        data=stream.read(MAX_FILE+1)
        after=os.fstat(stream.fileno())
        if len(data)>MAX_FILE:raise ValueError('larger than 4 MiB')
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
            raise ValueError('changed during export; retry')
    return data


def export_settings(folder, home=None):
    home=Path(home or Path.home()).resolve(); folder=Path(folder)
    paths=set(FIXED); skipped=[]
    for group in GROUPS:
        directory=home/group
        if not directory.exists() and not directory.is_symlink():continue
        if any(p.is_symlink() for p in (directory,*directory.parents) if p!=home and home in p.parents):
            skipped.append({'path':group,'reason':'symbolic link'});continue
        try:
            for p in directory.glob('*.json'):
                if p.name!='builtin-command-phrases.json':paths.add(str(p.relative_to(home)))
        except OSError as exc:skipped.append({'path':group,'reason':type(exc).__name__})
    files={}; total=0
    for relative in sorted(paths):
        try:content=private_bytes(home,relative)
        except FileNotFoundError:continue
        except (OSError,ValueError) as exc:
            skipped.append({'path':relative,'reason':str(exc)});continue
        total+=len(content)
        if total>MAX_TOTAL:raise RuntimeError('Settings exceed 24 MiB; no export created')
        files[relative]=content
    if not files:raise RuntimeError('No readable settings found; no export created')
    stamp=datetime.now(timezone.utc)
    manifest={'format':'jarvis-settings-export','version':1,'created_utc':stamp.isoformat(),
              'files':[{'path':p,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for p,b in files.items()],
              'skipped':skipped,'scope':'User settings only. No automatic restore, models, code, logs or recordings.'}
    readme='''PRIVATE JARVIS SETTINGS BACKUP

Contains saved user configuration, which may include service credentials.
No logs, transcripts, recordings, models or application data are included.
The listening cue is a fixed sound asset, not a microphone recording.

Files under settings/ retain paths relative to the original home directory.
manifest.json lists exact files, checksums and anything skipped. Missing optional
files are normal. This is not a complete system backup or a runnable installer.

To restore: unpack into a separate directory, review the manifest and compare
settings with the destination machine before copying selected files to its home.
Use Configure Jarvis to reapply keyboard shortcuts. Installed applications,
models, plugins and local code changes are not recreated by this archive.
There is no automatic import button in this update.
'''
    fd,temp=tempfile.mkstemp(prefix='.jarvis-export-',dir=folder)
    target=None
    try:
        with os.fdopen(fd,'wb') as raw:
            with tarfile.open(fileobj=raw,mode='w:gz') as archive:
                entries={'README.txt':readme.encode(),'manifest.json':(json.dumps(manifest,indent=2)+'\n').encode()}
                entries.update({'settings/'+p:b for p,b in files.items()})
                for name,content in entries.items():
                    info=tarfile.TarInfo(name);info.size=len(content);info.mode=0o600;info.mtime=int(stamp.timestamp())
                    archive.addfile(info,io.BytesIO(content))
            raw.flush();os.fsync(raw.fileno())
        # Hard-link publication is atomic and refuses to overwrite an existing backup.
        for index in range(100):
            name='jarvis-settings-'+stamp.strftime('%Y%m%dT%H%M%SZ')+(f'-{index}' if index else '')+'.tar.gz'
            target=folder/name
            try:os.link(temp,target);break
            except FileExistsError:continue
        else:raise RuntimeError('Could not allocate a new backup filename')
        return {'path':str(target),'files':len(files),'skipped':skipped}
    finally:
        Path(temp).unlink(missing_ok=True)
