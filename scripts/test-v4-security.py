#!/usr/bin/env python3
"""Failure-focused V4 checks; no desktop input, network or live deployment."""
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

sys.modules.setdefault('ovos_bus_client', types.SimpleNamespace(Message=types.SimpleNamespace))
editing = load('editing', 'ovos_skill_jarvis_dispatcher/text_editing.py')
helpers = load('helpers', 'ovos_skill_jarvis_dispatcher/helpers.py')
controls = load('controls', 'ovos_skill_jarvis_dispatcher/system_controls.py')
report = load('report', 'scripts/create_ai_report.py')
update = load('update', 'scripts/update.py')
desktop = load('desktop', 'ovos_skill_jarvis_dispatcher/desktop.py')

class Skill(editing.TextEditingActionsMixin, helpers.DispatcherHelpersMixin,
            controls.SystemControlsMixin, desktop.DesktopActionsMixin):
    def __init__(self, identity='"editor", "Editor"'):
        self.identity = identity
        self.spoken = []
        self.log = Mock()
        self.focus = [('123', identity)]
        self._desktop_app_display_names = {'zoom':'Zoom'}
        self._desktop_app_integrations = {'zoom':'zoom'}
    def speak(self, value): self.spoken.append(value)
    def _focused_window_details(self):
        return self.focus.pop(0) if len(self.focus)>1 else self.focus[0]

identities = ['Gnome-terminal','konsole','xterm','kitty','Alacritty','foot',
              'org.wezfurlong.wezterm','com.gexperts.Tilix','com.mitchellh.ghostty']
for name in identities:
    skill = Skill(f'WM_CLASS(STRING) = "{name}", "{name.upper()}"')
    with patch.object(helpers.subprocess, 'run', return_value=types.SimpleNamespace(stdout=skill.identity)) as run:
        skill._type_into_window('123', 'echo unsafe', True)
        assert len(run.call_args_list)==1 and 'xprop' in run.call_args.args[0][0]
        run.reset_mock()
        for operation in (skill._press_enter, skill._insert_new_line, skill._insert_period,
                          skill._press_space, lambda:skill._type_focused_text('unsafe')):
            operation()
        assert not run.called and skill.spoken[-1]=='Terminal input is blocked.'

skill=Skill()
with patch.object(helpers.subprocess,'run',return_value=types.SimpleNamespace(stdout=skill.identity)) as run:
    skill._type_into_window('123','-literal',True)
    commands=[call.args[0] for call in run.call_args_list]
    assert any(command[-2:]==['--','-literal'] for command in commands)
    assert any(command[-1]=='Return' for command in commands)

for focus in ([('999','"editor"')], [('123','"editor"'),('999','"editor"')],
              [('123','"editor"'),('123','"editor"'),('999','"editor"')]):
    skill=Skill();skill.focus=list(focus)
    with patch.object(helpers.subprocess,'run',return_value=types.SimpleNamespace(stdout=skill.identity)) as run:
        skill._type_into_window('123','text',True)
        assert not any(call.args[0][-1]=='Return' for call in run.call_args_list)
        if len(focus)<3:
            assert not any('type' in call.args[0] for call in run.call_args_list)

fixtures = [
    '{"api_key": "fixture-api", "client_secret": "fixture-client", "token": "fixture-token"}',
    'token=fixture-query password=fixture-pass pwd=fixture-pwd Bearer fixture-bearer',
    'Authorization: Bearer fixture-header\nAuthorization: Basic fixture-basic',
    'https://fixture-user:fixture-credential@example.org/path',
    '{"location": {\n "city": {"name": "fixture-city"}, "latitude": 12.345\n}}',
    'host fixture-host ip 192.0.2.100 [2001:db8::12] ::1',
]
with patch.object(report.platform,'node',return_value='fixture-host'):
    for fixture in fixtures:
        clean=report.sanitise(fixture,Path('/home/fixture-user'))
        for secret in ['fixture-api','fixture-client','fixture-token','fixture-query',
                       'fixture-pass','fixture-pwd','fixture-bearer','fixture-credential',
                       'fixture-header','fixture-basic',
                       'fixture-city','fixture-host','192.0.2.100','2001:db8::12','::1']:
            assert secret not in clean,(secret,clean)
    clean=report.sanitise(fixtures[0],Path('/home/example'))
    assert json.loads(clean)['token']=='<redacted>'

with tempfile.TemporaryDirectory() as directory:
    root=Path(directory);bundle=root/'bundle';bundle.mkdir();(bundle/'data').write_text('safe')
    output=root/'report.tar.gz'
    old_umask=os.umask(0)
    try: report.publish_private_archive(bundle,output)
    finally: os.umask(old_umask)
    assert stat.S_IMODE(output.stat().st_mode)==0o600
    before=output.read_bytes()
    try: report.publish_private_archive(bundle,output)
    except FileExistsError: pass
    else: raise AssertionError('Report overwrite allowed')
    assert output.read_bytes()==before and not list(root.glob('.jarvis-report-*'))
    target=root/'target';target.write_text('keep');link=root/'link';link.symlink_to(target)
    try: report.publish_private_archive(bundle,link)
    except FileExistsError: pass
    else: raise AssertionError('Report symlink overwrite allowed')
    assert target.read_text()=='keep'

with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{'JARVIS_HOME':directory}):
    release={'version':update.VERSION,'release_date':'2026-09-29'}
    with patch.object(update,'latest_release',return_value=release):
        assert update.check(quiet=True)[1] is False
    state=Path(directory)/'.local/state/jarvis/updates/latest.json'
    assert json.loads(state.read_text())['check_succeeded'] is True
    with patch.object(update,'latest_release',side_effect=RuntimeError('offline')):
        try:update.check(quiet=True)
        except RuntimeError:pass
        else:raise AssertionError('Failed update check reported success')
    assert json.loads(state.read_text())['check_succeeded'] is False

for url in ['http://github.com/x','https://github.com.evil.invalid/x',
            'https://user:password@github.com/x','https://github.com:8443/x',
            'file:///tmp/release','https://evil.invalid/x','https://github.com/x#fragment']:
    try: update.validate_update_url(url)
    except (RuntimeError,ValueError): pass
    else: raise AssertionError('Untrusted update URL allowed')
for host in update.UPDATE_HOSTS: update.validate_update_url('https://'+host+'/path')
handler=update.UpdateRedirectHandler()
try: handler.redirect_request(None,None,302,'',{},'http://github.com/downgrade')
except RuntimeError: pass
else: raise AssertionError('Redirect downgrade allowed')

skill=Skill()
with patch.object(desktop.subprocess,'run',side_effect=subprocess.CalledProcessError(24,'helper')):
    assert skill._run_desktop_app_action('zoom','open') is False
    assert 'running in the tray' in skill.spoken[-1] and not skill.log.exception.called

print('PASS: V4 terminal/focus guards, report privacy/atomicity, transport and Zoom state')
