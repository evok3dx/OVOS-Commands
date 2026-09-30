#!/usr/bin/env python3
"""Login controls do not start/stop services and recover failed preference writes."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('startup',ROOT/'scripts/startup_settings.py')
startup=importlib.util.module_from_spec(spec);spec.loader.exec_module(startup)

with tempfile.TemporaryDirectory() as directory:
    home=Path(directory)
    state={'enabled':False};calls=[]
    def command(*args):
        calls.append(args)
        assert args[0] not in {'start','stop','restart','unmask'}
        assert args[-1]=='ovos.service'
        if args[0]=='is-enabled':return subprocess.CompletedProcess(args,0 if state['enabled'] else 1,'enabled\n' if state['enabled'] else 'disabled\n','')
        state['enabled']=args[0]=='enable'
        return subprocess.CompletedProcess(args,0,'','')
    with patch.object(startup,'command',command):
        assert not startup.inspect(home)['enabled']
        startup.set_enabled(True,home)
        assert startup.inspect(home)['enabled']
        tray=home/'.config/autostart/ovos-tray.desktop'
        assert '--gui' not in tray.read_text()
        settings=home/'.config/jarvis/startup.json'
        value=json.loads(settings.read_text());value['future_setting']={'keep':True}
        settings.write_text(json.dumps(value))
        startup.set_enabled(False,home)
        assert not startup.inspect(home)['enabled']
        assert json.loads(settings.read_text())['future_setting']=={'keep':True}
        assert settings.stat().st_mode & 0o777==0o600
        before=tray.read_text(),settings.read_text()
        original=startup.write_file
        def fail(path,text,mode):
            if path==settings and json.loads(text)['enabled'] is True:
                raise OSError('Injected preference-write failure')
            original(path,text,mode)
        with patch.object(startup,'write_file',fail):
            try:startup.set_enabled(True,home)
            except OSError:pass
            else:raise AssertionError('Failed write reported success')
        assert not state['enabled']
        assert (tray.read_text(),settings.read_text())==before
        settings.unlink();settings.symlink_to(tray)
        count=len(calls)
        try:startup.set_enabled(True,home)
        except RuntimeError:pass
        else:raise AssertionError('Symlink preference accepted')
        assert not state['enabled'] and len(calls)==count+1 # only read-only is-enabled
        settings.unlink();settings.write_text('[]')
        count=len(calls)
        try:startup.set_enabled(True,home)
        except RuntimeError:pass
        else:raise AssertionError('Invalid preference accepted')
        assert not state['enabled'] and len(calls)==count+1
        settings.write_text(before[1])
        tray.write_text(before[0]+'\n[Desktop Action Review]\nName=Keep me\nExec=/usr/bin/true\n')
        startup.set_enabled(True,home)
        config=startup.configparser.ConfigParser(interpolation=None)
        config.read_string(tray.read_text())
        assert config['Desktop Entry']['Hidden']=='false'
        assert config['Desktop Action Review']['Name']=='Keep me'
        assert 'Hidden' not in config['Desktop Action Review']
        startup.set_enabled(False,home)
        original_command=command
        def partial_failure(*args):
            result=original_command(*args)
            if args[0]=='enable':return subprocess.CompletedProcess(args,1,'','Injected partial failure')
            return result
        with patch.object(startup,'command',partial_failure):
            try:startup.set_enabled(True,home)
            except RuntimeError:pass
            else:raise AssertionError('Partial systemctl failure reported success')
        assert not state['enabled'] and not startup.inspect(home)['enabled']

        # Every combination is intentional; neither toggle changes the other.
        for tray_value,voice_value in ((True,False),(False,True),(True,True),(False,False)):
            startup.set_options(home,tray_enabled=tray_value,voice_enabled=voice_value)
            value=startup.inspect(home)
            assert value['tray_enabled']==tray_value and value['voice_enabled']==voice_value and value['consistent']
            saved=json.loads(settings.read_text())
            assert saved['future_setting']=={'keep':True}
            assert saved['tray_enabled']==tray_value and saved['voice_enabled']==voice_value
            assert startup.preference(home,component='tray')==tray_value
            assert startup.preference(home,component='voice')==voice_value
            assert '--start-voice-at-login' in (home/'.config/autostart/jarvis-voice.desktop').read_text()
        count=len(calls)
        startup.set_options(home,tray_enabled=True)
        assert startup.inspect(home)['tray_enabled'] and not state['enabled']
        assert all(args[0]=='is-enabled' for args in calls[count:])
        before=(tray.read_text(),settings.read_text(),(home/'.config/autostart/jarvis-voice.desktop').read_text())
        with patch.object(startup,'write_file',side_effect=OSError('Injected independent write failure')):
            try:startup.set_options(home,voice_enabled=True)
            except OSError:pass
            else:raise AssertionError('Failed independent setting accepted')
        assert not state['enabled']
        assert before==(tray.read_text(),settings.read_text(),(home/'.config/autostart/jarvis-voice.desktop').read_text())

with tempfile.TemporaryDirectory() as directory:
    home=Path(directory)
    for mode in ('off','tray-only','voice-only','stopped','muted','starting','missing','failed-request'):
        requests=[]
        state={'enabled':mode!='off','preference':False if mode=='off' else True}
        if mode in {'tray-only','voice-only'}:
            state.update(voice_enabled=mode=='voice-only',voice_preference=mode=='voice-only',
                         tray_enabled=mode=='tray-only',enabled=False,preference=False)
        def login_command(*args):
            requests.append(args)
            if args[0]=='show':
                live='inactive' if mode in {'stopped','off','tray-only','voice-only','failed-request','missing'} else 'active'
                if mode=='muted' and args[1]=='ovos-listener.service':live='inactive'
                if mode=='starting':live='activating'
                return subprocess.CompletedProcess(args,0,'LoadState='+('not-found' if mode=='missing' else 'loaded')+'\nActiveState='+live+'\n','')
            assert args==('start','--no-block','ovos-audio.service','ovos-listener.service','ovos-core.service')
            return subprocess.CompletedProcess(args,1 if mode=='failed-request' else 0,'','')
        with patch.object(startup,'inspect',return_value=state),patch.object(startup,'command',login_command):
            if mode in {'missing','failed-request'}:
                try:startup.start_at_login(home)
                except RuntimeError:pass
                else:raise AssertionError('Unsafe login request reported success')
            else:startup.start_at_login(home)
        mutations=[args for args in requests if args[0]=='start']
        assert len(mutations)==(1 if mode in {'stopped','voice-only','failed-request'} else 0)

print('PASS: quiet login, one-shot/off/mute guards, unknown-field preservation and failure recovery')
