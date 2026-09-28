"""Native GTK control centre, embedding the existing apps/commands editor."""
import importlib.util
from pathlib import Path
import threading
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk, GLib, Gdk
from settings_export import export_settings
from control_runtime import (service_action, microphone_action, speech_stop, status,
                             maintenance, voice_setting, read_json, update_status,
                             speech_note_status, speech_note_action, audio_settings,
                             uninstall_jarvis)

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
.jarvis-danger { background-image: none; background-color: #2F6FED; border-color: #2459C2; color: #FFFFFF; }
.jarvis-danger:hover { background-color: #285FCF; border-color: #1E4DA7; color: #FFFFFF; }
.jarvis-warning { background-image: none; background-color: #2F6FED; border-color: #2459C2; color: #FFFFFF; }
.jarvis-warning:hover { background-color: #285FCF; border-color: #1E4DA7; color: #FFFFFF; }
.jarvis-restart { background-image: none; background-color: #2F6FED; border-color: #2459C2; color: #FFFFFF; }
.jarvis-restart:hover { background-color: #285FCF; border-color: #1E4DA7; color: #FFFFFF; }
.jarvis-update { background-image: none; background-color: #20A464; border-color: #16814C; color: #FFFFFF; }
.jarvis-update:hover { background-color: #198F56; border-color: #106E40; color: #FFFFFF; }
.jarvis-enable { background-image: none; background-color: #20A464; border-color: #16814C; color: #FFFFFF; }
.jarvis-enable:hover { background-color: #198F56; border-color: #106E40; color: #FFFFFF; }
.jarvis-service-row { border: 1px solid alpha(@theme_fg_color, 0.10); border-radius: 9px; padding: 7px 11px; background-color: alpha(@theme_base_color, 0.42); }
.jarvis-service-name { font-weight: 600; }
.jarvis-service-state { opacity: 0.66; }
.jarvis-led { min-width: 16px; }
.jarvis-led-ready { color: #20C875; }
.jarvis-led-warn { color: #F2A12C; }
.jarvis-led-down { color: #E05260; }
.jarvis-summary { border: 1px solid alpha(@theme_fg_color, 0.10); border-radius: 11px; padding: 10px 13px; }
.jarvis-summary-good { background-color: alpha(#20A464, 0.22); border-color: alpha(#20A464, 0.72); }
.jarvis-summary-update { background-color: alpha(#5b7fd4, 0.11); border-color: alpha(#5b7fd4, 0.34); }
.jarvis-summary-warn { background-color: alpha(#d6a247, 0.11); border-color: alpha(#d6a247, 0.34); }
.jarvis-summary-title { font-weight: 600; }
.jarvis-summary-detail { opacity: 0.70; }
.jarvis-mode { padding: 8px 10px; border: 1px solid alpha(@theme_fg_color, 0.13); border-radius: 8px; background-image: none; background-color: alpha(@theme_base_color, 0.40); }
.jarvis-mode:checked { background-color: #2D8CFF; border-color: #1673D3; color: #FFFFFF; }
.jarvis-mode-note { opacity: 0.70; }
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
        dialog.set_default_size(min(1080,width-48),min(760,height-80))
        dialog.set_size_request(min(760,width-48),min(520,height-80))
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
        maintenance_page=self.page('maintenance','Maintenance','Back up, check and troubleshoot Jarvis.','preferences-system-symbolic')
        self.build_maintenance(maintenance_page)
        updates_page=self.page('updates','Updates','Version, release date and installation.','software-update-available-symbolic')
        self.build_updates(updates_page)
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

    @staticmethod
    def colour(obj, style):
        context=obj.get_style_context()
        for name in ('jarvis-danger','jarvis-warning','jarvis-restart','jarvis-update','jarvis-enable'):
            context.remove_class(name)
        if style:context.add_class(style)

    def build_overview(self,parent):
        summary=Gtk.Box(spacing=11);summary.get_style_context().add_class('jarvis-summary')
        self.overview_icon=Gtk.Image.new_from_icon_name('emblem-default-symbolic',Gtk.IconSize.LARGE_TOOLBAR)
        summary.pack_start(self.overview_icon,False,False,0)
        summary_text=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2)
        self.overview_health=label('Checking Jarvis…','jarvis-summary-title')
        self.overview_update=label('Reading service and update status.','jarvis-summary-detail')
        summary_text.pack_start(self.overview_health,False,False,0)
        summary_text.pack_start(self.overview_update,False,False,0)
        summary.pack_start(summary_text,True,True,0);parent.pack_start(summary,False,False,0)
        self.overview_summary=summary
        card=self.card(parent,'Voice system')
        self.status_label=label('Checking Jarvis…','jarvis-status')
        self.status_detail=label('Reading the local service state.','jarvis-subtitle')
        card.pack_start(self.status_label,False,False,0);card.pack_start(self.status_detail,False,False,0)
        controls=Gtk.Box(spacing=10);card.pack_start(controls,False,False,0)
        self.start_stop=self.action(controls,'Start Jarvis','media-playback-start-symbolic',self.power,True)
        self.restart=self.action(controls,'Restart commands','view-refresh-symbolic',lambda _:self.task('Restarting commands',lambda:self.services('commands')))
        self.colour(self.restart,'jarvis-restart')
        service_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
        card.pack_start(service_box,False,False,0)
        self.service_labels={}
        for unit,title in [('ovos-audio.service','Speech'),('ovos-listener.service','Listener'),('ovos-core.service','Commands')]:
            row=Gtk.Box(spacing=9);row.get_style_context().add_class('jarvis-service-row')
            led=Gtk.Image.new_from_icon_name('media-record-symbolic',Gtk.IconSize.MENU)
            led.get_style_context().add_class('jarvis-led')
            name=label(title,'jarvis-service-name')
            state=Gtk.Label(label='Checking…',xalign=1);state.get_style_context().add_class('jarvis-service-state')
            row.pack_start(led,False,False,0);row.pack_start(name,True,True,0);row.pack_end(state,False,False,0)
            service_box.pack_start(row,False,False,0);self.service_labels[unit]=(led,state)
        quick=Gtk.Box(spacing=12);parent.pack_start(quick,False,False,0)
        card=self.card(quick,'Microphone','Pause Jarvis listening. Other applications can still use your microphone.')
        card.set_hexpand(True)
        self.mic=self.action(card,'Checking microphone…','audio-input-microphone-symbolic',lambda _:self.task('Updating microphone',microphone_action))
        self.colour(self.mic,'jarvis-warning')
        card=self.card(quick,'Need quiet?','Stop speech, reading and the current request immediately.')
        card.set_hexpand(True)
        self.emergency=button('Stop speaking','media-playback-stop-symbolic',self.stop_speech)
        self.colour(self.emergency,'jarvis-danger')
        card.pack_start(self.emergency,False,False,0)
        self.emergency_note=label('Available even while Jarvis is restarting.','jarvis-subtitle')
        card.pack_start(self.emergency_note,False,False,0)

    def build_voice(self,parent):
        config=read_json(Path.home()/'.config/jarvis/capabilities.json')
        audio=audio_settings()
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
        background=self.card(parent,'Background audio while listening','Keep music or other playback audible while Jarvis records a command.')
        enabled=Gtk.Box(spacing=10);background.pack_start(enabled,False,False,0)
        enabled.pack_start(label('Lower background audio'),True,True,0)
        self.audio_duck=Gtk.Switch();self.audio_duck.set_active(audio['enabled']);enabled.pack_end(self.audio_duck,False,False,0)
        self.audio_volume=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,10,50,5)
        self.audio_volume.set_value(audio['volume']);self.audio_volume.set_digits(0)
        self.audio_volume.set_value_pos(Gtk.PositionType.RIGHT);background.pack_start(self.audio_volume,False,False,0)
        background.pack_start(label('20% is recommended. Raise it if speakers become inaudible; lower it if recognition suffers.','jarvis-subtitle'),False,False,0)
        self.action(background,'Save background audio','document-save-symbolic',lambda _:self.voice('audio',[self.audio_duck.get_active(),int(round(self.audio_volume.get_value()/5)*5)]))
        speech_note=self.card(parent,'Speech Note','Local reading and dictation. Existing models, voices, settings and rules remain untouched.')
        speech_note.pack_start(label('Continuous dictation needs the wake-filter rule shown by setup. If you change the wake phrase, update that Speech Note rule too.','jarvis-subtitle'),False,False,0)
        self.action(speech_note,'Open Speech Note and setup guide…','audio-x-generic-symbolic',self.speech_note)
        parent.pack_start(label('Speech recognition and Bella keep their current settings.','jarvis-subtitle'),False,False,0)

    def speech_note(self,_button):
        self.task('Checking Speech Note…',speech_note_status,on_success=self.speech_note_ready)

    def speech_note_ready(self,value):
        if value['installed']:
            GLib.idle_add(self.start_speech_note_action,'open')
            return value['detail']
        prompt=Gtk.MessageDialog(transient_for=self.dialog,modal=True,
                                 message_type=Gtk.MessageType.QUESTION,
                                 buttons=Gtk.ButtonsType.OK_CANCEL,
                                 text='Install Speech Note for this user?')
        prompt.format_secondary_text('This is an optional sizeable Flatpak. Language and voice models are separate downloads. No administrator access is used.')
        answer=prompt.run();prompt.destroy()
        if answer==Gtk.ResponseType.OK:
            GLib.idle_add(self.start_speech_note_action,'install')
            return 'Speech Note installation approved.'
        return 'Speech Note is not installed.'

    def start_speech_note_action(self,action):
        self.task('Installing Speech Note…' if action=='install' else 'Opening Speech Note…',
                  lambda:speech_note_action(action))
        return False

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
        for name,icon,key in [('Health check','emblem-default-symbolic','health')]:
            self.action(grid,name,icon,lambda _,k=key:self.maintain(k))
        backup=self.card(parent,'Settings backup','Export app choices, spoken names, commands, shortcuts and voice settings. Saved configuration may contain credentials; keep the archive private.')
        self.action(backup,'Export settings…','document-save-as-symbolic',self.export_backup)
        support=self.card(parent,'Support')
        row=Gtk.Box(spacing=8);support.pack_start(row,False,False,0)
        for name,icon,key in [('Create report','document-save-symbolic','report'),('Recent logs','text-x-generic-symbolic','logs'),('About','help-about-symbolic','about')]:
            self.action(row,name,icon,lambda _,k=key:self.maintain(k))
        support.pack_start(label('Reports stay on this computer. Recent logs may contain your spoken words.','jarvis-subtitle'),False,False,0)
        advanced=Gtk.Expander(label='Advanced');parent.pack_start(advanced,False,False,0)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);advanced.add(box)
        self.action(box,'Restart full voice system','view-refresh-symbolic',lambda _:self.task('Restarting voice system',lambda:self.services('restart')))
        self.action(box,'Uninstall Jarvis…','edit-delete-symbolic',self.uninstall)
        self.details=Gtk.Expander(label='Results and details');parent.pack_start(self.details,True,True,0)
        scroll=Gtk.ScrolledWindow();scroll.set_min_content_height(180)
        self.output=Gtk.TextView();self.output.set_editable(False);self.output.set_monospace(True)
        self.output.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);scroll.add(self.output);self.details.add(scroll)
        self.output.get_buffer().set_text('Results will appear here.')

    def build_updates(self,parent):
        current=self.card(parent,'Jarvis updates','Updates are checked only when requested. Your settings and downloaded models are preserved.')
        self.update_label=label('Your version: checking…\nLatest version: checking…\nRelease date: checking…','jarvis-subtitle')
        current.pack_start(self.update_label,False,False,0)
        row=Gtk.Box(spacing=8);current.pack_start(row,False,False,0)
        self.action(row,'Check now','view-refresh-symbolic',lambda _:self.maintain('updates'))
        self.install_update=self.action(row,'No update available','software-update-available-symbolic',self.install_release)
        self.install_update.set_sensitive(False)
        details=self.card(parent,'Safe update','Jarvis creates a rollback snapshot before replacing managed files. Application choices, custom commands, OVOS settings, local models and private helpers are preserved.')
        details.pack_start(label('Use Maintenance → Export settings for a separate private settings archive.','jarvis-subtitle'),False,False,0)

    def uninstall(self,_button):
        prompt=Gtk.Dialog(title='Uninstall Jarvis',transient_for=self.dialog,modal=True)
        prompt.add_button('Cancel',Gtk.ResponseType.CANCEL)
        prompt.add_button('Uninstall',Gtk.ResponseType.OK)
        content=prompt.get_content_area();content.set_border_width(18);content.set_spacing(10)
        content.pack_start(label('Remove Jarvis from this computer?','jarvis-heading'),False,False,0)
        content.pack_start(label('Voice services will stop. Shared desktop applications are never removed.','jarvis-subtitle'),False,False,0)
        model=Gtk.CheckButton(label='Remove the Jarvis Qwen model (about 3.1 GB)')
        model.set_active(True);content.pack_start(model,False,False,0)
        settings=Gtk.CheckButton(label='Remove Jarvis settings, custom commands and rollback history')
        settings.set_active(False);content.pack_start(settings,False,False,0)
        ovos=Gtk.CheckButton(label='Also remove the complete OVOS environment')
        ovos.set_active(False);content.pack_start(ovos,False,False,0)
        content.pack_start(label('Leave OVOS unticked if another OVOS setup uses it. Speech Note and its models are left untouched.','jarvis-subtitle'),False,False,0)
        prompt.show_all();answer=prompt.run()
        choices=(model.get_active(),settings.get_active(),ovos.get_active());prompt.destroy()
        if answer!=Gtk.ResponseType.OK:return
        self.task('Uninstalling Jarvis…',lambda:uninstall_jarvis(*choices),on_success=self.uninstalled)

    def uninstalled(self,value):
        GLib.timeout_add(800,self.dialog.destroy)
        return value

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
            information=update_status()
            self.latest=information['latest'] if information['available'] else None
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
            if self.running:self.start_stop.get_style_context().remove_class('suggested-action')
            else:self.start_stop.get_style_context().add_class('suggested-action')
            self.mic.set_label('Pause microphone' if value['microphone'] else 'Enable microphone')
            self.colour(self.start_stop,'jarvis-danger' if self.running else None)
            self.colour(self.mic,'jarvis-warning' if value['microphone'] else 'jarvis-enable')
            for unit,(led,item) in self.service_labels.items():
                service_state=value['services'].get(unit,'unknown')
                item.set_text(service_state.capitalize())
                context=led.get_style_context()
                for style in ('jarvis-led-ready','jarvis-led-warn','jarvis-led-down'):context.remove_class(style)
                context.add_class('jarvis-led-ready' if service_state=='active' else
                                  'jarvis-led-warn' if service_state=='activating' else 'jarvis-led-down')
            if not self.state['busy']:
                self.restart.set_sensitive(self.running)
                information=update_status();self.latest=information['latest'] if information['available'] else None
                date=information['release_date'] or 'Not recorded'
                detail=('Your version: '+information['installed']+'\nLatest version: '+information['latest']+'\nRelease date: '+date)
                self.update_label.set_text(('Update available\n' if information['available'] else '')+detail)
                summary_context=self.overview_summary.get_style_context()
                for style in ('jarvis-summary-good','jarvis-summary-update','jarvis-summary-warn'):summary_context.remove_class(style)
                if information['available']:
                    self.overview_health.set_text('Update available: '+information['latest'])
                    self.overview_update.set_text('Your version: '+information['installed']+' · Released: '+date)
                    self.overview_icon.set_from_icon_name('software-update-available-symbolic',Gtk.IconSize.LARGE_TOOLBAR)
                    summary_context.add_class('jarvis-summary-update')
                elif value['state']=='ready':
                    self.overview_health.set_text('Everything is working')
                    self.overview_update.set_text('Jarvis '+information['installed']+' is up to date' if information['latest']!='Not checked' else 'Jarvis is ready · Update status has not been checked')
                    self.overview_icon.set_from_icon_name('emblem-default-symbolic',Gtk.IconSize.LARGE_TOOLBAR)
                    summary_context.add_class('jarvis-summary-good')
                else:
                    self.overview_health.set_text('Jarvis needs attention' if value['state']=='failed' else names[value['state']])
                    self.overview_update.set_text('Check the service status below')
                    self.overview_icon.set_from_icon_name('dialog-warning-symbolic',Gtk.IconSize.LARGE_TOOLBAR)
                    summary_context.add_class('jarvis-summary-warn')
                self.install_update.set_label('Update Available ('+self.latest+')' if self.latest else 'No update available')
                self.install_update.set_sensitive(bool(self.latest))
                self.colour(self.install_update,'jarvis-update' if self.latest else None)
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
