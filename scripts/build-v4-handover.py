#!/usr/bin/env python3
"""Package only the reviewed read-only laptop evidence tools, without host data."""
import hashlib
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
FILES=('scripts/v4-laptop-check.py','scripts/dependency-lock.py',
       'scripts/core-isolation-preflight.py','scripts/startup_settings.py','voice/reviewed-stack.json',
       'compatibility.json')
README='''Jarvis V4 read-only laptop check

Extract this folder in Downloads, then run as your normal desktop user:

~/.venvs/ovos/bin/python ~/Downloads/jarvis-v4-laptop-check/scripts/v4-laptop-check.py

Review and share Downloads/jarvis-v4-laptop-check.json.
For a repeat, choose a new output with --output ~/Downloads/jarvis-v4-laptop-check-2.json

This does not install, restart, download models or change service/firewall rules.
It reads package versions, bounded configuration indicators, service state
and the saved voice/tray login preference. It does not enable auto-start.
It uses one fixed loopback-only GET to record the configured Qwen digest.
It excludes raw settings, URLs, paths, hostnames, credentials and transcripts.
It is inventory only. Voice, GUI, effective tool permissions, model authenticity
and actual egress enforcement still require separate testing.
'''


def build(output):
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            path=ROOT/name
            if path.is_symlink() or not path.is_file():
                raise RuntimeError('Missing reviewed handover file')
            archive.write(path,'jarvis-v4-laptop-check/'+name)
        archive.writestr('jarvis-v4-laptop-check/README.txt',README)
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(digest+'  '+output.name+'\n')
    print('Built read-only laptop handover and SHA-256 checksum.')


if __name__=='__main__':
    build(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'dist/jarvis-v4-laptop-check.zip')
