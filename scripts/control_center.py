"""Native GTK control centre, embedding the existing apps/commands editor."""
import importlib.util
from pathlib import Path
import threading
import json
import subprocess
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk, GLib, Gdk, Pango
from settings_export import export_settings
from startup_settings import inspect as startup_status, set_options as set_startup
from appearance_settings import theme as appearance_theme, save as save_appearance
from isolation_check import policy_status as isolation_policy_status
from control_runtime import (service_action, microphone_action, speech_stop, status,
                             maintenance, voice_setting, read_json, update_status,
                             speech_note_status, speech_note_action, audio_settings,
                             uninstall_jarvis, relaunch_control_center)

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
.jarvis-update:disabled { background-image: none; background-color: #20A464; border-color: #16814C; color: #FFFFFF; opacity: 1; }
.jarvis-update:disabled label, .jarvis-update:disabled image { color: #FFFFFF; opacity: 1; }
.jarvis-update-available { background-image: none; background-color: #2F6FED; border-color: #2459C2; color: #FFFFFF; }
.jarvis-update-available:hover { background-color: #285FCF; border-color: #1E4DA7; color: #FFFFFF; }
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
.jarvis-default-label { font-weight: 600; }
.jarvis-default-combo { padding: 6px 11px; border-radius: 7px; }
.jarvis-default-choice { padding: 8px 10px; border-radius: 6px; }
combobox menu menuitem { padding: 9px 14px; min-height: 24px; }
.jarvis-brand { font-size: 18px; font-weight: 700; }
.jarvis-credit { font-size: 11px; opacity: 0.55; }
.jarvis-off { color: #8994A5; }
.jarvis-privacy { font-size: 11px; opacity: 0.65; margin-top: 12px; }
.jarvis-recent-row { padding: 8px 0; border-bottom: 1px solid alpha(@theme_fg_color, 0.08); }
.jarvis-root.jarvis-light { background-color: #F5F7FB; color: #243247; }
.jarvis-root.jarvis-dark { background-color: #101722; color: #EDF2FA; }
.jarvis-light .jarvis-sidebar { background-color: #ECF0F6; }
.jarvis-dark .jarvis-sidebar { background-color: #151F2E; }
.jarvis-dark .jarvis-sidebar row { background-image: none; background-color: transparent; color: #EDF2FA; }
.jarvis-dark .jarvis-sidebar row:hover { background-image: none; background-color: #26364C; color: #EDF2FA; }
.jarvis-dark .jarvis-sidebar row:selected,
.jarvis-dark .jarvis-sidebar row:selected:hover { background-image: none; background-color: #2F6FED; color: #FFFFFF; }
.jarvis-dark .jarvis-sidebar row label, .jarvis-dark .jarvis-sidebar row image,
.jarvis-dark .jarvis-sidebar row:hover label, .jarvis-dark .jarvis-sidebar row:hover image { color: #EDF2FA; }
.jarvis-dark .jarvis-sidebar row:selected label, .jarvis-dark .jarvis-sidebar row:selected image,
.jarvis-dark .jarvis-sidebar row:selected:hover label, .jarvis-dark .jarvis-sidebar row:selected:hover image { color: #FFFFFF; }
.jarvis-light .jarvis-card { background-color: #FFFFFF; border-color: #DFE5EE; }
.jarvis-dark .jarvis-card { background-color: #192536; border-color: #2A3A50; }
.jarvis-dark label { color: #EDF2FA; }
.jarvis-light label { color: #243247; }
.jarvis-dark notebook, .jarvis-dark notebook > stack,
.jarvis-dark notebook viewport { background-image: none; background-color: #101722; color: #EDF2FA; }
.jarvis-light notebook, .jarvis-light notebook > stack,
.jarvis-light notebook viewport { background-image: none; background-color: #FFFFFF; color: #243247; }
.jarvis-dark notebook > header { background-image: none; background-color: #192536; border-color: #3A4C65; }
.jarvis-light notebook > header { background-image: none; background-color: #ECF0F6; border-color: #DFE5EE; }
.jarvis-dark notebook > header tab { background-image: none; background-color: #192536; border-color: #3A4C65; color: #EDF2FA; }
.jarvis-dark notebook > header tab:hover { background-image: none; background-color: #26364C; color: #EDF2FA; }
.jarvis-dark notebook > header tab:checked { background-image: none; background-color: #26364C; border-bottom-color: #2F6FED; color: #FFFFFF; }
.jarvis-dark notebook > header tab label,
.jarvis-dark notebook > header tab image { color: #EDF2FA; }
.jarvis-dark notebook > header tab:checked label,
.jarvis-dark notebook > header tab:checked image { color: #FFFFFF; }
.jarvis-light notebook > header tab { background-image: none; background-color: #ECF0F6; border-color: #DFE5EE; color: #243247; }
.jarvis-light notebook > header tab:hover { background-image: none; background-color: #E0E7F1; color: #243247; }
.jarvis-light notebook > header tab:checked { background-image: none; background-color: #FFFFFF; border-bottom-color: #2F6FED; color: #243247; }
.jarvis-light notebook > header tab label,
.jarvis-light notebook > header tab image { color: #243247; }
.jarvis-dark .jarvis-subtitle, .jarvis-dark .jarvis-service-state { color: #AAB8CD; }
.jarvis-light .jarvis-subtitle, .jarvis-light .jarvis-service-state { color: #66758B; }
.jarvis-dark .jarvis-service-row { background-color: #1D2D41; border-color: #304158; }
.jarvis-light .jarvis-service-row { background-color: #F7F9FC; border-color: #E7ECF3; }
.jarvis-dark row:selected, .jarvis-light row:selected { background-color: #2F6FED; }
.jarvis-dark row:selected label, .jarvis-light row:selected label { color: #FFFFFF; }
.jarvis-dark button { background-image: none; background-color: #26364C; border-color: #3A4C65; color: #EDF2FA; }
.jarvis-dark entry, .jarvis-dark textview text, .jarvis-dark treeview { background-color: #152031; color: #EDF2FA; }
.jarvis-light entry, .jarvis-light textview text, .jarvis-light treeview { background-color: #FFFFFF; color: #243247; }
.jarvis-dark button.jarvis-danger, .jarvis-dark button.jarvis-warning, .jarvis-dark button.jarvis-restart,
.jarvis-dark button.jarvis-update-available { background-image: none; background-color: #2F6FED; border-color: #2459C2; color: #FFFFFF; }
.jarvis-dark button.jarvis-update, .jarvis-dark button.jarvis-enable { background-image: none; background-color: #20A464; border-color: #16814C; color: #FFFFFF; }
.jarvis-root button.jarvis-danger label, .jarvis-root button.jarvis-warning label,
.jarvis-root button.jarvis-restart label, .jarvis-root button.jarvis-update label,
.jarvis-root button.jarvis-update-available label, .jarvis-root button.jarvis-enable label,
.jarvis-root button.suggested-action label { color: #FFFFFF; }
.jarvis-root .jarvis-led-ready { color: #20C875; }
.jarvis-root .jarvis-led-warn { color: #F2A12C; }
.jarvis-root .jarvis-led-down { color: #E05260; }
.jarvis-root .jarvis-off { color: #8994A5; }
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
        self.activity_polling=False
        self.isolation_polling=False
        self.update_cancel=None;self.update_in_progress=False
        self.footer=footer;self.save=save;self.cancel=cancel;self.notebook=notebook
        self.saved_flags=None
        self.provider=Gtk.CssProvider();self.provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),self.provider,
                                                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        dialog.set_title('Jarvis');dialog.get_style_context().add_class('jarvis-root')
        try:self.selected_theme=appearance_theme()
        except (OSError,ValueError,RuntimeError):self.selected_theme='light'
        self.apply_theme(self.selected_theme)
        screen=Gdk.Screen.get_default()
        width,height=(screen.get_width(),screen.get_height()) if screen else (1024,768)
        dialog.set_default_size(min(1140,width-48),min(800,height-80))
        dialog.set_size_request(min(760,width-48),min(520,height-80))
        dialog.set_icon_name('audio-input-microphone')
        outer.remove(notebook)
        self.layout=Gtk.Box(spacing=0)
        outer.pack_start(self.layout,True,True,0);outer.reorder_child(self.layout,0)
        self.nav=Gtk.ListBox();self.nav.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.nav.set_size_request(180,-1);self.nav.get_style_context().add_class('jarvis-sidebar')
        sidebar=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        sidebar.get_style_context().add_class('jarvis-sidebar')
        brand=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=3);brand.set_border_width(12)
        brand.pack_start(label('Jarvis','jarvis-brand'),False,False,0)
        brand.pack_start(label('Control Centre','jarvis-subtitle'),False,False,0)
        brand.pack_start(label('by Unchained','jarvis-credit'),False,False,0)
        sidebar.pack_start(brand,False,False,0);sidebar.pack_start(self.nav,True,True,0)
        self.layout.pack_start(sidebar,False,False,0)
        self.stack=Gtk.Stack();self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120);self.layout.pack_start(self.stack,True,True,0)
        self.pages={}
        overview=self.page('overview','Dashboard','Your local voice assistant, at a glance.','view-grid-symbolic')
        self.build_overview(overview)
        general=self.page('general','General','Appearance and what starts when you sign in.','preferences-system-symbolic')
        self.build_general(general)
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
        dialog.connect('delete-event',self.request_close)
        dialog.connect('destroy',self.destroy)
        if not check_only:
            GLib.timeout_add_seconds(3,self.poll)
            GLib.timeout_add(120,self.tick)
            self.poll()
            self.refresh_startup()
            self.refresh_logging()
            GLib.timeout_add_seconds(1,self.logging_tick)

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
        if title:box.pack_start(label(title,'jarvis-heading'),False,False,0)
        if description:
            detail=label(description,'jarvis-subtitle');detail.set_max_width_chars(38)
            box.pack_start(detail,False,False,0)
        if isinstance(parent,Gtk.FlowBox):
            box.set_size_request(280,-1);parent.add(box)
        else:parent.pack_start(box,False,False,0)
        return box

    def card_grid(self,parent):
        grid=Gtk.FlowBox();grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_min_children_per_line(1);grid.set_max_children_per_line(2)
        grid.set_homogeneous(True);grid.set_column_spacing(12);grid.set_row_spacing(12)
        parent.pack_start(grid,False,False,0)
        return grid

    def action(self,parent,text,icon,callback,primary=False):
        obj=button(text,icon,callback)
        if primary:obj.get_style_context().add_class('suggested-action')
        parent.pack_start(obj,False,False,0);self.buttons.append(obj)
        return obj

    @staticmethod
    def colour(obj, style):
        context=obj.get_style_context()
        for name in ('jarvis-danger','jarvis-warning','jarvis-restart','jarvis-update','jarvis-update-available','jarvis-enable'):
            context.remove_class(name)
        if style:context.add_class(style)

    def build_overview(self,parent):
        cards=self.card_grid(parent)
        summary=self.card(cards,None);summary.get_style_context().add_class('jarvis-summary')
        headline=Gtk.Box(spacing=10);summary.pack_start(headline,False,False,0)
        self.overview_icon=Gtk.Image.new_from_icon_name('emblem-default-symbolic',Gtk.IconSize.LARGE_TOOLBAR)
        headline.pack_start(self.overview_icon,False,False,0)
        summary_text=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2)
        self.overview_health=label('Checking Jarvis…','jarvis-status')
        self.overview_update=label('Reading the local service state.','jarvis-subtitle')
        summary_text.pack_start(self.overview_health,False,False,0)
        summary_text.pack_start(self.overview_update,False,False,0)
        headline.pack_start(summary_text,True,True,0)
        self.overview_summary=summary
        self.status_label=self.overview_health;self.status_detail=self.overview_update
        controls=Gtk.Box(spacing=8);summary.pack_start(controls,False,False,0)
        self.start_stop=self.action(controls,'Run Jarvis','media-playback-start-symbolic',self.power,True)
        self.restart=self.action(controls,'Restart commands','view-refresh-symbolic',lambda _:self.task('Restarting commands',lambda:self.services('commands')))
        self.colour(self.restart,'jarvis-restart')
        summary.pack_start(label('Local AI · Private · Under Your Control','jarvis-privacy'),False,False,0)
        card=self.card(cards,'Voice services')
        service_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
        card.pack_start(service_box,False,False,0)
        self.service_labels={}
        for unit,title in [('ovos-audio.service','Speech'),('ovos-listener.service','Listener'),('ovos-core.service','Commands')]:
            row=Gtk.Box(spacing=9);row.get_style_context().add_class('jarvis-service-row')
            # A text dot follows our state colour even if a desktop icon theme
            # substitutes a coloured recording icon for the symbolic name.
            led=label('●')
            led.get_style_context().add_class('jarvis-led')
            name=label(title,'jarvis-service-name')
            state=Gtk.Label(label='Checking…',xalign=1);state.get_style_context().add_class('jarvis-service-state')
            row.pack_start(led,False,False,0);row.pack_start(name,True,True,0);row.pack_end(state,False,False,0)
            service_box.pack_start(row,False,False,0);self.service_labels[unit]=(led,state)
        quick=self.card_grid(parent)
        self.quiet_descriptions=Gtk.SizeGroup(mode=Gtk.SizeGroupMode.VERTICAL)
        card=self.card(quick,'Microphone','Pause Jarvis listening. Other applications can still use your microphone.')
        self.quiet_descriptions.add_widget(card.get_children()[1])
        card.set_hexpand(True)
        self.mic=self.action(card,'Checking microphone…','audio-input-microphone-symbolic',lambda _:self.task('Updating microphone',microphone_action))
        self.colour(self.mic,'jarvis-warning')
        card=self.card(quick,'Need quiet?','Stop speech, reading and the current request immediately.')
        self.quiet_descriptions.add_widget(card.get_children()[1])
        card.set_hexpand(True)
        self.emergency=button('Stop speaking','media-playback-stop-symbolic',self.stop_speech)
        self.colour(self.emergency,'jarvis-danger')
        card.pack_start(self.emergency,False,False,0)
        self.emergency_note=label('Available even while Jarvis is restarting.','jarvis-subtitle')
        card.pack_start(self.emergency_note,False,False,0)
        recent=self.card(parent,None)
        header=Gtk.Box(spacing=10);recent.pack_start(header,False,False,0)
        header.pack_start(label('Recent Activity','jarvis-heading'),True,True,0)
        self.recent_refresh=self.action(header,'Refresh','view-refresh-symbolic',lambda _:self.refresh_recent())
        self.recent_status=label('','jarvis-subtitle');recent.pack_start(self.recent_status,False,False,0)
        self.recent_rows=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2)
        recent.pack_start(self.recent_rows,False,False,0)
        recent.pack_start(label('This session only. No dictated text or search queries.','jarvis-credit'),False,False,0)
        self.render_recent([])

    def apply_theme(self,selected):
        context=self.dialog.get_style_context()
        for value in ('light','dark'):context.remove_class('jarvis-'+value)
        context.add_class('jarvis-'+selected)
        self.selected_theme=selected

    def change_theme(self,combo):
        selected=combo.get_active_id()
        if selected is None or selected==self.selected_theme:return
        try:
            from control_runtime import save_with_lock
            save_with_lock(lambda:save_appearance(selected))
        except Exception as error:
            combo.set_active_id(self.selected_theme)
            self.show_activity('Could not save appearance: '+str(error),False)
            return
        self.apply_theme(selected)

    def render_recent(self,rows):
        for child in self.recent_rows.get_children():child.destroy()
        if not rows:
            self.recent_rows.pack_start(label('Your next completed action will appear here.','jarvis-subtitle'),False,False,0)
        for text,stamp,success in rows[:5]:
            row=Gtk.Box(spacing=12);row.get_style_context().add_class('jarvis-recent-row')
            row.pack_start(Gtk.Image.new_from_icon_name('emblem-default-symbolic' if success else 'dialog-warning-symbolic',Gtk.IconSize.MENU),False,False,0)
            row.pack_start(label(text),True,True,0)
            time_label=Gtk.Label(label=stamp,xalign=1);time_label.get_style_context().add_class('jarvis-subtitle')
            row.pack_end(time_label,False,False,0);self.recent_rows.pack_start(row,False,False,0)
        self.recent_rows.show_all()

    def refresh_recent(self):
        if self.activity_polling or self.check_only:return
        if not self.running:
            self.render_recent([]);self.recent_status.set_text('Start Jarvis to see this session’s actions.');return
        self.activity_polling=True
        self.recent_status.set_text('Refreshing…')
        def read():
            arguments=[str(Path.home()/'.venvs/ovos/bin/python'),'-I',
                       str(Path(__file__).with_name('read_activity.py'))]
            try:
                output=subprocess.run(arguments,capture_output=True,text=True,timeout=6,check=True).stdout
            except subprocess.TimeoutExpired as error:
                # A completed snapshot can arrive before bus cleanup finishes.
                # subprocess.run stops only this reader; still validate its frame.
                output=error.stdout or ''
                if isinstance(output,bytes):output=output.decode('utf-8',errors='replace')
            spec=importlib.util.spec_from_file_location('jarvis_activity_view',Path(__file__).resolve().parents[1]/'ovos_skill_jarvis_dispatcher/activity.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            return module.display_output(output)
        def done(rows,error):
            self.activity_polling=False
            if not self.alive:return False
            if not self.running:
                self.render_recent([]);self.recent_status.set_text('Start Jarvis to see this session’s actions.')
            elif error is not None:
                self.recent_status.set_text('Activity unavailable. Try Refresh.')
            else:
                self.render_recent(rows);self.recent_status.set_text('')
            return False
        worker(read,done)

    def build_voice(self,parent):
        parent=self.card_grid(parent)
        config=read_json(Path.home()/'.config/jarvis/capabilities.json')
        audio=audio_settings()
        wake=self.card(parent,'Wake phrase','One active phrase. Hey Jarvis uses the reviewed model; a custom replacement uses local Vosk.')
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
        self.action(speech_note,'Open Speech Note','audio-x-generic-symbolic',self.speech_note)
        self.action(speech_note,'Setup guide…','help-browser-symbolic',self.speech_note_guide)

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
                  lambda:speech_note_action(action),on_success=lambda _value:'Speech Note opened.')
        return False

    def speech_note_guide(self,_button):
        self.task('Preparing setup guide…',lambda:speech_note_action('guide'),on_success=self.show_speech_note_guide)

    def show_speech_note_guide(self,text):
        guide=Gtk.Dialog(title='Speech Note setup',transient_for=self.dialog,modal=True)
        guide.set_default_size(560,420);guide.add_button('Close',Gtk.ResponseType.CLOSE)
        content=guide.get_content_area();content.set_border_width(18);content.set_spacing(12)
        scroll=Gtk.ScrolledWindow();scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        view=Gtk.TextView();view.set_editable(False);view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        view.set_monospace(True);view.get_buffer().set_text(str(text));scroll.add(view)
        content.pack_start(scroll,True,True,0)
        rule=next((line.split('Pattern:',1)[1].strip() for line in str(text).splitlines() if 'Pattern:' in line),'')
        def copy_rule(_button):
            clipboard=Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD);clipboard.set_text(rule,-1)
            GLib.timeout_add(1000,lambda:(clipboard.clear(),False)[1])
        content.pack_start(button('Copy rule (clears after 1 second)','edit-copy-symbolic',copy_rule),False,False,0)
        guide.show_all();guide.run();guide.destroy()
        return 'Speech Note setup guide closed.'

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
        isolation=self.card(parent,'Isolation','Network restrictions for Jarvis only. Weather and music can stay online.')
        row=Gtk.Box(spacing=10);isolation.pack_start(row,False,False,0)
        self.isolation_led=label('●','jarvis-off');row.pack_start(self.isolation_led,False,False,0)
        self.isolation_label=label('Not checked','jarvis-heading');row.pack_start(self.isolation_label,True,True,0)
        self.isolation_core=label('Core network restriction: not checked','jarvis-subtitle')
        self.isolation_model=label('Private model restriction: not checked','jarvis-subtitle')
        self.isolation_note=label('Active policy is separate from a passed network test.','jarvis-subtitle')
        for item in (self.isolation_core,self.isolation_model,self.isolation_note):isolation.pack_start(item,False,False,0)
        row=Gtk.Box(spacing=8);isolation.pack_start(row,False,False,0)
        self.action(row,'Refresh status','view-refresh-symbolic',lambda _:self.refresh_isolation())
        self.action(row,'Check isolation','security-high-symbolic',lambda _:self.maintain('isolation'))
        cards=self.card_grid(parent)
        actions=self.card(cards,'Keep Jarvis running')
        grid=Gtk.Box(spacing=8);actions.pack_start(grid,False,False,0)
        for name,icon,key in [('Health check','emblem-default-symbolic','health')]:
            self.action(grid,name,icon,lambda _,k=key:self.maintain(k))
        backup=self.card(cards,'Settings backup','Export app choices, spoken names, commands, shortcuts and voice settings. Saved configuration may contain credentials; keep the archive private.')
        self.action(backup,'Export settings…','document-save-as-symbolic',self.export_backup)
        support=self.card(parent,'Support')
        row=Gtk.Box(spacing=8);support.pack_start(row,False,False,0)
        for name,icon,key in [('Create report','document-save-symbolic','report'),('Recent logs','text-x-generic-symbolic','logs'),('About','help-about-symbolic','about')]:
            self.action(row,name,icon,lambda _,k=key:self.maintain(k))
        support.pack_start(label('Reports stay on this computer. Location coordinates are redacted, but Recent Logs may contain your spoken words.','jarvis-subtitle'),False,False,0)
        advanced=Gtk.Expander(label='Advanced');parent.pack_start(advanced,False,False,0)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);advanced.add(box)
        box.set_border_width(12)
        box.pack_start(label('Restart all voice services if a normal restart did not help. Uninstall offers separate choices for settings, the Qwen model and OVOS.','jarvis-subtitle'),False,False,0)
        self.action(box,'Restart full voice system','view-refresh-symbolic',lambda _:self.task('Restarting voice system',lambda:self.services('restart')))
        self.action(box,'Uninstall Jarvis…','edit-delete-symbolic',self.uninstall)
        self.details=Gtk.Expander(label='Results and details');parent.pack_start(self.details,True,True,0)
        scroll=Gtk.ScrolledWindow();scroll.set_min_content_height(260)
        self.output=Gtk.TextView();self.output.set_editable(False);self.output.set_monospace(True)
        self.output.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);scroll.add(self.output);self.details.add(scroll)
        self.output.get_buffer().set_text('Results will appear here.')

    def refresh_isolation(self):
        if self.check_only or self.isolation_polling:return
        self.isolation_polling=True
        def done(value,error):
            self.isolation_polling=False
            if not self.alive:return False
            state='attention' if error else value['summary']
            self.isolation_label.set_text({'active':'Isolation active','off':'Isolation off','attention':'Needs attention'}[state])
            context=self.isolation_led.get_style_context()
            for style in ('jarvis-led-ready','jarvis-led-warn','jarvis-off'):context.remove_class(style)
            context.add_class({'active':'jarvis-led-ready','off':'jarvis-off','attention':'jarvis-led-warn'}[state])
            self.isolation_core.set_text('Core network restriction: '+('unavailable' if error else 'configured' if value['core'] else 'not confirmed'))
            self.isolation_model.set_text('Private model restriction: '+('unavailable' if error else 'configured' if value['model'] else 'not confirmed'))
            self.isolation_note.set_text('Status unavailable. Use Check isolation for details.' if error else value['verification'])
            return False
        worker(isolation_policy_status,done)

    def build_updates(self,parent):
        current=self.card(parent,'Jarvis updates','Updates are checked only when requested. Your settings and downloaded models are preserved.')
        self.update_label=label('Your version: checking…\nLatest version: checking…\nRelease date: checking…','jarvis-subtitle')
        current.pack_start(self.update_label,False,False,0)
        row=Gtk.Box(spacing=8);current.pack_start(row,False,False,0)
        self.action(row,'Check now','view-refresh-symbolic',lambda _:self.maintain('updates'))
        self.update_health=label('Not checked','jarvis-subtitle');current.pack_start(self.update_health,False,False,0)
        self.install_update=self.action(row,'Check for updates','software-update-available-symbolic',self.install_release)
        self.install_update.set_sensitive(False)
        self.stop_update=button('Stop update','process-stop-symbolic',self.cancel_update)
        self.stop_update.set_no_show_all(True);self.stop_update.hide()
        row.pack_start(self.stop_update,False,False,0)
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
            if kind=='isolation':self.refresh_isolation()
            return {'health':'Health check complete. See results below.','report':'Report created. Location shown below.','updates':'Update check complete.','logs':'Recent logs loaded.','about':'Version information loaded.',
                    'isolation':'Isolation check complete. See results below.'}[kind]
        if kind=='isolation':
            self.task('Checking isolation… Network and model tests can take several minutes.',
                      lambda:maintenance(kind,progress=self.report),on_success=result)
        else:self.task('Working…',lambda:maintenance(kind),on_success=result)

    def install_release(self,_button):
        if not self.latest:return
        prompt=Gtk.MessageDialog(transient_for=self.dialog,modal=True,message_type=Gtk.MessageType.QUESTION,
                                 buttons=Gtk.ButtonsType.OK_CANCEL,text='Install Jarvis '+self.latest+'?')
        prompt.format_secondary_text('This runs the existing updater and may restart Jarvis.')
        answer=prompt.run();prompt.destroy()
        if answer==Gtk.ResponseType.OK:
            self.update_cancel=threading.Event();self.update_in_progress=True
            self.stop_update.set_label('Stop update');self.stop_update.set_sensitive(True)
            self.stop_update.show()
            def installed(result):
                self.output.get_buffer().set_text(str(result))
                self.details.set_expanded(True)
                relaunch_control_center()
                GLib.idle_add(self.dialog.response, Gtk.ResponseType.CANCEL)
                return 'Update installed. Reopening Jarvis…'
            self.task('Installing update…',
                      lambda:maintenance('install',cancel_event=self.update_cancel),
                      on_success=installed,on_finish=self.finish_update)

    def cancel_update(self,_button=None):
        if not self.update_in_progress or self.update_cancel is None:return
        prompt=Gtk.MessageDialog(transient_for=self.dialog,modal=True,
                                 message_type=Gtk.MessageType.WARNING,
                                 buttons=Gtk.ButtonsType.OK_CANCEL,
                                 text='Stop the current Jarvis update?')
        prompt.format_secondary_text('The updater will stop safely. If files were already changed, its rollback protection remains available.')
        answer=prompt.run();prompt.destroy()
        if answer!=Gtk.ResponseType.OK:return
        self.update_cancel.set();self.stop_update.set_sensitive(False)
        self.stop_update.set_label('Stopping update…')
        self.show_activity('Stopping update safely…',True)

    def finish_update(self):
        self.update_in_progress=False;self.update_cancel=None
        self.stop_update.hide();self.stop_update.set_sensitive(True)

    def services(self,action):return service_action(action,self.report)

    def build_general(self,parent):
        appearance=self.card(parent,'Appearance','Choose a look for Jarvis. Your desktop theme stays as it is.')
        self.theme_picker=Gtk.ComboBoxText()
        self.theme_picker.append('light','Light');self.theme_picker.append('dark','Dark')
        self.theme_picker.set_active_id(getattr(self,'selected_theme','light'))
        self.theme_picker.connect('changed',self.change_theme)
        appearance.pack_start(self.theme_picker,False,False,0)
        logging_card=self.card(parent,'Logging','Diagnostics capture technical events for five minutes, then clear automatically. Spoken and written content is excluded.')
        self.logging_picker=Gtk.ComboBoxText()
        self.logging_picker.append('off','No logs')
        self.logging_picker.append('diagnostics','Diagnostics for 5 minutes')
        self.logging_picker.set_active_id('off')
        self.logging_picker.connect('changed',self.change_logging)
        logging_card.pack_start(self.logging_picker,False,False,0)
        self.logging_note=label('No logs','jarvis-subtitle')
        logging_card.pack_start(self.logging_note,False,False,0)
        card=self.card(parent,'Startup')
        self.startup_switches={}
        for component,title,detail in (
                ('tray','Start app minimised at login','Show the tray icon without opening this window.'),
                ('voice','Start voice services at login','Enable Jarvis voice services automatically when you sign in.')):
            row=Gtk.Box(spacing=16);card.pack_start(row,False,False,0)
            text=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
            text.pack_start(label(title,'jarvis-default-label'),False,False,0)
            text.pack_start(label(detail,'jarvis-subtitle'),False,False,0)
            row.pack_start(text,True,True,0)
            switch=Gtk.Switch();switch.set_valign(Gtk.Align.CENTER);switch.set_sensitive(False)
            switch.get_accessible().set_name(title)
            switch.connect('state-set',self.change_startup,component)
            row.pack_end(switch,False,False,0)
            self.startup_switches[component]=switch;self.buttons.append(switch)
        self.startup_note=label('Checking login settings…','jarvis-subtitle')
        card.pack_start(self.startup_note,False,False,0)

    def change_logging(self,picker):
        if getattr(self,'updating_logging',False):return
        from privacy_logging import set_mode
        enabled=picker.get_active_id()=='diagnostics'
        try:
            set_mode(enabled)
        except (OSError,ValueError,RuntimeError):
            self.logging_note.set_text('Logging setting could not be changed. No new diagnostic capture was enabled.')
            return
        self.refresh_logging()

    def refresh_logging(self):
        from privacy_logging import mode
        current=mode()
        self.updating_logging=True
        try:
            self.logging_picker.set_active_id('diagnostics' if current['enabled'] else 'off')
            self.logging_note.set_text('Diagnostics: '+str(current['remaining'])+' seconds remaining.'
                                      if current['enabled'] else 'No logs')
        finally:self.updating_logging=False

    def logging_tick(self):
        if not self.alive:return False
        self.refresh_logging()
        return True

    def change_startup(self,_switch,enabled,component):
        if getattr(self,'updating_startup',False):return False
        if self.state['busy'] or self.busy:return True
        from control_runtime import save_with_lock
        self.task('Saving login setting',lambda:save_with_lock(lambda:set_startup(**{component+'_enabled':bool(enabled)})),
                  on_finish=self.refresh_startup)
        return True

    def refresh_startup(self):
        def done(value,error):
            if not self.alive:return False
            self.updating_startup=True
            try:
                if error:
                    self.startup_note.set_text('Login settings need attention. See Maintenance for details.')
                    for switch in self.startup_switches.values():switch.set_sensitive(False)
                else:
                    for component,switch in self.startup_switches.items():
                        switch.set_active(value[component+'_enabled'])
                        switch.set_sensitive((component=='tray' or value['target_state'] in {'enabled','disabled'})
                                             and not self.state['busy'] and not self.busy)
                    self.startup_note.set_text('These options affect the next login. Run/Stop on Dashboard controls this session.'
                        if value['consistent'] else 'Saved and system login settings differ. Review the two options above.')
            finally:self.updating_startup=False
            return False
        worker(startup_status,done)

    def power(self,_button):
        action='start' if not getattr(self,'running',False) else 'stop'
        self.task('Starting Jarvis' if action=='start' else 'Stopping Jarvis',lambda:self.services(action))

    def report(self,text):GLib.idle_add(self.show_activity,text,True)

    def show_activity(self,text,busy=False):
        if not self.alive:return False
        message=' '.join(str(text or '').splitlines())[:180]
        self.activity_label.set_line_wrap(False);self.activity_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.activity_label.set_text(message);self.activity.show();self.activity_label.show()
        if busy:self.progress.show()
        else:self.progress.hide()
        return False

    def task(self,title,work,on_success=None,on_finish=None):
        if self.state['busy'] or self.busy:return
        self.busy=True;self.state['busy']=True
        self.notebook.set_sensitive(False);self.save.set_sensitive(False);self.cancel.set_sensitive(False)
        for obj in self.buttons:obj.set_sensitive(False)
        self.show_activity(title,True)
        def done(value,error):
            if not self.alive:return False
            if on_finish:on_finish()
            self.busy=False;self.state['busy']=False
            self.notebook.set_sensitive(True);self.save.set_sensitive(True);self.cancel.set_sensitive(True)
            for obj in self.buttons:obj.set_sensitive(True)
            if error:
                self.output.get_buffer().set_text(error);self.details.set_expanded(True)
                self.show_activity('Could not complete: '+error,False)
            else:
                try:message=on_success(value) if on_success else str(value)
                except Exception as exc:message='Completed, but refresh failed: '+str(exc)
                if not on_success and '\n' in str(value):
                    self.output.get_buffer().set_text(str(value));self.details.set_expanded(True)
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
                context=self.overview_summary.get_style_context()
                for style in ('jarvis-summary-good','jarvis-summary-update','jarvis-summary-warn'):context.remove_class(style)
                self.overview_icon.set_from_icon_name('dialog-warning-symbolic',Gtk.IconSize.LARGE_TOOLBAR)
                icon_context=self.overview_icon.get_style_context()
                for style in ('jarvis-led-ready','jarvis-led-warn','jarvis-off'):icon_context.remove_class(style)
                icon_context.add_class('jarvis-led-warn')
                for led,item in self.service_labels.values():
                    item.set_text('Unknown')
                    context=led.get_style_context()
                    for style in ('jarvis-led-ready','jarvis-led-warn','jarvis-led-down','jarvis-off'):context.remove_class(style)
                    context.add_class('jarvis-led-warn')
                return False
            names={'ready':'System Online','muted':'Microphone paused','stopped':'System Offline','starting':'Starting…','failed':'Needs attention'}
            self.status_label.set_text(names[value['state']])
            self.running=value['services'].get('ovos-core.service')=='active'
            self.start_stop.set_image(Gtk.Image.new_from_icon_name('media-playback-stop-symbolic' if self.running else 'media-playback-start-symbolic',Gtk.IconSize.BUTTON))
            self.status_detail.set_text('Ready for your next command.' if value['state']=='ready' else
                                       'Use the controls below, or check Maintenance for details.')
            self.start_stop.set_label('Stop Jarvis' if self.running else 'Run Jarvis')
            self.start_stop.set_image(Gtk.Image.new_from_icon_name('media-playback-stop-symbolic' if self.running else 'media-playback-start-symbolic', Gtk.IconSize.BUTTON))
            if self.running:self.start_stop.get_style_context().remove_class('suggested-action')
            else:self.start_stop.get_style_context().add_class('suggested-action')
            self.mic.set_label('Pause microphone' if value['microphone'] else 'Enable microphone')
            self.colour(self.start_stop,'jarvis-danger' if self.running else None)
            self.colour(self.mic,'jarvis-warning' if value['microphone'] else 'jarvis-enable')
            for unit,(led,item) in self.service_labels.items():
                service_state=value['services'].get(unit,'unknown')
                item.set_text('Ready' if service_state=='active' and value['state']=='ready' else service_state.capitalize())
                context=led.get_style_context()
                for style in ('jarvis-led-ready','jarvis-led-warn','jarvis-led-down','jarvis-off'):context.remove_class(style)
                context.add_class('jarvis-led-ready' if service_state=='active' and value['state'] in {'ready','muted'} else
                                  'jarvis-led-warn' if service_state=='active' else
                                  'jarvis-led-warn' if service_state=='activating' else
                                  'jarvis-off' if service_state=='inactive' else 'jarvis-led-down')
            if not self.state['busy']:
                self.restart.set_sensitive(self.running)
                information=update_status();self.latest=information['latest'] if information['available'] else None
                date=information['release_date'] or 'Not recorded'
                detail=('Your version: '+information['installed']+'\nLatest version: '+information['latest']+'\nRelease date: '+date)
                self.update_label.set_text(('Update available\n' if information['available'] else '')+detail)
                summary_context=self.overview_summary.get_style_context()
                icon_context=self.overview_icon.get_style_context()
                for style in ('jarvis-led-ready','jarvis-led-warn','jarvis-off'):icon_context.remove_class(style)
                icon_context.add_class('jarvis-led-ready' if value['state']=='ready' else 'jarvis-off' if value['state']=='stopped' else 'jarvis-led-warn')
                for style in ('jarvis-summary-good','jarvis-summary-update','jarvis-summary-warn'):summary_context.remove_class(style)
                if value['state']=='ready':
                    self.overview_icon.set_from_icon_name('emblem-default-symbolic',Gtk.IconSize.LARGE_TOOLBAR)
                    summary_context.add_class('jarvis-summary-good')
                else:
                    self.overview_icon.set_from_icon_name('media-record-symbolic' if value['state']=='stopped' else 'dialog-warning-symbolic',Gtk.IconSize.LARGE_TOOLBAR)
                    summary_context.add_class('jarvis-summary-warn')
                self.refresh_update_button(information)
            self.refresh_startup()
            self.refresh_recent()
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
        if row.key=='maintenance':self.refresh_isolation()

    def refresh_update_button(self,information):
        available=information['available']
        healthy=information['checked'] and not available and not information['failed']
        self.update_health.set_text('Check failed' if information['failed'] else 'Update available' if available else 'Not checked' if not healthy else '')
        self.update_health.get_style_context().remove_class('jarvis-led-ready')
        self.install_update.set_label('Update available ('+information['latest']+')' if available else 'Everything is up to date' if healthy else 'Check for updates')
        self.install_update.set_sensitive(available)
        self.colour(self.install_update,'jarvis-update-available' if available else 'jarvis-update' if healthy else None)

    def show_tab(self,tab='overview'):
        if tab=='dashboard':tab='overview'
        key='apps' if tab in {'applications','commands','apps'} else tab
        self.nav.select_row(self.pages.get(key,self.pages['overview']))
        if tab in {'applications','commands'}:self.notebook.set_current_page(1 if tab=='commands' else 0)
        self.dialog.present()

    def destroy(self,*_args):
        if self.update_cancel is not None:self.update_cancel.set()
        self.alive=False

    def request_close(self,*_args):
        if not self.update_in_progress:return False
        prompt=Gtk.MessageDialog(transient_for=self.dialog,modal=True,
                                 message_type=Gtk.MessageType.WARNING,
                                 buttons=Gtk.ButtonsType.OK_CANCEL,
                                 text='An update is still running.')
        prompt.format_secondary_text('Stop the update and close Jarvis?')
        answer=prompt.run();prompt.destroy()
        if answer!=Gtk.ResponseType.OK:return True
        if self.update_cancel is not None:self.update_cancel.set()
        return False
