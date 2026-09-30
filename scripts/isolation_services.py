"""Fixed service mapping for an explicitly activated V4 candidate.

A receipt selects a service manager. It is never enforcement evidence.
"""
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

LOGICAL = {'ovos-core.service':'core', 'ovos-listener.service':'listener', 'ovos-audio.service':'audio'}
COMPONENTS = (*LOGICAL.values(), 'weather', 'media')


def regular(path, private=False, owner=None, limit=65536):
    if any(item.is_symlink() for item in (path,*path.parents)):
        raise ValueError('Isolation path must be regular')
    info=path.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_size>limit
            or info.st_uid!=(os.getuid() if owner is None else owner)
            or info.st_mode & (0o077 if private else 0o022)):
        raise ValueError('Isolation file ownership, privacy or type needs review')
    return path.read_text()


def active(home=None):
    path=Path(home or Path.home())/'.local/state/jarvis/isolation/active.json'
    if not path.exists() and not path.is_symlink():return False
    value=json.loads(regular(path,private=True,limit=8192))
    if value!={'schema_version':1,'uid':os.getuid(),'backend':'system-manager-v1','actual_egress_verified':False}:
        raise RuntimeError('Isolation receipt needs review')
    return True


def physical(unit,home=None):
    if unit not in LOGICAL:raise ValueError('Unknown isolation unit')
    return ('--system',f'jarvis-v4-{os.getuid()}-{LOGICAL[unit]}.service') if active(home) else ('--user',unit)


def state_arguments(unit,*properties):
    scope,name=physical(unit)
    return ['systemctl',scope,'show',name,'--property='+','.join(properties)]


def journal_arguments(unit,invocation):
    scope,name=physical(unit)
    # Let journalctl include every journal the ordinary user can read for
    # system workers. --system alone can hide that user's split journal.
    return ['journalctl',*(['--user'] if scope=='--user' else []),'-u',name,
            '_SYSTEMD_INVOCATION_ID='+invocation,'--no-pager','-o','cat']


def control_arguments(arguments):
    args=[str(arg) for arg in arguments]
    if (len(args)>=4 and args[:2]==['systemctl','--user'] and args[2] in {'start','stop','restart'}
            and all(unit in LOGICAL for unit in args[3:]) and active()):
        return ['systemctl','--system',args[2],'--no-ask-password',*[physical(unit)[1] for unit in args[3:]]]
    return args


def session_text():
    display=os.environ.get('DISPLAY','')
    if not re.fullmatch(r':[0-9]{1,3}(?:\.[0-9]{1,2})?',display):
        raise RuntimeError('Use the local X11 desktop session for isolation controls')
    values={'DISPLAY':display}
    authority=os.environ.get('XAUTHORITY')
    if authority:
        if not Path(authority).is_absolute() or len(authority)>1024 or any(ord(c)<32 or ord(c)==127 for c in authority):
            raise ValueError('Desktop authentication path needs review')
        values['XAUTHORITY']=authority
    return ''.join(key+'='+json.dumps(value,ensure_ascii=False)+'\n' for key,value in values.items())


def refresh_session(home=None):
    if not active(home):return
    path=Path(home or Path.home())/'.local/state/jarvis/isolation/session.env'
    regular(path,private=True)
    content=session_text()
    fd,name=tempfile.mkstemp(prefix='.session-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:
            stream.write(content);stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:Path(name).unlink(missing_ok=True)


def native_workers_absent():
    """Read system-manager state without authentication or any service control.

    A hidden rule is not assumed absent. With no installed or loaded target
    workers it cannot authorise execution of the code being updated. Inspect
    stale rules separately when preparing native isolation, never via sudo here.
    """
    uid=os.getuid()
    if uid<=0:raise RuntimeError('Deployment requires the normal desktop user')
    names={f'jarvis-v4-{uid}-{part}.service' for part in COMPONENTS}
    tool=Path('/usr/bin/systemctl')
    resolved=tool.resolve(strict=True)
    for part in (resolved,*resolved.parents,tool.parent):
        info=part.stat()
        if info.st_uid!=0 or info.st_mode & 0o022:
            raise RuntimeError('Native state reader ownership needs review')
    try:
        result=subprocess.run([str(tool),'--system','--no-pager','--no-ask-password','show','--all',
                              '--property=Id,LoadState,ActiveState,FragmentPath,DropInPaths','--',*sorted(names)],
                              capture_output=True,text=True,timeout=5,
                              env={**os.environ,'LC_ALL':'C','LANG':'C'})
    except (OSError,subprocess.TimeoutExpired):
        raise RuntimeError('Native worker state unavailable; deployment remains blocked.') from None
    if result.returncode or result.stderr or len(result.stdout)>32768:
        raise RuntimeError('Cannot verify native worker state; deployment remains blocked.')
    observed=set()
    for block in result.stdout.strip().split('\n\n'):
        pairs=[line.partition('=') for line in block.splitlines()]
        keys=[key for key,separator,value in pairs]
        if (len(keys)!=5 or len(set(keys))!=5 or any(not separator for key,separator,value in pairs)
                or set(keys)!={'Id','LoadState','ActiveState','FragmentPath','DropInPaths'}):
            raise RuntimeError('Incomplete native worker state; deployment remains blocked.')
        properties={key:value for key,separator,value in pairs}
        name=properties['Id']
        if name not in names or name in observed:
            raise RuntimeError('Unexpected native worker identity; deployment remains blocked.')
        observed.add(name)
        if (properties['LoadState']!='not-found' or properties['ActiveState']!='inactive'
                or properties['FragmentPath'] or properties['DropInPaths']):
            raise RuntimeError('Remove the reviewed native isolation workers before deployment.')
    if observed!=names:
        raise RuntimeError('Missing native worker state; deployment remains blocked.')
    return True


def native_policy_present(path,protected_rule=None):
    try:
        path.lstat()
        return True  # Includes dangling symlinks; do not infer removal from a missing target.
    except FileNotFoundError:
        return False
    except PermissionError:
        if path==protected_rule:
            native_workers_absent()
            return False  # Hidden rule uninspected; its fixed target workers are verified absent.
        raise RuntimeError('Cannot inspect native isolation policy. Review its removal in the owner terminal before deployment.') from None


def guard_deployment(operation,home):
    if operation not in {'install','rollback','uninstall'}:raise ValueError('Unknown deployment operation')
    if active(home):
        raise RuntimeError('Stop Jarvis and deactivate isolation before install, rollback or uninstall.')
    if operation in {'install','rollback','uninstall'}:
        native=Path('/etc')
        if os.environ.get('JARVIS_TEST_MODE')=='1':
            home=Path(home)
            if (home.resolve()==Path.home().resolve() or home.stat().st_uid!=os.getuid()
                    or any(path.is_symlink() for path in (home,*home.parents))):
                raise RuntimeError('Deployment fixtures require a separate regular user-owned home')
            # Test-mode installs do not touch real services. Inspect their own
            # native-policy fixtures rather than the runner's protected /etc.
            native=home/'.local/state/jarvis/test-native'
        paths=[native/'systemd/system'/f'jarvis-v4-{os.getuid()}-{part}.service' for part in COMPONENTS]
        rule=native/'polkit-1/rules.d'/f'90-jarvis-v4-{os.getuid()}.rules'
        paths.append(rule)
        paths.append(native/'systemd/system/ollama.service.d/90-jarvis-isolation.conf')
        protected_rule=rule if native==Path('/etc') else None
        remaining=any(native_policy_present(path,protected_rule) for path in paths)
        if remaining:
            raise RuntimeError('Remove the reviewed native isolation files before install, rollback or uninstall.')


if __name__=='__main__':
    import sys
    try:
        if len(sys.argv)!=3 or sys.argv[1] not in {'--guard-install','--guard-rollback','--guard-uninstall'}:
            raise ValueError('Unknown isolation operation')
        guard_deployment(sys.argv[1].removeprefix('--guard-'),Path(sys.argv[2]))
    except (OSError,ValueError,RuntimeError) as error:
        print(str(error),file=sys.stderr);raise SystemExit(2)
