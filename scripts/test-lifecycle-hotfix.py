#!/usr/bin/env python3
"""Hotfix source guards and rollback after local registration failure."""
import contextlib
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

if os.getuid()==0:raise RuntimeError('Run regression as the ordinary user')
spec=importlib.util.spec_from_file_location('hotfix',Path(__file__).with_name('apply-v4-lifecycle-fix.py'))
hotfix=importlib.util.module_from_spec(spec);spec.loader.exec_module(hotfix)
with patch.object(hotfix.os,'getuid',return_value=0):
    try:hotfix.main()
    except RuntimeError as error:assert 'without sudo' in str(error)
    else:raise AssertionError('Root repair accepted')

with tempfile.TemporaryDirectory() as directory:
    home=Path(directory);(home/'Downloads').mkdir()
    root=home/'.local/src/ovos-skill-jarvis-dispatcher';root.mkdir(parents=True)
    target=root/'fixture.py';old=b'value=1\n';new=b'value=2\n'
    target.write_bytes(old);target.chmod(0o644)
    records=[{'path':'fixture.py','before':[hashlib.sha256(old).hexdigest()],
              'after':hashlib.sha256(new).hexdigest()}]
    calls=[]
    def register(project,log):
        calls.append(target.read_bytes())
        if len(calls)==1:raise RuntimeError('Injected local registration failure')
    with patch.object(hotfix.Path,'home',return_value=home),patch.object(hotfix.sys,'prefix',str(home/'.venvs/ovos')),\
         patch.object(hotfix.sys,'argv',['fix']),patch.object(hotfix,'FILES',records),\
         patch.object(hotfix,'stopped'),patch.object(hotfix,'editable'),\
         patch.object(hotfix,'urlopen',return_value=io.BytesIO(new)),\
         patch.object(hotfix,'install_media',register),contextlib.redirect_stdout(io.StringIO()):
        try:hotfix.main()
        except RuntimeError as error:assert 'Injected' in str(error)
        else:raise AssertionError('Failed registration reported success')
    assert calls==[new,old] and target.read_bytes()==old and target.stat().st_mode & 0o777==0o644
    backup=next((home/'Downloads').glob('jarvis-v4-final-fix.*'))
    assert (backup/'fixture.py').read_bytes()==old and backup.stat().st_mode & 0o777==0o700
    assert (backup/'fixture.py').stat().st_mode & 0o777==0o600
    target.write_bytes(b'custom=3\n')
    with patch.object(hotfix.Path,'home',return_value=home),patch.object(hotfix.sys,'prefix',str(home/'.venvs/ovos')),\
         patch.object(hotfix.sys,'argv',['fix']),patch.object(hotfix,'FILES',records),\
         patch.object(hotfix,'stopped'),patch.object(hotfix,'editable'),\
         patch.object(hotfix,'urlopen',side_effect=AssertionError('Unknown source downloaded')),\
         contextlib.redirect_stdout(io.StringIO()):
        try:hotfix.main()
        except RuntimeError as error:assert 'differs' in str(error)
        else:raise AssertionError('Unknown/custom source replaced')
    assert target.read_bytes()==b'custom=3\n'
    with patch.object(hotfix.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'LoadState=loaded\nActiveState=active\nMainPID=123\n','')):
        try:hotfix.stopped()
        except RuntimeError:pass
        else:raise AssertionError('Hotfix accepted running worker')
print('PASS: normal-user/stopped-worker guards, unknown source preservation and complete source/registration rollback')
