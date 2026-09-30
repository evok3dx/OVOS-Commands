#!/usr/bin/env python3
"""Prepare/review an ordinary-user service candidate; never run Python as root."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import shlex
import stat
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from isolation_services import COMPONENTS,LOGICAL,active,regular,session_text
from isolation_worker import verify_pins

DROPIN='90-jarvis-isolation.conf'
SOURCES=('scripts/isolation_worker.py','scripts/isolation_services.py','scripts/weather_boundary.py',
         'scripts/verify_core_isolation.py','scripts/prepare_core_isolation.py','scripts/runtime_provenance.py',
         'voice/runtime-linux-x86_64-py311.json','voice/runtime-wheels-linux-x86_64-py311.txt')


def source_hashes(deployment):
    result={}
    for name in SOURCES:
        path=deployment/name
        regular(path)
        result[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def private_file(path,text):
    if any(p.is_symlink() for p in (path,*path.parents)) or path.exists():
        raise ValueError('Choose a new regular output path')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:
        stream.write(text);stream.flush();os.fsync(stream.fileno())


def unit_string(value):
    value=str(value)
    if any(ord(c)<32 or ord(c)==127 for c in value):raise ValueError('Invalid unit value')
    return '"'+value.replace('\\','\\\\').replace('"','\\"').replace('%','%%')+'"'


def render(uid,gid,username,home,deployment):
    if type(uid) is not int or type(gid) is not int or uid<=0 or gid<=0:
        raise ValueError('Workers must use an ordinary user/group')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]{0,63}',username):raise ValueError('Account name needs review')
    home,deployment=Path(home),Path(deployment)
    if not home.is_absolute() or not deployment.is_absolute():raise ValueError('Absolute deployment paths required')
    units={}
    for name in COMPONENTS:
        dependencies=''
        if name=='core':
            helpers=' '.join(f'jarvis-v4-{uid}-{part}.service' for part in ('weather','media'))
            dependencies=f'Wants={helpers}\nBindsTo=jarvis-v4-{uid}-audio.service\nAfter=jarvis-v4-{uid}-audio.service\n'
        elif name in {'weather','media'}:
            dependencies=f'PartOf=jarvis-v4-{uid}-core.service\nBindsTo=jarvis-v4-{uid}-core.service\nAfter=jarvis-v4-{uid}-core.service\n'
        elif name=='listener':
            needs=f'jarvis-v4-{uid}-core.service jarvis-v4-{uid}-audio.service'
            dependencies=f'BindsTo={needs}\nAfter={needs}\n'
        text=(f'[Unit]\nDescription=Jarvis V4 {name} worker\n{dependencies}'
              f'After=user@{uid}.service\nBindsTo=user@{uid}.service\n'
              f'[Service]\nType=exec\nUser={uid}\nGroup={gid}\nSlice=system.slice\n'
              'NoNewPrivileges=yes\nCapabilityBoundingSet=\nAmbientCapabilities=\n'
              'UMask=0077\nRestart=no\nTimeoutStopSec=20\n'
              f'Environment={unit_string("HOME="+str(home))}\n'
              f'Environment={unit_string("XDG_RUNTIME_DIR=/run/user/"+str(uid))}\n'
              f'Environment={unit_string("DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/"+str(uid)+"/bus")}\n'
              f'EnvironmentFile={unit_string(home/".local/state/jarvis/isolation/session.env")}\n'
              'Environment=HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1\n'
              f'ExecStart={unit_string(home/".venvs/ovos/bin/python")} -I '
              f'{unit_string(deployment/"scripts/isolation_worker.py")} {name} --uid {uid} --gid {gid}\n')
        if name in LOGICAL.values():
            text+='IPAddressDeny=any\nIPAddressAllow=127.0.0.1 ::1\nIPAccounting=yes\n'
        units[f'jarvis-v4-{uid}-{name}.service']=text
    rule=('polkit.addRule(function(action, subject) {\n'
          '  if (action.id !== "org.freedesktop.systemd1.manage-units" || '
          f'subject.user !== {json.dumps(username)}) return;\n'
          f'  var units = {json.dumps(list(units))};\n'
          '  var verbs = ["start", "stop", "restart"];\n'
          '  if (units.indexOf(action.lookup("unit")) >= 0 && verbs.indexOf(action.lookup("verb")) >= 0) return polkit.Result.YES;\n'
          '});\n')
    dropins={logical:'[Service]\nType=oneshot\nRemainAfterExit=yes\nRestart=no\nExecStart=\nExecStop=\nExecReload=\n'
             f'ExecStart=/usr/bin/systemctl --system --no-ask-password start jarvis-v4-{uid}-{part}.service\n'
             f'ExecStop=/usr/bin/systemctl --system --no-ask-password stop jarvis-v4-{uid}-{part}.service\n'
             for logical,part in LOGICAL.items()}
    return units,rule,dropins


def prepare(output,deployment):
    account=pwd.getpwuid(os.getuid())
    if account.pw_gid!=os.getgid():raise ValueError('Account group needs review')
    verify_pins()
    for name in ('isolation_worker.py','weather_boundary.py','verify_core_isolation.py'):
        regular(deployment/'scripts'/name)
    root=Path(account.pw_dir)/'.local/state/jarvis/isolation-candidates'
    if root not in output.parents or any(p.is_symlink() for p in (output,*output.parents)):
        raise ValueError('Use a new private candidate directory under Jarvis isolation-candidates')
    output.parent.mkdir(parents=True,exist_ok=True,mode=0o700);output.mkdir(mode=0o700)
    try:
        units,rule,dropins=render(account.pw_uid,account.pw_gid,account.pw_name,account.pw_dir,deployment)
        files={**units,f'90-jarvis-v4-{account.pw_uid}.rules':rule,
               **{name+'.dropin':body for name,body in dropins.items()}}
        for name,body in files.items():private_file(output/name,body)
        info={'schema_version':1,'uid':account.pw_uid,'gid':account.pw_gid,'username':account.pw_name,
              'home':account.pw_dir,'deployment':str(deployment),
              'source_sha256':source_hashes(deployment),
              'sha256':{name:hashlib.sha256(body.encode()).hexdigest() for name,body in files.items()}}
        private_file(output/'candidate.json',json.dumps(info,indent=2)+'\n')
        installs=[];removal=['sudo /usr/bin/systemctl stop '+' '.join(units)]
        for name in [*units,f'90-jarvis-v4-{account.pw_uid}.rules']:
            dest=('/etc/polkit-1/rules.d/' if name.endswith('.rules') else '/etc/systemd/system/')+name
            installs.append('test ! -e '+shlex.quote(dest)+' || { echo "Existing native data needs review"; exit 1; }')
            installs.append('sudo /usr/bin/install -o root -g root -m 0644 -- '+shlex.quote(str(output/name))+' '+shlex.quote(dest))
            removal.append('sudo /usr/bin/rm -- '+shlex.quote(dest))
        installs.append('sudo /usr/bin/systemctl daemon-reload');removal.append('sudo /usr/bin/systemctl daemon-reload')
        private_file(output/'REVIEW.md','# Private V4 service candidate\n\n'
            'Inspect the units, account and exact five-unit/three-verb rule before native installation.\n'
            'Never sudo Python, pip, extraction, repository code or a whole generated script.\n'
            'These native commands install data only. No boot enablement or listening port is added.\n'
            'Stop Jarvis before activate/deactivate. Settings, models and login choices stay owned by their existing files.\n\n'
            '## Native installation after review\n```bash\n'+'\n'.join(installs)+'\n```\n\n'
            'Activate as the ordinary user with prepare_core_isolation.py activate --candidate PATH.\n'
            'If the public rule is hidden, authorise native sudo in your own terminal first. Activation never prompts for a password.\n'
            'Use Run Jarvis and complete actual-worker, voice, desktop, weather, Media and recovery acceptance.\n'
            'Known web/query skills are disabled in the core overlay. Weather and Media run separately. Local Qwen remains.\n'
            'Same-user IPC/desktop mediation is trusted. A receipt proves no enforcement.\n'
            'The existing Ollama service remains unrestricted by this candidate and is a release gate.\n\n'
            '## Native removal after normal-user deactivate\n```bash\n'+'\n'.join(removal)+'\n```\n'
            'Only then use rollback/uninstall, or Run Jarvis to return to original user services.\n')
    except BaseException:
        for path in output.iterdir():
            if path.is_file() and not path.is_symlink():path.unlink()
        output.rmdir();raise
    return output


def read_candidate(path,validate_source=True):
    info=json.loads(regular(path/'candidate.json',private=True,limit=16384))
    account=pwd.getpwuid(os.getuid())
    if (info.get('schema_version')!=1 or info.get('uid')!=os.getuid() or info.get('gid')!=os.getgid()
            or info.get('username')!=account.pw_name or info.get('home')!=account.pw_dir):
        raise ValueError('Candidate account does not match')
    units,rule,dropins=render(info['uid'],info['gid'],info['username'],info['home'],info['deployment'])
    if validate_source and info.get('source_sha256')!=source_hashes(Path(info['deployment'])):
        raise ValueError('Candidate source changed. Prepare/review a new candidate before activation')
    files={**units,f'90-jarvis-v4-{info["uid"]}.rules':rule,**{name+'.dropin':body for name,body in dropins.items()}}
    if info.get('sha256')!={name:hashlib.sha256(body.encode()).hexdigest() for name,body in files.items()}:
        raise ValueError('Candidate policy was changed')
    for name,body in files.items():
        if regular(path/name,private=True)!=body:raise ValueError('Candidate data was changed')
    return info,units,rule,dropins


def command(*args):
    result=subprocess.run(['/usr/bin/systemctl',*args],capture_output=True,text=True,timeout=25)
    if result.returncode:raise RuntimeError('Native service operation failed; inspect it locally')
    return result.stdout


def properties(scope,unit,*keys):
    return dict(line.split('=',1) for line in command(scope,'show',unit,'--property='+','.join(keys)).splitlines() if '=' in line)


def stopped():
    isolated=active()
    for name,part in LOGICAL.items():
        value=properties('--user',name,'LoadState','ActiveState','ExecStartPre','ExecStartPost','ExecStopPost')
        if value.get('LoadState')!='loaded':raise RuntimeError('Original voice unit unavailable')
        if any(value.get(key) for key in ('ExecStartPre','ExecStartPost','ExecStopPost')):
            raise RuntimeError('Custom service hooks need review before isolation')
        if isolated:value=properties('--system',f'jarvis-v4-{os.getuid()}-{part}.service','ActiveState')
        if value.get('ActiveState') not in {'inactive','failed'}:raise RuntimeError('Stop Jarvis before changing isolation')


def verify_native_units(info,units,directory=Path('/etc/systemd/system')):
    for name,body in units.items():
        if regular(directory/name,owner=0)!=body:raise RuntimeError('Reviewed native unit data is not installed')
        value=properties('--system',name,'LoadState','ActiveState','User','Group','DropInPaths')
        if (value.get('LoadState')!='loaded' or value.get('ActiveState') not in {'inactive','failed'}
                or value.get('User')!=str(info['uid']) or value.get('Group')!=str(info['gid']) or value.get('DropInPaths')):
            raise RuntimeError('Native unit identity, overrides or state needs review')


def verify_native_rule(uid,body):
    if uid!=os.getuid() or uid<=0:raise ValueError('Unexpected native account')
    path=f'/etc/polkit-1/rules.d/90-jarvis-v4-{uid}.rules'
    for name in ('sudo','stat','sha256sum'):
        tool=Path('/usr/bin')/name
        resolved=tool.resolve(strict=True)
        for part in (resolved,*resolved.parents,tool.parent):
            if part.stat().st_uid!=0 or part.stat().st_mode & 0o022:raise RuntimeError('Native verifier ownership needs review')
    prefix=['/usr/bin/sudo','-n','--']
    result=subprocess.run([*prefix,'/usr/bin/stat','--format=%u %f','--',path],capture_output=True,text=True,timeout=5)
    values=result.stdout.strip().split()
    if result.returncode or len(values)!=2 or values[0]!='0' or not re.fullmatch('[a-f0-9]+',values[1]):
        raise RuntimeError('Authorise native sudo in your own terminal. Python never reads a password.')
    mode=int(values[1],16)
    if not stat.S_ISREG(mode) or mode & 0o022:raise RuntimeError('Native rule type/permissions need review')
    result=subprocess.run([*prefix,'/usr/bin/sha256sum','--',path],capture_output=True,text=True,timeout=5)
    if result.returncode or result.stdout.split()[:1]!=[hashlib.sha256(body.encode()).hexdigest()]:
        raise RuntimeError('Native rule does not match reviewed data')


def owned_paths(dropins):
    return [Path.home()/'.config/systemd/user'/(unit+'.d')/DROPIN for unit in dropins]


def activate(candidate):
    info,units,rule,dropins=read_candidate(candidate)
    if active():raise ValueError('Isolation already activated')
    stopped();verify_native_units(info,units);verify_native_rule(info['uid'],rule)
    root=Path.home()/'.local/state/jarvis/isolation'
    if any(p.is_symlink() for p in (root,*root.parents)):raise ValueError('Isolation staging must be regular')
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    if root.stat().st_uid!=os.getuid() or root.stat().st_mode & 0o077:raise ValueError('Isolation staging must be private')
    receipt,session=root/'active.json',root/'session.env'
    paths=owned_paths(dropins)
    if any(p.exists() or p.is_symlink() for p in (receipt,session,*paths)):
        raise ValueError('Existing isolation-owned files need review')
    written=[]
    try:
        private_file(session,session_text());written.append(session)
        for path,body in zip(paths,dropins.values()):
            if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('User unit paths must be regular')
            path.parent.mkdir(parents=True,exist_ok=True)
            private_file(path,body);written.append(path)
        private_file(receipt,json.dumps({'schema_version':1,'uid':os.getuid(),'backend':'system-manager-v1','actual_egress_verified':False})+'\n')
        written.append(receipt);command('--user','daemon-reload')
    except BaseException:
        for path in reversed(written):path.unlink()
        command('--user','daemon-reload');raise


def deactivate(candidate):
    # Recovery validates account and exact owned policy data even when worker
    # source is unavailable. Activation also validates current source identities.
    _,units,_,dropins=read_candidate(candidate,validate_source=False)
    if not active():raise ValueError('No active isolation receipt')
    stopped()
    for name in units:
        if properties('--system',name,'ActiveState').get('ActiveState') not in {'inactive','failed'}:
            raise RuntimeError('Stop all native workers before removing isolation')
    paths=owned_paths(dropins)
    for path,body in zip(paths,dropins.values()):
        if regular(path,private=True)!=body:raise ValueError('Changed isolation drop-in needs review')
    receipt=Path.home()/'.local/state/jarvis/isolation/active.json';session=receipt.with_name('session.env')
    receipt_text=regular(receipt,private=True);session_value=regular(session,private=True)
    # Relays can remain active after their physical workers stop. Clear them
    # before restoring the original normal-service type.
    command('--user','stop',*reversed(LOGICAL))
    removed=[]
    try:
        for path,body in [*zip(paths,dropins.values()),(receipt,receipt_text),(session,session_value)]:
            path.unlink();removed.append((path,body))
        command('--user','daemon-reload')
    except BaseException:
        for path,body in removed:private_file(path,body)
        command('--user','daemon-reload');raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','activate','deactivate'))
    parser.add_argument('--output',type=Path);parser.add_argument('--candidate',type=Path)
    parser.add_argument('--deployment',type=Path,default=Path.home()/'.local/src/ovos-skill-jarvis-dispatcher')
    args=parser.parse_args()
    if os.getuid()<=0 or os.getuid()!=os.geteuid() or os.getgid()!=os.getegid():parser.error('Never sudo Python; use the ordinary desktop account')
    if args.action=='prepare':
        if args.candidate:parser.error('prepare needs a new output, not --candidate')
        output=args.output or Path.home()/'.local/state/jarvis/isolation-candidates'/secrets.token_hex(8)
        print(prepare(output,args.deployment));return
    if not args.candidate or args.output:parser.error('Use the exact reviewed --candidate directory')
    from control_runtime import operation_lock
    with operation_lock():
        (activate if args.action=='activate' else deactivate)(args.candidate)
    print('Isolation mapping changed with voice stopped. Settings unchanged. Live acceptance remains pending.')


if __name__=='__main__':main()
