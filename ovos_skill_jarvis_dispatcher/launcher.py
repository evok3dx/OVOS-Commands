"""Approved app launch commands using the pinned OVOS launcher methods.

Speech never supplies a command. Jarvis selects an integration; local desktop
entries and fixed Flatpak IDs provide its launch command. Window handling stays
with jarvis-app-window. No additional skill or PHAL listeners are installed.
"""
from __future__ import annotations

import argparse
import configparser
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import uuid

from ._ovos_launcher import ApplicationLauncherSkill
from .profile import load_profile
from .discovery import desktop_roots

# Exact desktop IDs, never fuzzy names or a transcript-derived executable.
DESKTOP_IDS = {
    "brave": ("brave-browser.desktop", "brave-browser-stable.desktop"),
    "firefox": ("firefox.desktop", "org.mozilla.firefox.desktop"),
    "signal": ("signal-desktop.desktop",),
    "zoom": ("Zoom.desktop", "zoom.desktop"),
    "terminal": ("org.gnome.Terminal.desktop", "gnome-terminal.desktop"),
    "standard_notes": ("standard-notes.desktop", "standard-notes-appimage.desktop", "standardnotes.desktop"),
    "onlyoffice": ("onlyoffice-desktopeditors.desktop", "org.onlyoffice.desktopeditors.desktop"),
    "calculator": ("org.gnome.Calculator.desktop", "gnome-calculator.desktop", "galculator.desktop"),
    "settings": ("cinnamon-settings.desktop",),
    "files": ("nemo.desktop",),
}
FLATPAKS = {
    "brave": "com.brave.Browser", "firefox": "org.mozilla.firefox",
    "signal": "org.signal.Signal", "standard_notes": "org.standardnotes.standardnotes",
    "onlyoffice": "org.onlyoffice.desktopeditors", "zoom": "us.zoom.Zoom",
    "calculator": "org.gnome.Calculator",
}
BASIC_APPS = ("calculator", "settings", "files")
HELPER_IDS = {"notes": "standard_notes", "office": "onlyoffice"}


def desktop_command(integration, roots=None):
    """Use upstream metadata parsing, and GIO for desktop Exec semantics."""
    gio = shutil.which("gio")
    if not gio:
        return None
    roots = desktop_roots() if roots is None else roots
    for desktop_id in DESKTOP_IDS.get(integration, ()):
        for root in roots:
            path = root / desktop_id
            if not path.is_file():
                continue
            try:
                # Honour a user-level Hidden override instead of launching the
                # system entry it masks. NoDisplay entries are not new choices.
                raw = configparser.ConfigParser(interpolation=None)
                raw.read(path, encoding="utf-8")
                entry = raw["Desktop Entry"]
                if entry.getboolean("Hidden", False) or entry.getboolean("NoDisplay", False):
                    break
                info = ApplicationLauncherSkill.parse_desktop_file(str(path))
                if info.get("Type") != "Application" or not info.get("Exec"):
                    break
                candidate = entry.get("TryExec")
                if candidate and not shutil.which(candidate):
                    break
                # Do not split/trim Exec. GIO handles quotes, field codes, paths
                # and desktop activation. The selected file is locally owned
                # desktop configuration, not model output.
                return {"argv": [gio, "launch", str(path)], "kind": "desktop"}
            except (OSError, ValueError, KeyError, configparser.Error):
                break
    return None


def installed_flatpaks():
    flatpak = shutil.which("flatpak")
    if not flatpak:
        return None, set()
    try:
        out = subprocess.run([flatpak, "list", "--app", "--columns=application"],
                             capture_output=True, text=True, timeout=5, check=True)
        return flatpak, set(out.stdout.splitlines())
    except (OSError, subprocess.SubprocessError):
        return flatpak, set()


def discover(integrations=None):
    result = {}
    flatpak, installed = installed_flatpaks()
    for integration in (DESKTOP_IDS if integrations is None else integrations):
        # Respect the existing explicit Standard Notes override.
        if integration == "standard_notes" and os.environ.get("JARVIS_STANDARD_NOTES"):
            continue
        native = desktop_command(integration)
        app_id = FLATPAKS.get(integration)
        flat = ({"argv": [flatpak, "run", app_id], "kind": "flatpak"}
                if flatpak and app_id in installed else None)
        # Existing Brave helper prefers Flatpak. Other apps prefer their native
        # desktop entry; Flatpak is used when that entry is absent.
        selected = (flat or native) if integration == "brave" else (native or flat)
        if selected:
            result[integration] = selected
    return result


class _LaunchRequest:
    """Only the state needed by upstream launch_app; no voice skill instance."""
    def __init__(self, argv):
        self.settings = {"thresh": 1.0, "shell": False}
        self.applist = {"Jarvis Approved App": shlex.join(argv)}

    def acknowledge(self):
        pass  # Existing Jarvis handler provides its normal spoken confirmation.


def desktop_action(app_id, action):
    """Act only on a currently enabled, freshly discovered desktop entry.

    GIO interprets the complete desktop launch command, including Flatpak
    arguments and field codes. No transcript text becomes a command or path.
    Named window controls use exact desktop-provided class identity only.
    """
    if action not in {'open', 'focus', 'minimize', 'maximize', 'close'}:
        return False
    selected = load_profile().get('applications', {}).get(app_id)
    if not selected or not app_id.startswith('desktop_'):
        return False
    wmctrl = shutil.which('wmctrl')
    wm_class = selected.get('wm_class', '').casefold()
    window = None
    if wmctrl and wm_class:
        output = subprocess.run([wmctrl, '-lx'], capture_output=True, text=True,
                                timeout=3, check=True).stdout
        import re
        for line in output.splitlines():
            fields = line.split(None, 4)
            if len(fields) < 4 or not re.fullmatch(r'0x[0-9a-fA-F]+', fields[0]):
                continue
            value = fields[2].casefold()
            if value == wm_class or value.endswith('.' + wm_class):
                window = fields[0]
                break
    if window:
        if action in {'open', 'focus'}:
            argv = [wmctrl, '-ia', window]
        elif action == 'close':
            argv = [wmctrl, '-ic', window]
        elif action == 'maximize':
            argv = [wmctrl, '-ir', window, '-b', 'add,maximized_vert,maximized_horz']
        else:
            xdotool = shutil.which('xdotool')
            if not xdotool:
                return False
            argv = [xdotool, 'windowminimize', window]
        return subprocess.run(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=5, check=False).returncode == 0
    if action != 'open':
        return False
    gio = shutil.which('gio')
    if not gio:
        return False
    return start_desktop([gio, 'launch', selected['path']])


def start_desktop(command):
    """Keep launched children alive after GIO exits; wait for startup only."""
    from ovos_utils.log import LOG
    systemd = shutil.which('systemd-run')
    if not systemd:
        return False
    argv = [systemd, '--user', '--quiet', '--collect',
            '--property=Type=exec', '--property=ExitType=cgroup',
            '--unit=jarvis-launch-' + uuid.uuid4().hex, '--', *command]
    try:
        result = subprocess.run(argv, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, text=True, timeout=12, check=False)
        if result.returncode:
            LOG.error('Desktop launcher startup failed: %s', result.stderr.strip()[:800])
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError) as error:
        LOG.error('Desktop launcher startup failed: %s', type(error).__name__)
        return False


def launch(integration, profile=None, candidates=None):
    integration = HELPER_IDS.get(integration, integration)
    profile = load_profile() if profile is None else profile
    permitted = {v["integration"] for v in profile.get("applications", {}).values()}
    if integration not in permitted or integration not in DESKTOP_IDS:
        return 2
    candidates = discover((integration,)) if candidates is None else candidates
    candidate = candidates.get(integration)
    if candidate is None:
        return 3  # Existing fixed helper may handle this installation type.
    systemd = shutil.which("systemd-run")
    if not systemd:
        return 3
    ok = start_desktop(candidate['argv'])
    # The helper subsequently verifies the real window before speaking success.
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("integration", nargs="?")
    parser.add_argument("--discover", action="store_true")
    args = parser.parse_args()
    if args.discover:
        print(json.dumps(discover()))
        return
    raise SystemExit(launch(args.integration or ""))
