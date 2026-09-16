#!/usr/bin/env python3
"""Small Cinnamon tray controller for the local OVOS services."""

import json
import re
import subprocess
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk


SERVICES = (
    "ovos-core.service",
    "ovos-listener.service",
    "ovos-audio.service",
)
POLL_SECONDS = 3


class OvosTray:
    def __init__(self):
        self.icon_dir = (
            Path.home() / ".local/share/icons/ovos-tray"
        )
        self.restart_pending = False
        self.core_started = None
        self.ready_observed = False
        self.update_release = None
        self.update_item = None
        self.status_icon = Gtk.StatusIcon()
        self.status_icon.set_visible(True)
        self.status_icon.connect("popup-menu", self._show_menu)
        self.status_icon.connect("activate", self._show_menu)
        self.menu = self._build_menu()
        self._poll()

    @staticmethod
    def _run(*command):
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )

    def _service_states(self):
        states = {}
        for service in SERVICES:
            result = self._run(
                "systemctl", "--user", "is-active", service
            )
            states[service] = result.stdout.strip() or "unknown"
        return states

    def _jarvis_ready(self, core_started):
        result = self._run(
            "journalctl",
            "--user",
            "-u",
            "ovos-core.service",
            "--since",
            core_started,
            "--no-pager",
            "-o",
            "cat",
        )
        return (
            "ovos-skill-jarvis-dispatcher.openvoiceos is ready"
            in result.stdout
            or "Skill ovos-skill-jarvis-dispatcher.openvoiceos "
            "loaded successfully" in result.stdout
        )

    def _state(self, states):
        values = set(states.values())
        if values == {"active"}:
            started = self._run(
                "systemctl",
                "--user",
                "show",
                "ovos-core.service",
                "--property=ActiveEnterTimestamp",
                "--value",
            ).stdout.strip()
            if started != self.core_started:
                self.core_started = started
                self.ready_observed = False
            if not self.ready_observed:
                self.ready_observed = self._jarvis_ready(started)
            if not self.ready_observed:
                return "starting"
            self.restart_pending = False
            return "ready"
        if values <= {"inactive", "unknown"}:
            return "stopped"
        if "failed" in values:
            return "failed"
        return "starting"

    @staticmethod
    def _version_key(value):
        match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(value).strip())
        return tuple(int(part) for part in match.groups()) if match else None

    @staticmethod
    def _json(path):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError, json.JSONDecodeError):
            return {}

    def _available_update(self):
        state_dir = Path.home() / ".local/state/jarvis"
        update = self._json(state_dir / "updates/latest.json")
        current = self._json(state_dir / "current.json")
        latest = self._version_key(update.get("latest", ""))
        installed = self._version_key(current.get("version", ""))
        if update.get("update_available") is True and latest and installed:
            if latest > installed:
                return str(update["latest"])
        return None

    def _poll(self):
        try:
            states = self._service_states()
            state = self._state(states)
            self.update_release = self._available_update()
            suffix = "-update" if self.update_release else ""
            self.status_icon.set_from_file(
                str(self.icon_dir / f"ovos-{state}{suffix}.svg")
            )
            details = ", ".join(
                f"{name.removeprefix('ovos-').removesuffix('.service')}: "
                f"{value}"
                for name, value in states.items()
            )
            tooltip = f"Voice system: {state}\n{details}"
            if self.update_release:
                tooltip += f"\nJarvis {self.update_release} is available"
            self.status_icon.set_tooltip_text(tooltip)
            if self.update_item is not None:
                label = (
                    f"Update available: {self.update_release}…"
                    if self.update_release else "Check for updates"
                )
                self.update_item.set_label(label)
        except Exception as error:
            self.status_icon.set_from_file(
                str(self.icon_dir / "ovos-failed.svg")
            )
            self.status_icon.set_tooltip_text(
                f"Voice-system tray error: {error}"
            )
        return GLib.SOURCE_CONTINUE

    def _background(self, command):
        self.restart_pending = True
        self.status_icon.set_from_file(
            str(self.icon_dir / "ovos-starting.svg")
        )
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    @staticmethod
    def _commands(_item=None):
        subprocess.Popen(
            [str(Path.home() / ".local/bin/jarvis-command-editor")],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    @staticmethod
    def _setup(_item=None):
        subprocess.Popen(
            [str(Path.home() / ".local/bin/jarvis-setup"), "--gui"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    @staticmethod
    def _terminal_command(command):
        terminal = "x-terminal-emulator"
        subprocess.Popen(
            [terminal, "-e", "bash", "-lc", f"{command}; printf '\\n'; read -r -p 'Press Enter to close'"],
            start_new_session=True,
        )

    def _health(self, _item=None):
        self._terminal_command("jarvis-health-check && echo 'Jarvis health check passed.'")

    def _report(self, _item=None):
        self._terminal_command("jarvis-report && echo 'Support report saved in Downloads.'")

    def _updates(self, _item=None):
        command = (
            "jarvis-update install"
            if self.update_release else "jarvis-update check"
        )
        self._terminal_command(command)

    def _restart(self, _item=None):
        self._background(
            [str(Path.home() / ".local/bin/jarvis-restart")]
        )

    def _full_restart(self, _item=None):
        self._background(
            [
                str(Path.home() / ".local/bin/jarvis-restart"),
                "--full",
            ]
        )

    def _start(self, _item=None):
        self._background(
            ["systemctl", "--user", "start", *SERVICES]
        )

    def _stop(self, _item=None):
        self.restart_pending = False
        subprocess.Popen(
            ["systemctl", "--user", "stop", *SERVICES],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    @staticmethod
    def _logs(_item=None):
        command = (
            "journalctl --user -u ovos-core.service "
            "-u ovos-listener.service -u ovos-audio.service "
            "-n 200 -f"
        )
        subprocess.Popen(
            ["x-terminal-emulator", "-e", "bash", "-lc", command],
            start_new_session=True,
        )

    def _build_menu(self):
        menu = Gtk.Menu()
        entries = [
            ("Setup…", self._setup),
            ("Health check", self._health),
            ("Create AI support report", self._report),
            ("Check for updates", self._updates),
            ("Restart Commands", self._restart),
            ("Restart Voice System", self._full_restart),
            ("Start Voice System", self._start),
            ("Stop Voice System", self._stop),
            ("Recent logs", self._logs),
            ("Exit tray", lambda _item: Gtk.main_quit()),
        ]
        editor = Path.home() / ".local/bin/jarvis-command-editor"
        if editor.is_file():
            entries.insert(1, ("Commands…", self._commands))
        for label, callback in entries:
            item = Gtk.MenuItem(label=label)
            item.connect("activate", callback)
            if label == "Check for updates":
                self.update_item = item
            menu.append(item)
        menu.show_all()
        return menu

    def _show_menu(self, *_args):
        self.menu.popup(
            None,
            None,
            Gtk.StatusIcon.position_menu,
            self.status_icon,
            0,
            Gtk.get_current_event_time(),
        )

    def run(self):
        GLib.timeout_add_seconds(POLL_SECONDS, self._poll)
        Gtk.main()


if __name__ == "__main__":
    OvosTray().run()
