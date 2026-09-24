"""Native GTK control centre, embedding the existing apps/commands editor."""
import importlib.util
from pathlib import Path
import threading
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk, GLib, Gdk
from settings_export import export_settings
from control_runtime import (service_action, microphone_action, speech_stop, status,
                             maintenance, voice_setting, read_json, update_available)

CSS = b'''
.jarvis-root { background-color: @theme_bg_color; }
.jarvis-sidebar { padding: 12px 8px; background-color: alpha(@theme_fg_color, 0.035); }
.jarvis-sidebar row { border-radius: 8px; padding: 12px 10px; margin-bottom: 5px; }
.jarvis-title { font-size: 27px; font-weight: 700; }
.jarvis-subtitle { opacity: 0.72; }
.jarvis-card { border: 1px solid alpha(@theme_fg_color, 0.13); border-radius: 12px; padding: 18px; background-color: alpha(@theme_base_color, 0.65); }
.jarvis-heading { font-size: 16px; font-weight: 600; }
.jarvis-control button { padding: 9px 14px; border-radius: 7px; }
.jarvis-status { font-size: 21px; font-weight: 600; }
'''


def label(text, style=None):
    obj=Gtk.Label(label=text,xalign=0)
    obj.set_line_wrap(True)
    if style:obj.get_style_context().add_class(style)
    return obj


def button(text, icon, callback):
    obj=Gtk.Button(label=text)
    obj.set_image(Gtk.Image.new_from_icon_name(icon,Gtk.IconSize.BUTTON))
    obj.set_always_show_image(True)
    obj.connect('clicked',callback)
    return obj


def worker(work, finish, progress=None):
    def run():
        try:result,error=work(),None
        except Exception as exc:result,error=None,str(exc)
        GLib.idle_add(finish,result,error)
    threading.Thread(target=run,name='jarvis-control',daemon=True).start()


class ControlCenter:
    def __init__(self, dialog, outer, notebook, footer, save, cancel, state, editor,
                 refresh_config, *, check_only=False):
        self.dialog=dialog;self.state=state;self.editor=editor
        self.refresh_config=refresh_config;self.check_only=check_only
        self.alive=True;self.polling=False;self.buttons=[];self.busy=False
        self.emergency_busy=False;self.latest=None
        self.footer=footer;self.save=save;self.cancel=cancel;self.notebook=notebook
        self.saved_flags=None
        self.provider=Gtk.CssProvider();self.provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),self.provider,
                                                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        dialog.set_title('Jarvis');dialog.get_style_context().add_class('jarvis-root')
        screen=Gdk.Screen.get_default()
        width,height=(screen.get_width(),screen.get_height()) if screen else (1024,768)
        dialog.set_default_size(min(960,width-48),min(700,height-80))
        dialog.set_size_request(min(680,width-48),min(460,height-80))
        dialog.set_icon_name('audio-input-microphone')
        outer.remove(notebook)
        self.layout=Gtk.Box(spacing=0)
        outer.pack_start(self.layout,True,True,0);outer.reorder_child(self.layout,0)
        self.nav=Gtk.ListBox();self.nav.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.nav.set_size_request(180,-1);self.nav.get_style_context().add_class('jarvis-sidebar')
        self.layout.pack_start(self.nav,False,False,0)
        self.stack=Gtk.Stack();self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120);self.layout.pack_start(self.stack,True,True,0)
        self.pages={}
        overview=self.page('overview','Overview','Your voice assistant, at a glance.','view-grid-symbolic')
        self.build_overview(overview)
        app_page=self.page('apps','Apps & Commands','Choose what Jarvis can open and what you say.','applications-other-symbolic',scroll=False)
        app_page.pack_start(notebook,True,True,0)
        voice=self.page('voice','Voice','Wake phrase and keyboard shortcuts.','audio-input-microphone-symbolic')
        self.build_voice(voice)
        maintenance_page=self.page('maintenance','Maintenance','Check, update and troubleshoot Jarvis.','preferences-system-symbolic')
        self.build_maintenance(maintenance_page)
        self.nav.connect('row-selected',self.selected)
        # A pulsing bar is honest about unbounded service startup, not a timer estimate.
        self.activity=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
        self.activity.set_margin_start(12);self.activity.set_margin_end(12)
        self.activity_label=label('');self.activity_label.set_max_width_chars(95)
        self.progress=Gtk.ProgressBar();self.progress.set_show_text(False)
        self.activity.pack_start(self.activity_label,False,False,0)
        self.activity.pack_start(self.progress,False,False,0)
        outer.pack_start(self.activity,False,False,0)
        self.activity.set_no_show_all(True)
        dialog.connect('destroy',self.destroy)
        if not check_only:
            GLib.timeout_add_seconds(3,self.poll)
            GLib.timeout_add(120,self.tick)
            self.poll()

    def page(self,key,title,subtitle,icon,scroll=True):
        row=Gtk.ListBoxRow();row.key=key
        box=Gtk.Box(spacing=9)
        box.pack_start(Gtk.Image.new_from_icon_name(icon,Gtk.IconSize.MENU),False,False,0)
        box.pack_start(Gtk.Label(label=title,xalign=0),True,True,0);row.add(box);self.nav.add(row)
        content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=18)
        content.set_border_width(24);content.get_style_context().add_class('jarvis-control')
        heading=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=5)
        heading.pack_start(label(title,'jarvis-title'),False,False,0)
        heading.pack_start(label(subtitle,'jarvis-subtitle'),False,False,0)
        content.pack_start(heading,False,False,0)
        if scroll:
            scroller=Gtk.ScrolledWindow();scroller.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
            scroller.add(content);self.stack.add_named(scroller,key)
        else:self.stack.add_named(content,key)
        self.pages[key]=row
        return content

    def card(self,parent,title,description=None):
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10)
        box.get_style_context().add_class('jarvis-card')
        box.pack_start(label(title,'jarvis-heading'),False,False,0)
        if description:box.pack_start(label(description,'jarvis-subtitle'),False,False,0)
        parent.pack_start(box,False,False,0)
        return box

    def action(self,parent,text,icon,callback,primary=False):
        obj=button(text,icon,callback)
        if primary:obj.get_style_context().add_class('suggested-action')
        parent.pack_start(obj,False,False,0);self.buttons.append(obj)
        return obj

    def build_overview(self,parent):
        card=self.card(parent,'Voice system')
        self.status_label=label('Checking Jarvis…','jarvis-status')
        self.status_detail=label('Reading the local service state.','jarvis-subtitle')
        card.pack_start(self.status_label,False,False,0);card.pack_start(self.status_detail,False,False,0)
        controls=Gtk.Box(spacing=10);card.pack_start(controls,False,False,0)
        self.start_stop=self.action(controls,'Start Jarvis','media-playback-start-symbolic',self.power,True)
        self.restart=self.action(controls,'Restart Jarvis','view-refresh-symbolic',lambda _:self.task('Restarting Jarvis',lambda:self.services('restart')))
        card=self.card(parent,'Microphone','Pause Jarvis listening. Other applications can still use your microphone.')
        self.mic=self.action(card,'Checking microphone…','audio-input-microphone-symbolic',lambda _:self.task('Updating microphone',microphone_action))
        card=self.card(parent,'Need quiet?','Emergency stop for speech and reading. Also cancels the current voice request.')
        self.emergency=button('Stop speaking','media-playback-stop-symbolic',self.stop_speech)
        card.pack_start(self.emergency,False,False,0)
        self.emergency_note=label('Available even while Jarvis is restarting.','jarvis-subtitle')
        card.pack_start(self.emergency_note,False,False,0)

    def build_voice(self,parent):
        config=read_json(Path.home()/'.config/jarvis/capabilities.json')
        wake=self.card(parent,'Wake phrase','Say this to get Jarvis’s attention.')
        self.wake=Gtk.Entry();self.wake.set_text(config.get('wake_phrase_spoken',config.get('wake_phrase','hey_jarvis').replace('_',' ')))
        wake.pack_start(self.wake,False,False,0)
        self.action(wake,'Save wake phrase','document-save-symbolic',lambda _:self.voice('wake',[self.wake.get_text()]))
        shortcuts=self.card(parent,'Keyboard shortcuts','Use GTK notation, for example <Super>l or <Control><Alt>j. Existing collision checks still apply.')
        self.listen=Gtk.Entry();self.listen.set_text(config.get('listen_shortcut',''))
        self.mic_shortcut=Gtk.Entry();self.mic_shortcut.set_text(config.get('microphone_shortcut',''))
        for title,entry in [('Start listening',self.listen),('Toggle Jarvis microphone',self.mic_shortcut)]:
            shortcuts.pack_start(label(title),False,False,0);shortcuts.pack_start(entry,False,False,0)
        self.action(shortcuts,'Save shortcuts','document-save-symbolic',lambda _:self.voice('shortcuts',[self.listen.get_text(),self.mic_shortcut.get_text()]))
        self.action(shortcuts,'Load current shortcuts','view-refresh-symbolic',self.load_shortcuts)
        parent.pack_start(label('Speech recognition and Bella keep their current settings.','jarvis-subtitle'),False,False,0)

    def load_shortcuts(self,_button):
        def work():
            path=Path(__file__).with_name('listen-shortcut.py')
            spec=importlib.util.spec_from_file_location('jarvis_shortcut_settings',path)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            return module.current_shortcuts()
        def done(value):
            self.listen.set_text(value[0]);self.mic_shortcut.set_text(value[1])
            return 'Current shortcuts loaded.'
        self.task('Loading shortcuts',work,on_success=done)

    def voice(self,kind,values):
        if self.state['dirty'] or self.editor.dirty:
            self.show_activity('Save or discard your app and command changes first.',False);return
        self.task('Saving voice settings',lambda:voice_setting(kind,values,self.report),on_success=self.voice_saved)

    def voice_saved(self,value):
        self.refresh_config()
        return value

    def build_maintenance(self,parent):
        actions=self.card(parent,'Keep Jarvis running')
        grid=Gtk.Box(spacing=8);actions.pack_start(grid,False,False,0)
        for name,icon,key in [('Health check','emblem-default-symbolic','health'),('Check for updates','software-update-available-symbolic','updates')]:
            self.action(grid,name,icon,lambda _,k=key:self.maintain(k))
        self.update_label=label('Updates are checked only when requested.','jarvis-subtitle');actions.pack_start(self.update_label,False,False,0)
        self.install_update=self.action(actions,'Install available update','software-update-available-symbolic',self.install_release)
        self.install_update.set_sensitive(False)
        backup=self.card(parent,'Settings backup','Export app choices, spoken names, commands, shortcuts and voice settings. Saved configuration may contain credentials; keep the archive private.')
        self.action(backup,'Export settings…','document-save-as-symbolic',self.export_backup)
        support=self.card(parent,'Support')
        row=Gtk.Box(spacing=8);support.pack_start(row,False,False,0)
        for name,icon,key in [('Create report','document-save-symbolic','report'),('Recent logs','text-x-generic-symbolic','logs'),('About','help-about-symbolic','about')]:
            self.action(row,name,icon,lambda _,k=key:self.maintain(k))
        support.pack_start(label('Reports stay on this computer. Recent logs may contain your spoken words.','jarvis-subtitle'),False,False,0)
        advanced=Gtk.Expander(label='Advanced');parent.pack_start(advanced,False,False,0)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);advanced.add(box)
        self.action(box,'Restart commands only','view-refresh-symbolic',lambda _:self.task('Restarting commands',lambda:self.services('commands')))
        self.details=Gtk.Expander(label='Results and details');parent.pack_start(self.details,True,True,0)
        scroll=Gtk.ScrolledWindow();scroll.set_min_content_height(180)
        self.output=Gtk.TextView();self.output.set_editable(False);self.output.set_monospace(True)
        self.output.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);scroll.add(self.output);self.details.add(scroll)
        self.output.get_buffer().set_text('Results will appear here.')

    def export_backup(self,_button):
        if self.state['dirty'] or self.editor.dirty:
            self.show_activity('Save your app and command changes before exporting.',False);return
        chooser=Gtk.FileChooserDialog(title='Choose where to save your settings backup',
            transient_for=self.dialog,modal=True,action=Gtk.FileChooserAction.SELECT_FOLDER)
        chooser.add_buttons('Cancel',Gtk.ResponseType.CANCEL,'Export here',Gtk.ResponseType.OK)
        chooser.set_current_folder(str(Path.home()/'Downloads' if (Path.home()/'Downloads').is_dir() else Path.home()))
        answer=chooser.run();folder=chooser.get_filename();chooser.destroy()
        if answer!=Gtk.ResponseType.OK or not folder:return
        def done(result):
            text='Settings exported to '+result['path']+'\n'+str(result['files'])+' files saved.'
            if result['skipped']:
                text+='\nSome settings were skipped. See the archive manifest.\n'+'\n'.join(item['path']+': '+item['reason'] for item in result['skipped'])
            self.output.get_buffer().set_text(text);self.details.set_expanded(True)
            return text
        self.task('Exporting saved settings…',lambda:export_settings(folder),on_success=done)

    def maintain(self,kind):
        def result(text):
            self.output.get_buffer().set_text(str(text));self.details.set_expanded(True)
            self.latest=update_available()
            return {'health':'Health check complete. See results below.','report':'Report created. Location shown below.','updates':'Update check complete.','logs':'Recent logs loaded.','about':'Version information loaded.'}[kind]
        self.task('Working…',lambda:maintenance(kind),on_success=result)

    def install_release(self,_button):
        if not self.latest:return
        prompt=Gtk.MessageDialog(transient_for=self.dialog,modal=True,message_type=Gtk.MessageType.QUESTION,
                                 buttons=Gtk.ButtonsType.OK_CANCEL,text='Install Jarvis '+self.latest+'?')
        prompt.format_secondary_text('This runs the existing updater and may restart Jarvis.')
        answer=prompt.run();prompt.destroy()
        if answer==Gtk.ResponseType.OK:self.task('Installing update…',lambda:maintenance('install'))

    def services(self,action):return service_action(action,self.report)

    def power(self,_button):
        action='start' if not getattr(self,'running',False) else 'stop'
        self.task('Starting Jarvis' if action=='start' else 'Stopping Jarvis',lambda:self.services(action))

    def report(self,text):GLib.idle_add(self.show_activity,text,True)

    def show_activity(self,text,busy=False):
        if not self.alive:return False
        self.activity_label.set_text(text);self.activity.show();self.activity_label.show()
        if busy:self.progress.show()
        else:self.progress.hide()
        return False

    def task(self,title,work,on_success=None):
        if self.state['busy'] or self.busy:return
        self.busy=True;self.state['busy']=True
        self.notebook.set_sensitive(False);self.save.set_sensitive(False);self.cancel.set_sensitive(False)
        for obj in self.buttons:obj.set_sensitive(False)
        self.show_activity(title,True)
        def done(value,error):
            if not self.alive:return False
            self.busy=False;self.state['busy']=False
            self.notebook.set_sensitive(True);self.save.set_sensitive(True);self.cancel.set_sensitive(True)
            for obj in self.buttons:obj.set_sensitive(True)
            if error:
                self.output.get_buffer().set_text(error);self.details.set_expanded(True)
                self.show_activity('Could not complete: '+error,False)
            else:
                try:message=on_success(value) if on_success else str(value)
                except Exception as exc:message='Completed, but refresh failed: '+str(exc)
                self.show_activity(message,False)
            self.poll();return False
        worker(work,done)

    def stop_speech(self,_button):
        if self.emergency_busy:return
        self.emergency_busy=True;self.emergency.set_sensitive(False)
        self.emergency_note.set_text('Sending stop…')
        def done(value,error):
            if not self.alive:return False
            self.emergency_busy=False;self.emergency.set_sensitive(True)
            self.emergency_note.set_text(error or value);return False
        worker(speech_stop,done)

    def poll(self):
        if not self.alive:return False
        if self.polling or self.state['busy']:return True
        self.polling=True
        def done(value,error):
            self.polling=False
            if not self.alive:return False
            if error:
                self.status_label.set_text('Status unavailable');self.status_detail.set_text(error)
                return False
            names={'ready':'Ready','muted':'Microphone paused','stopped':'Stopped','starting':'Starting…','failed':'Needs attention'}
            self.status_label.set_text(names[value['state']])
            self.running=value['services'].get('ovos-core.service')=='active'
            self.status_detail.set_text('Voice services report ready.' if value['state']=='ready' else
                                       'Use the controls below, or check Maintenance for details.')
            self.start_stop.set_label('Stop Jarvis' if self.running else 'Start Jarvis')
            self.start_stop.set_image(Gtk.Image.new_from_icon_name('media-playback-stop-symbolic' if self.running else 'media-playback-start-symbolic', Gtk.IconSize.BUTTON))
            self.mic.set_label('Pause microphone' if value['microphone'] else 'Enable microphone')
            if not self.state['busy']:
                self.restart.set_sensitive(self.running)
                self.latest=update_available();self.install_update.set_sensitive(bool(self.latest))
                self.update_label.set_text('Jarvis '+self.latest+' is available.' if self.latest else 'No update currently marked available.')
            return False
        worker(status,done);return True

    def tick(self):
        if not self.alive:return False
        if self.busy:self.progress.pulse()
        elif self.state['busy']:
            self.show_activity('Applying app and command changes; waiting for voice readiness…',True)
            self.progress.pulse();self.saved_flags=True
        elif self.saved_flags:
            self.show_activity('App and command save finished. See its result above.',False);self.saved_flags=None
            for obj in self.buttons:obj.set_sensitive(True)
            self.poll()
        for obj in self.buttons:
            if self.state['busy']:obj.set_sensitive(False)
        return True

    def selected(self,_list,row):
        if not row:return
        self.stack.set_visible_child_name(row.key)
        visible=row.key=='apps'
        self.footer.set_visible(visible);self.save.set_visible(visible)

    def show_tab(self,tab='overview'):
        key='apps' if tab in {'applications','commands','apps'} else tab
        self.nav.select_row(self.pages.get(key,self.pages['overview']))
        if tab in {'applications','commands'}:self.notebook.set_current_page(1 if tab=='commands' else 0)
        self.dialog.present()

    def destroy(self,*_args):
        self.alive=False
