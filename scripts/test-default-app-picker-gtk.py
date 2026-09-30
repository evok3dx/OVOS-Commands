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

control_source=ast.parse((ROOT/'scripts/control_center.py').read_text())
nodes=[node for node in control_source.body if isinstance(node,(ast.ClassDef,ast.FunctionDef))
       and node.name in {'ControlCenter','label','button'}]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'production-control-centre','exec'),namespace)
centre=namespace['ControlCenter'].__new__(namespace['ControlCenter'])
centre.buttons=[]
centre.change_startup=lambda *args: True
parent=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
centre.build_general(parent)
assert set(centre.startup_switches)=={'tray','voice'}
assert all(isinstance(switch,Gtk.Switch) for switch in centre.startup_switches.values())
centre.install_update=Gtk.Button();centre.update_health=Gtk.Label()
for available,checked,failed,expected in ((False,True,False,'jarvis-update'),
                                        (True,True,False,'jarvis-update-available'),
                                        (False,False,False,None),(False,True,True,None)):
    centre.refresh_update_button({'available':available,'checked':checked,'failed':failed,'latest':'4.0.0'})
    context=centre.install_update.get_style_context()
    assert context.has_class('jarvis-update')==(expected=='jarvis-update')
    assert context.has_class('jarvis-update-available')==(expected=='jarvis-update-available')
    assert centre.install_update.get_sensitive()==available
    if expected=='jarvis-update':
        assert centre.install_update.get_label()=='Everything is up to date'
        assert centre.update_health.get_text()==''
css=next(node.value for node in control_source.body if isinstance(node,ast.Assign)
         and any(isinstance(target,ast.Name) and target.id=='CSS' for target in node.targets))
provider=Gtk.CssProvider();provider.load_from_data(ast.literal_eval(css))
assert '.jarvis-update:disabled' in ast.literal_eval(css).decode()
parent.destroy();centre.install_update.destroy();centre.update_health.destroy()
print('PASS: General has two independent switches; real GTK update button is green/blue/neutral and CSS loads')
