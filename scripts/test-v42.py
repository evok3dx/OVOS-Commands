#!/usr/bin/env python3
"""Failure regressions for private appearance, result activity and Notes/Mail."""
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from unittest.mock import Mock, patch
import time

if os.getuid() == 0:
    raise RuntimeError('Run tests as the ordinary user')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import appearance_settings as appearance
import private_reports as reports
import isolation_check as isolation


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rejected(call):
    try:
        call()
    except (OSError, ValueError, RuntimeError):
        return
    raise AssertionError('Unsafe input was accepted')


activity = load('activity_fixture', 'ovos_skill_jarvis_dispatcher/activity.py')
feed = activity.ActivityLog()
for _ in range(100):
    feed.record('application.open', True, 'firefox')
feed.record('reading.selection', False)
feed.record('private query text', True, 'private title')
feed.record('application.open', True, 'private title')
snapshot = feed.snapshot()
assert len(snapshot['rows']) == 32
assert 'private' not in json.dumps(snapshot)
rows = activity.display_rows(snapshot)
assert rows[0][0] == 'Opened an application'
assert rows[1][2] is False
assert rows[2][0] == 'Opened Firefox'
framed=activity.FRAME+json.dumps(snapshot)+'\n'
assert activity.display_output('Background diagnostic\n'+framed+'Another diagnostic\n')==rows
rejected(lambda:activity.display_output(framed+framed))
rejected(lambda:activity.display_output('No snapshot was received'))
rejected(lambda:activity.display_output('x'*65537))
rejected(lambda:activity.display_output(activity.FRAME+'{}'))
rejected(lambda: activity.display_rows({'schema_version': 1, 'rows': [{'action': 'raw private text', 'success': True, 'time': '12:00'}]}))
rejected(lambda: activity.display_rows({'schema_version': 1, 'rows': [{'action': 'notes.new', 'success': True, 'time': '99:00'}]}))
feed.clear();assert feed.snapshot()['rows'] == []
with patch.object(activity.time,'monotonic',return_value=0):feed.record('notes.new')
with patch.object(activity.time,'monotonic',return_value=299):assert len(feed.snapshot()['rows'])==1
with patch.object(activity.time,'monotonic',return_value=300):assert feed.snapshot()['rows']==[]

with tempfile.TemporaryDirectory() as directory:
    home = Path(directory)
    path = home / '.config/jarvis/appearance.json'
    path.parent.mkdir(parents=True)
    path.write_text('{"theme":"light","future":{"keep":true}}')
    with patch.object(subprocess, 'run', side_effect=AssertionError('Appearance called a service')):
        assert appearance.save('dark', home) == 'dark'
        assert appearance.theme(home) == 'dark'
    assert json.loads(path.read_text())['future'] == {'keep': True}
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    rejected(lambda: appearance.save('anything else', home))
    path.unlink();path.symlink_to(home / 'other')
    rejected(lambda: appearance.save('light', home))
    stamp = datetime(2026, 1, 2, 3, 4, 5)
    first = reports.new_directory(home / 'Downloads', 'Jarvis-Isolation-Check', stamp)
    second = reports.new_directory(home / 'Downloads', 'Jarvis-Isolation-Check', stamp)
    assert first.name == 'Jarvis-Isolation-Check-2026-01-02_03-04-05'
    assert second.name == first.name + '-02'
    assert stat.S_IMODE(first.stat().st_mode) == 0o700
    link = home / 'linked';link.symlink_to(home / 'Downloads')
    rejected(lambda: reports.new_directory(link, 'Jarvis-Isolation-Check'))
    rejected(lambda: reports.new_directory(home, '../private'))

profile = load('preferred_fixture', 'ovos_skill_jarvis_dispatcher/profile.py')
for categories in (['Office', 'Network'], ['Office', 'Network', 'Email']):
    app = {'integration': 'desktop_' + 'a' * 24, 'display_name': 'ElectronMail',
           'menu_categories': categories}
    apps = {'desktop_' + 'a' * 24: app}
    assert profile.preferred_app_candidates(apps, 'mail') == list(apps)
    assert profile.preferred_app_candidates(apps, 'office') == []

desktop = load('desktop_fixture', 'ovos_skill_jarvis_dispatcher/desktop.py')
notes = load('notes_fixture', 'ovos_skill_jarvis_dispatcher/integrations/standard_notes.py')

for signature,expected in ((('standard notes','Standard Notes'),True),
                           (('standard-notes','StandardNotes'),True),
                           (('standardnotes','standardnotes'),True),
                           (('org.standardnotes.standardnotes','org.standardnotes.standardnotes'),True),
                           (('fake-standard-notes','Other'),False),
                           (('standard','Other'),False)):
    with patch.object(notes.subprocess,'run',side_effect=[Mock(stdout='123'),
         Mock(stdout='WM_CLASS(STRING) = "'+signature[0]+'", "'+signature[1]+'"\n')]):
        assert notes.StandardNotesIntegrationMixin._standard_notes_is_focused() is expected


class Notes(notes.StandardNotesIntegrationMixin, desktop.DesktopActionsMixin):
    def __init__(self):
        self.log = Mock();self.speak = Mock();self._jarvis_activity = activity.ActivityLog()
        self._jarvis_profile = {'applications': {'notes': {'integration': 'standard_notes'}}}
        self._desktop_app_integrations = {'notes': 'standard_notes'}
        self._desktop_app_display_names = {'notes': 'Notes'}
        self._focused_window_details = Mock(return_value=('123', 'standard notes'))
        self._send_focused_keys = Mock();self._type_focused_text = Mock()
        self._cancelled_search = lambda value: value is None
        self.get_response = Mock(return_value='query only in application')


for method in ('_create_new_note', '_search_standard_notes'):
    skill = Notes()
    with patch.object(skill, '_run_desktop_app_action', return_value=False), patch.object(notes.subprocess, 'run') as keys:
        getattr(skill, method)()
        keys.assert_not_called()
        skill._type_focused_text.assert_not_called()
        skill.speak.assert_called_once_with("That didn't work.")
    skill = Notes()
    with patch.object(skill, '_run_desktop_app_action', return_value=True), \
         patch.object(skill, '_standard_notes_is_focused', return_value=False), \
         patch.object(notes.time, 'sleep'), patch.object(notes.subprocess, 'run') as keys:
        getattr(skill, method)()
        keys.assert_not_called()
        skill._type_focused_text.assert_not_called()

skill = Notes()
with patch.object(skill, '_run_desktop_app_action', return_value=True), \
     patch.object(skill, '_standard_notes_is_focused', return_value=True), \
     patch.object(notes.time, 'sleep'), patch.object(notes.subprocess, 'run') as keys:
    skill._create_new_note()
    assert keys.call_args.args[0][-1] == 'alt+shift+n'
    assert activity.display_rows(skill._jarvis_activity.snapshot())[0][0] == 'Created a new note'
    skill._search_standard_notes()
    skill._send_focused_keys.assert_called_once_with('ctrl+shift+colon')
    skill._type_focused_text.assert_called_once_with('query only in application')
    assert 'query only' not in json.dumps(skill._jarvis_activity.snapshot())

skill = Notes();skill._focused_window_details.side_effect = [('123', 'notes'), ('124', 'other')]
with patch.object(skill, '_run_desktop_app_action', return_value=True), \
     patch.object(skill, '_standard_notes_is_focused', return_value=True), patch.object(notes.time, 'sleep'):
    skill._search_standard_notes();skill._type_focused_text.assert_not_called()

props = {'ActiveState': 'active', 'MainPID': '123'}
policy = {'LoadState': 'loaded', 'User': str(os.getuid()), 'NoNewPrivileges': 'yes',
          'IPAddressDeny': '::/0 0.0.0.0/0', 'IPAddressAllow': '::1/128 127.0.0.1/32'}
with patch.object(isolation, 'active', return_value=True), patch.object(isolation, 'model_port', return_value=11435), \
     patch.object(isolation, 'properties', return_value=policy):
    assert isolation.policy_status()['summary'] == 'active'
    assert 'Policy status only' in isolation.policy_status()['verification']
    with patch.object(isolation, 'properties', return_value={**policy, 'IPAddressAllow': '0.0.0.0/0 ::1/128 127.0.0.1/32'}):
        assert isolation.policy_status()['summary'] == 'attention'
with patch.object(isolation, 'active', return_value=False), patch.object(isolation, 'model_port', return_value=11434), \
     patch.object(isolation, 'properties', return_value={'LoadState': 'not-found'}):
    assert isolation.policy_status()['summary'] == 'off'
with patch.object(isolation, 'properties', return_value=props), \
     patch.object(isolation, 'outside_ipv4', return_value=True), \
     patch.object(isolation, 'api', side_effect=[{'done': True, 'response': 'OK'}, {'error': 'invalid model name'}]):
    result = isolation.model_checks()
    assert result['model_IPv4']['status'] == 'INCONCLUSIVE'
    assert result['model_IPv6']['status'] == 'NOT TESTED'
print('PASS: 4.2 appearance/privacy, exclusive readable reports, ElectronMail roles and Notes focus/shortcut failures')

# The real diagnostic child must deliver progress before it exits. Completion
# and timeouts may not hold service locks or terminate unrelated processes.
runtime=load('diagnostic_runtime_fixture','scripts/control_runtime.py')
with tempfile.TemporaryDirectory() as directory:
    acknowledgement=Path(directory)/'progress-received'
    script="""import sys,time
from pathlib import Path
print('Isolation check: Comparing actual worker network access…',flush=True)
deadline=time.monotonic()+4
while not Path(sys.argv[1]).exists():
    if time.monotonic()>deadline:raise SystemExit('Progress was buffered until exit')
    time.sleep(0.01)
print('Workers: INCONCLUSIVE')
"""
    stages=[]
    def received(stage):
        stages.append(stage);acknowledgement.write_text('received')
    completed=runtime._run_isolation_check([sys.executable,'-c',script,str(acknowledgement)],received,timeout=6)
    assert completed.returncode==0 and 'Workers: INCONCLUSIVE' in completed.stdout
    assert stages==['Comparing actual worker network access…']
    with patch.object(runtime,'_run_isolation_check',return_value=subprocess.CompletedProcess([],1,'Diagnostic failed','')):
        rejected(lambda:runtime.maintenance('isolation',progress=received))

unrelated=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'])
started=time.monotonic()
try:
    try:
        runtime._run_isolation_check([sys.executable,'-c','import time; time.sleep(30)'],lambda text:None,timeout=0.15)
    except RuntimeError as error:
        assert 'timed out' in str(error) and 'No passed result' in str(error)
    else:raise AssertionError('Hung diagnostic returned success')
    assert time.monotonic()-started<6 and unrelated.poll() is None
finally:
    unrelated.terminate();unrelated.wait(timeout=5)
print('PASS: real diagnostic stage delivery before exit, failed-result refusal and bounded timeout without unrelated termination')
