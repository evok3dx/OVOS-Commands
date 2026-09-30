#!/usr/bin/env python3
"""Exercise the actual default-app picker with GTK 3 under a test display."""
import ast
import os
from pathlib import Path

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, Gtk

assert os.getuid() != 0, 'Run GUI tests as the ordinary user'
assert Gtk.init_check()[0], 'A test display is required; use xvfb-run'

ROOT = Path(__file__).resolve().parents[1]
source = ast.parse((ROOT / 'scripts/setup.py').read_text())
picker_class = next(node for node in ast.walk(source)
                    if isinstance(node, ast.ClassDef) and node.name == 'DefaultAppPicker')
# Execute the production widget without loading user settings or controlling services.
namespace = {'Gtk': Gtk, 'app_icon': lambda identifier: Gio.ThemedIcon.new(identifier)}
exec(compile(ast.Module(body=[picker_class], type_ignores=[]),
             'production-default-app-picker', 'exec'), namespace)
picker = namespace['DefaultAppPicker']()
notifications = []
picker.connect_changed(lambda widget: notifications.append(widget.get_active_id()))
options = {'web-browser': 'Brave', 'mail-send': 'System default mail',
           'text-editor': 'Notes & documents – café'}
for identifier, text in options.items():
    picker.append(identifier, text)
    # This is the real GTK behaviour that crashed the released GUI.
    assert picker._choices[identifier].get_label() is None

for identifier, text in options.items():
    for _ in range(2):
        picker._display_label.set_text('stale')
        picker.set_active_id(identifier)
        assert picker.get_active_id() == identifier
        assert picker._display_label.get_text() == text
        assert picker.get_accessible().get_name() == text
        assert picker._display_icon.get_property('gicon').equal(Gio.ThemedIcon.new(identifier))
assert notifications == [], 'Loading saved defaults must not mark settings changed'

picker._choices['web-browser'].set_active(True)
assert notifications == ['web-browser']
assert picker._display_label.get_text() == 'Brave'
picker.set_active_id('missing')
assert picker.get_active_id() is None
assert picker._display_label.get_text() == 'No compatible app enabled'
picker.remove_all()
assert not picker._choices and not picker._choice_text
picker.append('web-browser', 'Renamed browser')
picker.set_active_id('web-browser')
assert picker._display_label.get_text() == 'Renamed browser'
picker.destroy()
print('PASS: real GTK custom icon rows restore saved labels/icons without None or change callbacks')
