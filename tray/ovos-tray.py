#!/usr/bin/python3
"""Compact Jarvis tray. Recovery controls live in the main window."""
import fcntl
import subprocess
import sys
import threading
from pathlib import Path
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk, GLib

SOURCE = Path.home()/'.local/src/ovos-skill-jarvis-dispatcher'
sys.path.insert(0,str(SOURCE/'scripts'))
from control_runtime import status, microphone_action, speech_stop, update_available


def tray_image(icon_dir, state, update, paused):
    from gi.repository import GdkPixbuf
    base='ready' if state=='muted' else state
    svg=(icon_dir/f'ovos-{base}{"-update" if update else ""}.svg').read_text()
    if paused:
        svg=svg.replace('</svg>', '<circle cx="52" cy="51" r="11" fill="#fff"/>'
                        '<circle cx="52" cy="51" r="8" fill="#ef9b0f"/></svg>')
    loader=GdkPixbuf.PixbufLoader.new_with_type('svg')
    loader.set_size(64,64);loader.write(svg.encode());loader.close()
    return loader.get_pixbuf()


class OvosTray:
    def __init__(self):
        self.polling=False;self.busy=False;self.emergency_busy=False
        self.alive=True;self.microphone=None
        self.status_icon=Gtk.StatusIcon();self.status_icon.set_visible(True)
        self.status_icon.connect('activate',self._open)
        self.status_icon.connect('popup-menu',self._menu)
        self.menu=Gtk.Menu()
        self._item('Open Jarvis…','preferences-system-symbolic',self._open)
        self.mic_item=self._item('Microphone…','audio-input-microphone-symbolic',self._mic)
        self._item('Stop speaking','media-playback-stop-symbolic',self._silence)
        self.menu.append(Gtk.SeparatorMenuItem())
        self._item('Quit tray','application-exit-symbolic',self._quit)
        self.menu.show_all();self._poll()

    def _item(self,title,icon,callback):
        item=Gtk.ImageMenuItem(label=title)
        item.set_image(Gtk.Image.new_from_icon_name(icon,Gtk.IconSize.MENU));item.set_always_show_image(True)
        item.connect('activate',callback);self.menu.append(item);return item

    def _open(self,*_args):
        subprocess.Popen([str(Path.home()/'.local/bin/jarvis-setup'),'--gui','--tab','overview'],
                         stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)

    def _menu(self,_icon,button,timestamp):
        self.menu.popup(None,None,Gtk.StatusIcon.position_menu,self.status_icon,button,timestamp)

    def _job(self,work,finish):
        def background():
            try:value,error=work(),None
            except Exception as exc:value,error=None,str(exc)
            GLib.idle_add(finish,value,error)
        threading.Thread(target=background,daemon=True).start()

    def _mic(self,*_args):
        if self.busy:return
        self.busy=True;self.mic_item.set_sensitive(False)
        def done(value,error):
            self.busy=False;self.mic_item.set_sensitive(True)
            if error:self.status_icon.set_tooltip_text(error);self._notify(error)
            self._poll();return False
        self._job(microphone_action,done)

    @staticmethod
    def _notify(text):
        try:subprocess.Popen(['notify-send','Jarvis',str(text)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except OSError:pass

    def _silence(self,*_args):
        if self.emergency_busy:return
        self.emergency_busy=True
        def done(value,error):
            self.emergency_busy=False
            if error:self._notify(error)
            return False
        self._job(speech_stop,done)

    def _poll(self):
        if not self.alive:return False
        if self.polling or self.busy:return True
        self.polling=True
        def query():return status(),update_available()
        def done(value,error):
            self.polling=False
            if not self.alive:return False
            if error:
                self.status_icon.set_from_icon_name('dialog-warning-symbolic')
                self.status_icon.set_tooltip_text('Jarvis: status unavailable\n'+error);return False
            result,update=value
            state=result['state']
            icon_dir=Path.home()/'.local/share/icons/ovos-tray'
            paused=not result['microphone'] and result['services'].get('ovos-core.service')=='active'
            try:self.status_icon.set_from_pixbuf(tray_image(icon_dir,state,update,paused))
            except (OSError,GLib.Error):self.status_icon.set_from_icon_name('audio-input-microphone-symbolic')
            self.microphone=result['microphone']
            self.mic_item.set_label('Pause microphone' if self.microphone else 'Enable microphone')
            self.status_icon.set_tooltip_text('Jarvis: '+state+('\nMicrophone paused (amber dot)' if paused else '')+'\nClick to open'+ ('\nUpdate available: '+update if update else ''))
            return False
        self._job(query,done);return True

    def _quit(self,*_args):self.alive=False;Gtk.main_quit()

    def run(self):GLib.timeout_add_seconds(3,self._poll);Gtk.main()


if __name__=='__main__':
    lock_path=Path.home()/'.cache/jarvis-tray.lock';lock_path.parent.mkdir(parents=True,exist_ok=True)
    lock=open(lock_path,'w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise SystemExit(0)
    OvosTray().run()
