#!/usr/bin/env python3
"""Prepare a reviewed network-only drop-in for the existing system Ollama.

No installation, restart, model pull, account change or administrator command.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from private_reports import next_path
import shlex
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from prepare_core_isolation import private_file
from isolation_services import regular

DEST='/etc/systemd/system/ollama.service.d/90-jarvis-isolation.conf'
POLICY='[Service]\nIPAddressDeny=\nIPAddressAllow=\nIPAddressDeny=any\nIPAddressAllow=127.0.0.1 ::1\nIPAccounting=yes\n'


def daemon_context():
    result=subprocess.run(['/usr/bin/systemctl','--system','show','ollama.service',
                           '--property=LoadState,ActiveState,MainPID,FragmentPath,IPAddressAllow,IPAddressDeny'],
                          capture_output=True,text=True,timeout=5)
    props=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    if result.returncode or props.get('LoadState')!='loaded' or props.get('ActiveState')!='active':
        raise RuntimeError('The existing system Ollama must be observable; no guessed daemon migration')
    pid=props.get('MainPID','')
    if not pid.isdigit() or int(pid)<=0:raise RuntimeError('Existing daemon identity unavailable')
    values=dict(line.split(':',1) for line in Path('/proc',pid,'status').read_text().splitlines() if ':' in line)
    identities=values.get('Uid','').split()
    if len(identities)!=4 or not all(value.isdigit() and int(value)>0 for value in identities):
        raise RuntimeError('Existing Ollama is not an observed ordinary-user process; review its account first')
    fragment=Path(props.get('FragmentPath',''))
    if not fragment.is_absolute():raise RuntimeError('Existing daemon unit needs review')
    regular(fragment,owner=0)
    if props.get('IPAddressAllow') or props.get('IPAddressDeny'):
        raise RuntimeError('Existing custom daemon IP policy needs review before replacement')
    return {'system_service_observed':True,'ordinary_daemon_uid_observed':True,
            'base_unit_sha256':hashlib.sha256(fragment.read_bytes()).hexdigest(),
            'effective_model_egress_verified':False}


def prepare(output):
    if os.getuid()<=0 or os.getuid()!=os.geteuid() or os.getgid()!=os.getegid():
        raise ValueError('Run as the normal desktop user, never sudo Python')
    roots=(Path.home()/'Downloads/jarvis-v4-model-isolation-candidates',
           Path.home()/'.local/state/jarvis/model-isolation-candidates')
    root=next((root for root in roots if root in output.parents),None)
    if root is None or any(p.is_symlink() for p in (output,*output.parents)):
        raise ValueError('Use a new private Jarvis model-isolation-candidates directory in Downloads')
    context=daemon_context()
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    if root.stat().st_uid!=os.getuid() or root.stat().st_mode & 0o077:
        raise ValueError('Candidate directory must be private and user-owned')
    output.parent.mkdir(parents=True,exist_ok=True,mode=0o700);output.mkdir(mode=0o700)
    try:
        private_file(output/'90-jarvis-isolation.conf',POLICY)
        private_file(output/'candidate.json',json.dumps({'schema_version':1,'policy_sha256':hashlib.sha256(POLICY.encode()).hexdigest(),
                                                       'context':context},indent=2)+'\n')
        commands=['test ! -e '+shlex.quote(DEST)+' || { echo "Existing owned policy needs review"; exit 1; }',
                  'sudo /usr/bin/install -d -o root -g root -m 0755 -- /etc/systemd/system/ollama.service.d',
                  'sudo /usr/bin/install -o root -g root -m 0644 -- '+shlex.quote(str(output/'90-jarvis-isolation.conf'))+' '+shlex.quote(DEST),
                  'sudo /usr/bin/systemctl daemon-reload','sudo /usr/bin/systemctl restart ollama.service']
        removal=['sudo /usr/bin/rm -- '+shlex.quote(DEST),'sudo /usr/bin/systemctl daemon-reload',
                 'sudo /usr/bin/systemctl restart ollama.service']
        private_file(output/'REVIEW.md','# Existing Ollama network restriction candidate\n\n'
            'Inspect the source drop-in and existing daemon before applying anything. No live changes have occurred.\n'
            'The candidate changes only network/accounting properties. It preserves account, executable, models, CPU/GPU and environment.\n'
            'Normal inference stays local. Model downloads/pulls are deliberately blocked once the policy is enforced.\n'
            'Administrator commands are native, fixed and owner-terminal only. Never sudo repository code or a whole copied script.\n'
            'Stop voice and finish current model work before the explicitly reviewed daemon restart.\n\n'
            '## Native activation after review\n```bash\n'+'\n'.join(commands)+'\n```\n\n'
            'Verify actual daemon cgroup IPv4/IPv6/UDP denial with functioning outside controls, local inference and recovery.\n'
            'Configured properties and the earlier temporary worker pass alone cannot close that gate.\n'
            'Neither the core receipt nor the actual-core socket collector claims Ollama enforcement.\n\n'
            '## Owned removal\n```bash\n'+'\n'.join(removal)+'\n```\n'
            'Remove only this exact owned file, leaving all other daemon drop-ins intact.\n')
    except BaseException:
        for path in output.iterdir():
            if path.is_file() and not path.is_symlink():path.unlink()
        output.rmdir();raise
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    output=args.output or next_path(Path.home()/'Downloads/jarvis-v4-model-isolation-candidates',
                                   'Jarvis-Model-Isolation-Review')
    print(prepare(output))
