"""Bounded login preferences for the existing OVOS target and quiet tray."""
import configparser
import json
import os
from pathlib import Path
import subprocess
import tempfile

TARGET='ovos.service'


def command(*args):
    return subprocess.run(['systemctl','--user',*args],capture_output=True,text=True,timeout=20)


def read_file(path):
    if any(item.is_symlink() for item in (path,*path.parents)):
        raise RuntimeError('Startup path is a symbolic link; review it first.')
    if not path.exists():return None
    if path.stat().st_uid!=os.getuid() or path.stat().st_size>65536:
        raise RuntimeError('Startup file needs ownership or size review.')
    return path.read_text()


def preference(home=None):
    raw=read_file(Path(home or Path.home())/'.config/jarvis/startup.json')
    if raw is None:return None
    value=json.loads(raw)
    if not isinstance(value,dict):raise RuntimeError('Saved auto-start preference is invalid.')
    enabled=value.get('enabled')
    if type(enabled) is not bool:raise RuntimeError('Saved auto-start preference is invalid.')
    return enabled


def inspect(home=None):
    home=Path(home or Path.home())
    result=command('is-enabled',TARGET)
    state=result.stdout.strip()
    enabled=state=='enabled'
    path=home/'.config/autostart/ovos-tray.desktop'
    raw=read_file(path)
    tray=False
    if raw:
        config=configparser.ConfigParser(interpolation=None,strict=True)
        config.read_string(raw)
        entry=config['Desktop Entry']
        tray=entry.get('Hidden','false').lower()!='true' and entry.get('X-GNOME-Autostart-enabled','true').lower()!='false'
    saved=preference(home)
    return {'enabled':enabled and tray,'voice_enabled':enabled,'tray_enabled':tray,
            'target_state':state if state in {'enabled','enabled-runtime','disabled','static','masked','not-found','indirect'} else 'unknown',
            'preference':saved,'consistent':saved is None or (saved==enabled and saved==tray)}


def write_file(path,text,mode):
    if any(item.is_symlink() for item in (path,*path.parents)):
        raise RuntimeError('Startup settings must use regular user-owned paths.')
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.jarvis-startup-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:
            stream.write(text);stream.flush();os.fsync(stream.fileno())
        os.chmod(name,mode);os.replace(name,path)
    finally:
        Path(name).unlink(missing_ok=True)


def tray_text(home,enabled,previous=None):
    if previous:
        config=configparser.ConfigParser(interpolation=None,strict=True)
        config.read_string(previous)
        entry=config['Desktop Entry']
        if (entry.get('Name')!='Jarvis Voice Controls'
                or entry.get('Exec') not in {str(home/'.local/bin/ovos-tray'), str(home/'.local/bin/ovos-tray')+' --login'}):
            raise RuntimeError('The existing tray launcher is customised; review it first.')
        lines=[];in_entry=False;written=False
        flags=[f'Hidden={str(not enabled).lower()}',f'X-GNOME-Autostart-enabled={str(enabled).lower()}']
        for line in previous.splitlines():
            if line.strip().startswith('['):
                if in_entry and not written:lines.extend(flags);written=True
                in_entry=line.strip()=='[Desktop Entry]'
            if in_entry and line.split('=',1)[0].strip() in {'Hidden','X-GNOME-Autostart-enabled'}:continue
            if in_entry and line.startswith('Exec='):
                line='Exec='+str(home/'.local/bin/ovos-tray')+' --login'
            lines.append(line)
        if not written:lines.extend(flags)
        return '\n'.join(lines)+'\n'
    else:
        lines=['[Desktop Entry]','Type=Application','Name=Jarvis Voice Controls',
               'Exec='+str(home/'.local/bin/ovos-tray')+' --login','TryExec='+str(home/'.local/bin/ovos-tray'),
               'Terminal=false','X-GNOME-Autostart-Delay=5']
    return '\n'.join(lines)+f'\nHidden={str(not enabled).lower()}\nX-GNOME-Autostart-enabled={str(enabled).lower()}\n'


def set_enabled(enabled,home=None):
    if type(enabled) is not bool:raise ValueError('Auto-start must be on or off.')
    home=Path(home or Path.home())
    before=inspect(home)
    if before['target_state'] not in {'enabled','disabled'}:
        raise RuntimeError('OVOS login target is unavailable, masked or not installable; review it first.')
    tray=home/'.config/autostart/ovos-tray.desktop'
    settings=home/'.config/jarvis/startup.json'
    previous_tray,previous_settings=read_file(tray),read_file(settings)
    text=tray_text(home,enabled,previous_tray)
    try:
        result=command('enable' if enabled else 'disable',TARGET)
        if result.returncode:
            raise RuntimeError('Could not change the OVOS login target. Current running services were left alone.')
        write_file(tray,text,0o644)
        saved=json.loads(previous_settings) if previous_settings else {'schema_version':1}
        saved['enabled']=enabled
        write_file(settings,json.dumps(saved,indent=2)+'\n',0o600)
        after=inspect(home)
        if after['voice_enabled']!=enabled or after['tray_enabled']!=enabled:
            raise RuntimeError('Auto-start state did not match the requested setting.')
    except Exception:
        recovery=command('enable' if before['voice_enabled'] else 'disable',TARGET)
        for path,original,mode in ((tray,previous_tray,0o644),(settings,previous_settings,0o600)):
            if original is None:path.unlink(missing_ok=True)
            else:write_file(path,original,mode)
        if recovery.returncode:raise RuntimeError('Auto-start change failed; restoring the login target also needs attention.')
        raise
    return 'Auto-start at login is on. The tray opens quietly.' if enabled else 'Auto-start at login is off. Current running services were left alone.'


def start_at_login(home=None):
    """One explicit login request, never a polling restart or manual-tray action."""
    home=Path(home or Path.home())
    settings=inspect(home)
    if settings['preference'] is False or not settings['enabled']:
        return 'Auto-start is off.'
    from control_runtime import UNITS
    from isolation_services import active as isolation_active,refresh_session,state_arguments,physical
    isolated=isolation_active(home)
    refresh_session(home)
    states=[]
    for unit in UNITS:
        result=command('show',unit,'--property=LoadState,ActiveState')
        props=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
        if result.returncode or props.get('LoadState')!='loaded':
            raise RuntimeError('Login voice unit is unavailable. Use Run Jarvis to inspect it.')
        if isolated:
            result=subprocess.run(state_arguments(unit,'LoadState','ActiveState'),capture_output=True,text=True,timeout=20)
            props=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
            if result.returncode or props.get('LoadState')!='loaded':raise RuntimeError('Protected login worker is unavailable')
        states.append(props.get('ActiveState'))
    if any(state not in {'inactive','failed'} for state in states):
        return 'Running or muted voice system left alone.'
    if isolated:
        result=command('start','--no-block',TARGET)
        if result.returncode:raise RuntimeError('Login coordinator unavailable')
        result=subprocess.run(['systemctl','--system','start','--no-block','--no-ask-password',
                               *[physical(unit)[1] for unit in UNITS]],capture_output=True,text=True,timeout=20)
    else:result=command('start','--no-block',*UNITS)
    if result.returncode:
        raise RuntimeError('Login start request failed. Use Run Jarvis to retry.')
    return 'Login voice start requested once.'
