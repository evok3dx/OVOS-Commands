#!/usr/bin/env python3
"""Exercise full X11 class identity for discovered and default applications."""
import ast
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import tempfile
import time
from unittest.mock import Mock, patch

if os.getuid() == 0:
    raise SystemExit('Run tests as the ordinary user.')

ROOT = Path(__file__).resolve().parents[1]
default = runpy.run_path(str(ROOT / 'system_helpers/jarvis-default-app'),
                        run_name='default_mail_fixture')
tree = ast.parse((ROOT / 'ovos_skill_jarvis_dispatcher/launcher.py').read_text())
method = next(node for node in tree.body
              if isinstance(node, ast.FunctionDef) and node.name == 'desktop_action')
selected = {'wm_class': 'Proton Mail', 'path': '/reviewed/app.desktop'}
launch = Mock(return_value=True)
scope = {'subprocess': subprocess, 'shutil': shutil, 're': re, 'time': time,
         'load_profile': lambda: {'applications': {'desktop_fixture': selected}},
         'start_desktop': launch}
exec(compile(ast.Module(body=[method], type_ignores=[]), 'launcher.py', 'exec'), scope)
desktop_action = scope['desktop_action']
calls = []
properties = {}

def run(argv, **kwargs):
    calls.append(argv)
    if argv[:2] == ['wmctrl', '-l']:
        # A browser title intentionally contains the target application name.
        return subprocess.CompletedProcess(argv, 0,
            '0x001 0 fixture Proton Mail\n0x002 0 fixture Inbox\n')
    if argv[0] == 'xprop':
        value = properties.get(argv[2])
        if isinstance(value, Exception):
            raise value
        return subprocess.CompletedProcess(argv, 0, value or 'WM_CLASS: not found.')
    return subprocess.CompletedProcess(argv, 0, '')

classes = (
    ('proton mail', 'Proton Mail', 'Proton Mail'),
    ('electron-mail', 'electron-mail', 'electron-mail'),
    ('bitwarden', 'bitwarden', 'bitwarden'),
    ('DesktopEditors', 'ONLYOFFICE', 'ONLYOFFICE'),
    ('Telegram', 'TelegramDesktop', 'TelegramDesktop'),
)
with patch.object(subprocess, 'run', side_effect=run), \
     patch.object(shutil, 'which', side_effect=lambda name: name):
    for instance, class_name, expected in classes:
        properties.update({
            '0x001': 'WM_CLASS(STRING) = "brave-browser", "Brave-browser"',
            '0x002': f'WM_CLASS(STRING) = "{instance}", "{class_name}"',
        })
        selected['wm_class'] = expected
        for action in ('open', 'focus', 'minimize', 'maximize', 'close'):
            calls.clear()
            assert desktop_action('desktop_fixture', action)
            assert calls[-1][0] in {'wmctrl', 'xdotool'}
            assert '0x002' in calls[-1], calls[-1]
            launch.assert_not_called()
        assert default['find_window']({expected.lower()}) == '0x002'

    selected['wm_class'] = 'Proton Mail'
    for invalid in (
        'WM_CLASS(STRING) = "fake-proton mail", "Proton Mail Fake"',
        'WM_CLASS: not found.',
        'WM_CLASS(STRING) = "proton mail", "Proton Mail"\nextra data',
        subprocess.TimeoutExpired('xprop', 1),
    ):
        properties['0x002'] = invalid
        calls.clear()
        assert not desktop_action('desktop_fixture', 'close')
        assert default['find_window']({'proton mail'}) is None
        assert all(call[0] == 'xprop' or call[:2] == ['wmctrl', '-l']
                   for call in calls), calls

with tempfile.TemporaryDirectory() as directory:
    entry = Path(directory) / 'reviewed.desktop'
    entry.write_text('[Desktop Entry]\nName=Proton Mail\nStartupWMClass=Proton Mail\n'
                     'Exec=flatpak run reviewed.application\n')
    needles = default['window_needles']('reviewed.desktop', entry)
    assert 'proton mail' in needles and 'flatpak' not in needles

print('PASS: full class identity, spaced names, fixed desktop metadata and title-spoof rejection')
