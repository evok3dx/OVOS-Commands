#!/usr/bin/env python3
"""Exercise the actual default-app picker with GTK 3 under a test display."""
import ast
import os
from pathlib import Path

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, Gtk, Gdk, GLib

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
assert centre.logging_picker.get_active_id()=='off'
assert centre.logging_note.get_text()=='No logs'
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
# Verify computed text/icon colours, not only the presence of CSS strings.
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),provider,
                                        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
window=Gtk.Window();white_button=Gtk.Button(label='Everything is up to date')
white_button.set_image(Gtk.Image.new_from_icon_name('software-update-available-symbolic',Gtk.IconSize.BUTTON))
white_button.set_always_show_image(True)
white_button.get_style_context().add_class('jarvis-update')
white_button.set_sensitive(False);window.add(white_button);window.show_all()
while Gtk.events_pending():Gtk.main_iteration()
def descendants(widget):
    yield widget
    if isinstance(widget,Gtk.Container):
        for child in widget.get_children():yield from descendants(child)
for child in descendants(white_button):
    if isinstance(child,(Gtk.Label,Gtk.Image)):
        colour=child.get_style_context().get_color(child.get_state_flags())
        assert all(abs(value-1)<0.001 for value in (colour.red,colour.green,colour.blue,colour.alpha)),colour
window.destroy()
parent.destroy();centre.install_update.destroy();centre.update_health.destroy()
print('PASS: General independent switches; GTK update button green/blue/neutral and disabled text/icon computed white')

# A host's light hover/icon rules must not leak into the app's dark sidebar.
settings=Gtk.Settings.get_default();animations=settings.get_property('gtk-enable-animations')
settings.set_property('gtk-enable-animations',False)
host=Gtk.CssProvider();host.load_from_data(b'.jarvis-sidebar row:hover { background-image: linear-gradient(#FFFFFF, #FFFFFF); background-color: #FFFFFF; } .jarvis-sidebar image { color: #000000; }')
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),host,
                                        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION-1)
window=Gtk.Window();window.get_style_context().add_class('jarvis-root')
window.get_style_context().add_class('jarvis-dark')
nav=Gtk.ListBox();nav.set_selection_mode(Gtk.SelectionMode.NONE)
nav.get_style_context().add_class('jarvis-sidebar')
row=Gtk.ListBoxRow();box=Gtk.Box(spacing=8)
icon=Gtk.Image.new_from_icon_name('preferences-system-symbolic',Gtk.IconSize.MENU)
text=Gtk.Label(label='Maintenance');box.add(icon);box.add(text);row.add(box);nav.add(row)
window.add(nav);window.show_all()
def luminance(colour):
    channels=[value/12.92 if value<=0.04045 else ((value+0.055)/1.055)**2.4
              for value in (colour.red,colour.green,colour.blue)]
    return sum(value*weight for value,weight in zip(channels,(0.2126,0.7152,0.0722)))
for flags,background in ((Gtk.StateFlags.NORMAL,None),
                         (Gtk.StateFlags.PRELIGHT,(38,54,76)),
                         (Gtk.StateFlags.SELECTED,(47,111,237)),
                         (Gtk.StateFlags.SELECTED|Gtk.StateFlags.PRELIGHT,(47,111,237))):
    row.set_state_flags(flags,True)
    while Gtk.events_pending():Gtk.main_iteration()
    colour=row.get_style_context().get_background_color(flags)
    if background is None:
        assert colour.alpha<0.01,colour
        colour=Gdk.RGBA(21/255,31/255,46/255,1)
    else:
        assert all(abs(actual-expected/255)<0.01 for actual,expected in
                   zip((colour.red,colour.green,colour.blue),background)),colour
    for child in (text,icon):
        foreground=child.get_style_context().get_color(child.get_state_flags())
        assert min(foreground.red,foreground.green,foreground.blue)>0.8,foreground
        assert (luminance(foreground)+0.05)/(luminance(colour)+0.05)>=4.5
window.destroy()
Gtk.StyleContext.remove_provider_for_screen(Gdk.Screen.get_default(),host)
settings.set_property('gtk-enable-animations',animations)
print('PASS: dark sidebar hover/selected text and symbolic icons resist light host styling with readable contrast')

# Render the production Dashboard in both app-scoped themes, with real GTK
# widgets, and preserve screenshots for review. No service operations run.
window=Gtk.Window();window.set_default_size(950,700)
window.get_style_context().add_class('jarvis-root')
centre.dialog=window
dashboard=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=18);dashboard.set_border_width(24)
window.add(dashboard);centre.build_overview(dashboard)
centre.status_label.set_text('System Online');centre.status_detail.set_text('Ready for your next command.')
centre.start_stop.set_label('Stop Jarvis');centre.colour(centre.start_stop,'jarvis-danger')
centre.start_stop.set_image(Gtk.Image.new_from_icon_name('media-playback-stop-symbolic',Gtk.IconSize.BUTTON))
centre.mic.set_label('Pause microphone')
for led,state in centre.service_labels.values():
    led.get_style_context().add_class('jarvis-led-ready');state.set_text('Ready')
centre.render_recent([('Opened Firefox','21:00',True),('Created a new note','21:01',True),('Started dictation','21:02',True)])
for selected in ('light','dark'):
    centre.apply_theme(selected)
    window.show_all()
    while Gtk.events_pending():Gtk.main_iteration()
    for led,_state in centre.service_labels.values():
        assert isinstance(led,Gtk.Label)
        colour=led.get_style_context().get_color(led.get_state_flags())
        assert colour.green>colour.red and colour.green>colour.blue,colour
    context=centre.start_stop.get_child().get_style_context()
    for child in descendants(centre.start_stop):
        if isinstance(child,Gtk.Label):
            colour=child.get_style_context().get_color(child.get_state_flags())
            assert all(abs(value-1)<0.001 for value in (colour.red,colour.green,colour.blue)),colour
    if os.environ.get('RUNNER_TEMP'):
        # Wait for a real painted frame, not a guessed sleep or an empty event
        # queue which can precede the very first paint.
        loop=GLib.MainLoop();painted=[]
        clock=window.get_frame_clock()
        def after_paint(_clock):
            painted.append(True);loop.quit()
        handler=clock.connect('after-paint',after_paint)
        def expired():
            loop.quit();return False
        timeout=GLib.timeout_add(3000,expired)
        window.queue_draw();loop.run();clock.disconnect(handler)
        if painted:GLib.source_remove(timeout)
        assert painted,'Dashboard did not paint a frame'
        pixbuf=Gdk.pixbuf_get_from_window(window.get_window(),0,0,*window.get_size())
        assert pixbuf is not None
        assert abs(centre.mic.translate_coordinates(window,0,0)[1]-
                   centre.emergency.translate_coordinates(window,0,0)[1])<=1
        pixbuf.savev(str(Path(os.environ['RUNNER_TEMP'])/('Jarvis-Dashboard-'+selected+'.png')),'png',[],[])
assert centre.start_stop.get_parent().get_parent() is centre.overview_summary
assert centre.restart.get_parent() is centre.start_stop.get_parent()
assert len(centre.recent_rows.get_children())==3
window.destroy()
print('PASS: real GTK Dashboard layout, scoped light/dark styling, white action labels and private activity rows')

# Reproduce Apps & Commands' light host notebook inside an app-dark window.
# Check actual painted content and computed tab text/symbolic-icon colours on
# all three pages, including a live theme change on the same widget tree.
animations=settings.get_property('gtk-enable-animations')
settings.set_property('gtk-enable-animations',False)
host=Gtk.CssProvider()
host.load_from_data(b'notebook, notebook > stack, notebook > header, notebook > header tab { background-image: linear-gradient(#FFFFFF, #FFFFFF); background-color: #FFFFFF; } notebook > header image { color: #000000; }')
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),host,
                                        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION-1)
window=Gtk.Window();window.set_default_size(760,420)
window.get_style_context().add_class('jarvis-root')
book=Gtk.Notebook();pages=[];tab_children=[]
for title,icon_name in (('Applications','applications-other-symbolic'),
                        ('Defaults','emblem-default-symbolic'),
                        ('Custom commands','input-keyboard-symbolic')):
    page=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12)
    page.set_border_width(20)
    intro=Gtk.Label(label='Choose what Jarvis can control.',xalign=0)
    page.pack_start(intro,False,False,0)
    search=Gtk.SearchEntry();search.set_placeholder_text('Find an app or spoken command')
    page.pack_start(search,False,False,0)
    tab=Gtk.Box(spacing=6)
    icon=Gtk.Image.new_from_icon_name(icon_name,Gtk.IconSize.MENU)
    text=Gtk.Label(label=title);tab.pack_start(icon,False,False,0);tab.pack_start(text,False,False,0)
    tab.show_all()  # Production setup's tab_label shows custom tab children.
    book.append_page(page,tab);pages.append((page,intro,search));tab_children.extend((text,icon))
window.add(book);window.show_all()
for selected,background in (('dark',(16,23,34)),('light',(255,255,255)),('dark',(16,23,34))):
    context=window.get_style_context()
    for name in ('jarvis-light','jarvis-dark'):context.remove_class(name)
    context.add_class('jarvis-'+selected)
    for index,(page,intro,search) in enumerate(pages):
        book.set_current_page(index)
        while Gtk.events_pending():Gtk.main_iteration()
        loop=GLib.MainLoop();painted=[];clock=window.get_frame_clock()
        def after_paint(_clock):painted.append(True);loop.quit()
        handler=clock.connect('after-paint',after_paint)
        def expired():loop.quit();return False
        timeout=GLib.timeout_add(3000,expired);window.queue_draw();loop.run()
        clock.disconnect(handler)
        if painted:GLib.source_remove(timeout)
        assert painted,'Apps notebook did not paint'
        assert all(child.get_visible() and child.get_mapped() for child in tab_children)
        pixbuf=Gdk.pixbuf_get_from_window(window.get_window(),0,0,*window.get_size())
        assert pixbuf is not None
        x,y=page.translate_coordinates(window,0,0)
        offset=(y+3)*pixbuf.get_rowstride()+(x+3)*pixbuf.get_n_channels()
        actual=pixbuf.get_pixels()[offset:offset+3]
        assert all(abs(value-expected)<=3 for value,expected in zip(actual,background)),(selected,index,list(actual))
        bg=Gdk.RGBA(*(value/255 for value in background),1)
        entry_background=search.get_style_context().get_background_color(search.get_state_flags())
        expected_entry=(21,32,49) if selected=='dark' else (255,255,255)
        assert all(abs(value-expected/255)<0.01 for value,expected in
                   zip((entry_background.red,entry_background.green,entry_background.blue),expected_entry)),entry_background
        for child in [intro,*tab_children]:
            foreground=child.get_style_context().get_color(child.get_state_flags())
            assert (max(luminance(foreground),luminance(bg))+0.05)/(min(luminance(foreground),luminance(bg))+0.05)>=4.5,(selected,foreground)
        if os.environ.get('RUNNER_TEMP') and index==0:
            pixbuf.savev(str(Path(os.environ['RUNNER_TEMP'])/('Jarvis-Apps-'+selected+'.png')),'png',[],[])
window.destroy()
Gtk.StyleContext.remove_provider_for_screen(Gdk.Screen.get_default(),host)
settings.set_property('gtk-enable-animations',animations)
print('PASS: Apps/Defaults/Custom commands resist light host backgrounds, retain readable tab icons/text and switch themes live')

# A failed activity query must not erase known rows or pretend the feed is
# empty. Manual refresh and the polling guard use the same read-only path.
import importlib.util
import json
import subprocess
from unittest.mock import Mock,patch
namespace.update({'Path':Path,'__file__':str(ROOT/'scripts/control_center.py'),
                  'importlib':importlib,'json':json,'subprocess':subprocess})
centre.running=True;centre.check_only=False;centre.activity_polling=False;centre.alive=True
centre.recent_rows=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);centre.recent_status=Gtk.Label()
namespace['worker']=lambda work,finish:finish(work(),None)
snapshot={'schema_version':1,'rows':[{'action':'application.open','integration':'firefox','success':True,'time':'12:00'},
                                  {'action':'notes.new','integration':None,'success':True,'time':'12:01'}]}
with patch.object(subprocess,'run',return_value=Mock(stdout='Background diagnostic\nJARVIS_ACTIVITY_SNAPSHOT='+json.dumps(snapshot)+'\n')):
    centre.refresh_recent()
assert len(centre.recent_rows.get_children())==2 and centre.recent_status.get_text()==''
assert 'Opened Firefox' in [child.get_text() for child in descendants(centre.recent_rows) if isinstance(child,Gtk.Label)]
with patch.object(subprocess,'run',side_effect=subprocess.TimeoutExpired(['fixed-reader'],6,
                  output=('JARVIS_ACTIVITY_SNAPSHOT='+json.dumps(snapshot)+'\n').encode())):
    centre.refresh_recent()
assert len(centre.recent_rows.get_children())==2 and centre.recent_status.get_text()==''
namespace['worker']=lambda work,finish:finish(None,'unavailable')
centre.refresh_recent()
assert len(centre.recent_rows.get_children())==2 and 'Activity unavailable' in centre.recent_status.get_text()
centre.running=False;centre.refresh_recent()
assert 'Start Jarvis' in centre.recent_status.get_text() and len(centre.recent_rows.get_children())==1
centre.recent_rows.destroy();centre.recent_status.destroy()
print('PASS: activity refresh reads framed Firefox/Notes rows, retains results on error and distinguishes stopped voice')

# Visual policy status is not a claim that live network tests passed.
centre.check_only=False;centre.isolation_polling=False;centre.alive=True
namespace['worker']=lambda work,finish: finish(work(),None)
parent=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
centre.build_maintenance(parent)
for state,colour in (('active','jarvis-led-ready'),('off','jarvis-off'),('attention','jarvis-led-warn')):
    namespace['isolation_policy_status']=lambda s=state: {'summary':s,'core':s=='active','model':s=='active',
                                                        'verification':'Policy status only. Use Check isolation for network verification.'}
    centre.refresh_isolation()
    assert centre.isolation_led.get_style_context().has_class(colour)
    assert 'Policy status only' in centre.isolation_note.get_text()

# Exercise the actual task lifecycle: stage feedback, result details and reset
# after success/failure, without touching native services or the model.
centre.buttons=[];centre.state={'busy':False};centre.busy=False
centre.notebook=Gtk.Notebook();centre.save=Gtk.Button();centre.cancel=Gtk.Button()
centre.poll=lambda:None;centre.refresh_isolation=lambda:None
messages=[];centre.show_activity=lambda text,busy=False:messages.append((text,busy))
centre.report=lambda text:messages.append((text,True))
namespace['update_status']=lambda:{'available':False,'latest':'4.2.1'}
def isolation_success(kind,progress):
    assert kind=='isolation'
    progress('Comparing actual worker network access…')
    return 'Workers: ACTUAL WORKER SOCKET TESTS PASSED\nPrivate model IPv6: NOT TESTED'
namespace['maintenance']=isolation_success
centre.maintain('isolation')
assert any('Comparing actual worker' in text for text,_ in messages)
assert messages[-1]==('Isolation check complete. See results below.',False)
assert 'NOT TESTED' in centre.output.get_buffer().get_text(
    centre.output.get_buffer().get_start_iter(),centre.output.get_buffer().get_end_iter(),True)
assert not centre.busy and not centre.state['busy'] and centre.cancel.get_sensitive()
def failed_worker(work,finish):finish(None,'Isolation check timed out. No passed result was recorded.')
namespace['worker']=failed_worker
centre.maintain('isolation')
assert messages[-1][0].startswith('Could not complete: Isolation check timed out.')
assert messages[-1][1] is False and not centre.busy and not centre.state['busy']
namespace['worker']=lambda work,finish:finish(work(),None)
for warnings in (0,2):
    def health_success(kind):
        assert kind=='health'
        assert centre.health_check_button.get_label()=='Health check'
        assert not centre.health_check_button.get_style_context().has_class('jarvis-enable')
        return f'12 passed, {warnings} warnings, 0 failures'
    namespace['maintenance']=health_success
    centre.maintain('health')
    assert centre.health_check_button.get_label()=='No errors found'
    assert centre.health_check_button.get_style_context().has_class('jarvis-enable')
    assert messages[-1]==('No errors found. Health check passed.',False)
    text=centre.output.get_buffer().get_text(centre.output.get_buffer().get_start_iter(),centre.output.get_buffer().get_end_iter(),True)
    assert f'{warnings} warnings' in text
namespace['worker']=lambda work,finish:finish(None,'Health check failed')
centre.maintain('health')
assert centre.health_check_button.get_label()=='Health check'
assert not centre.health_check_button.get_style_context().has_class('jarvis-enable')
assert messages[-1][0]=='Could not complete: Health check failed'
namespace['worker']=lambda work,finish:finish(work(),None)
for widget in (centre.notebook,centre.save,centre.cancel):widget.destroy()
parent.destroy()
print('PASS: Maintenance policy, isolation lifecycle and green zero-error health results with warnings preserved')

# Exercise the production first-install choice with a real dialog. Existing
# choices are tested separately without a dialog or administrator prompt.
import contextlib
import io
import sys
import tempfile
from unittest.mock import patch
from gi.repository import GLib
sys.path.insert(0, str(ROOT / 'scripts'))
import isolation_install

for accept, selected in ((True, True), (True, False), (False, True)):
    observed = []
    def respond():
        for dialog in Gtk.Window.list_toplevels():
            if isinstance(dialog, Gtk.Dialog) and dialog.get_title() == 'Jarvis installation':
                choices = [widget for widget in descendants(dialog) if isinstance(widget, Gtk.CheckButton)]
                assert len(choices) == 1 and choices[0].get_active() is True
                observed.append(True)
                choices[0].set_active(selected)
                dialog.response(Gtk.ResponseType.OK if accept else Gtk.ResponseType.CANCEL)
                return False
        return True
    GLib.idle_add(respond)
    with tempfile.TemporaryDirectory() as folder, \
         patch.object(isolation_install, 'active', return_value=False), \
         patch.object(sys.stdin, 'isatty', return_value=False), \
         patch.object(sys.stdout, 'isatty', return_value=False), \
         contextlib.redirect_stdout(io.StringIO()):
        if accept:
            assert isolation_install.select(Path(folder), False)[0] is selected
        else:
            try:
                isolation_install.select(Path(folder), False)
            except RuntimeError as error:
                assert 'cancelled' in str(error)
            else:
                raise AssertionError('Cancel changed isolation preference')
        assert observed == [True]
print('PASS: real GTK first-install recommendation, opt-out and cancellation without native operations')
