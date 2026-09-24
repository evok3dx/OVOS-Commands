"""Desktop-menu discovery, independent of OVOS and its Python environment."""
import configparser
import hashlib
import os
from pathlib import Path
import re
import shutil
import shlex


def normalise(value):
    return ' '.join(re.sub(r'[^\w\s]', ' ', value.casefold()).split())


def desktop_roots(home=None):
    home = Path(home or Path.home())
    data_home = Path(os.environ.get('XDG_DATA_HOME', str(home / '.local/share')))
    if not data_home.is_absolute():
        data_home = home / '.local/share'
    roots = [data_home / 'applications']
    roots += [Path(d) / 'applications' for d in os.environ.get(
        'XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':')
        if d and Path(d).is_absolute()]
    roots += [home / '.local/share/flatpak/exports/share/applications',
              Path('/var/lib/flatpak/exports/share/applications')]
    return list(dict.fromkeys(roots))


def scan_desktop_apps(home=None, roots=None):
    """Discover visible launchable entries, including Flatpak exports.

    Desktop IDs honour user overrides, including Hidden entries. Launching
    uses the original file through GIO, never our own interpretation of Exec.
    """
    found, seen = {}, set()
    desktops = set(os.environ.get('XDG_CURRENT_DESKTOP', '').split(':')) - {''}
    for root in desktop_roots(home) if roots is None else roots:
        try:
            paths = sorted(root.rglob('*.desktop'))
        except OSError:
            continue
        for path in paths:
            desktop_id = str(path.relative_to(root)).replace(os.sep, '-')
            if desktop_id in seen:
                continue
            seen.add(desktop_id)
            try:
                parser = configparser.ConfigParser(interpolation=None, strict=False)
                parser.read(path, encoding='utf-8')
                entry = parser['Desktop Entry']
                if entry.get('Type') != 'Application':
                    continue
                if entry.getboolean('Hidden', False) or entry.getboolean('NoDisplay', False):
                    continue
                only = set(entry.get('OnlyShowIn', '').split(';')) - {''}
                excluded = set(entry.get('NotShowIn', '').split(';')) - {''}
                if (only and not only.intersection(desktops)) or excluded.intersection(desktops):
                    continue
                if not entry.get('Exec') and not entry.getboolean('DBusActivatable', False):
                    continue
                if entry.get('TryExec') and not shutil.which(entry['TryExec']):
                    continue
                name = entry.get('Name', '').strip()
                if not name or not normalise(name) or any(ord(c) < 32 for c in name):
                    continue
                flatpak = entry.get('X-Flatpak', '').strip()
                kind = 'flatpak' if flatpak or 'flatpak/exports/' in str(path) else 'desktop'
                app_id = 'desktop_' + hashlib.sha256(desktop_id.encode()).hexdigest()[:24]
                aliases = [normalise(name)]
                command = shlex.split(entry.get('Exec', ''))
                if command:
                    executable = Path(command[0]).name
                    alias = normalise(executable.removesuffix('.AppImage'))
                    if executable not in {'env','flatpak','sh','bash','python','python3','gio','xdg-open'} and alias:
                        aliases.append(alias)
                if flatpak:
                    aliases.append(normalise(flatpak.split('.')[-1]))
                found[app_id] = {
                    'desktop_id': desktop_id, 'path': str(path),
                    'display_name': name, 'aliases': list(dict.fromkeys(aliases)),
                    'kind': kind, 'flatpak_id': flatpak,
                    'icon': entry.get('Icon', '').strip(),
                    'wm_class': entry.get('StartupWMClass', '').strip() or flatpak,
                    'exec': entry.get('Exec', ''),
                }
            except (OSError, ValueError, KeyError, configparser.Error):
                continue
    return found


def available_apps(definitions, home=None):
    """Exclude existing integrations and disambiguate duplicate menu names."""
    reserved = {normalise(alias) for value in definitions.values()
                for alias in [value['display_name'], *value.get('aliases', [])]}
    apps = scan_desktop_apps(home)
    result = {}
    for key, entry in apps.items():
        name = entry['aliases'][0]
        # Existing named integrations own their names, even when disabled.
        if name in reserved:
            continue
        identity = normalise(' '.join((entry['desktop_id'], entry['exec'], name)))
        if any(word in identity.split() for word in (
                'hermes', 'claude', 'chatgpt', 'proton', 'brave', 'firefox',
                'signal', 'zoom', 'onlyoffice', 'standardnotes',
                'galculator', 'nemo')) or any(' ' + phrase + ' ' in ' ' + identity + ' '
                    for phrase in ('standard notes', 'gnome calculator',
                                   'gnome terminal', 'cinnamon settings')):
            continue
        result[key] = entry
    groups = {}
    for key, entry in result.items():
        groups.setdefault(entry['aliases'][0], []).append(key)
    for name, keys in groups.items():
        if len(keys) < 2:
            continue
        for key in keys:
            entry = result[key]
            qualifier = entry['kind']
            if sum(result[k]['kind'] == qualifier for k in keys) > 1:
                qualifier = normalise(entry['desktop_id'].removesuffix('.desktop'))
            entry['display_name'] += ' (' + qualifier + ')'
            entry['aliases'] = [name + ' ' + qualifier]
    # A qualified name must not collide with another app or built-in alias.
    owners = {}
    for key, entry in result.items():
        for alias in entry['aliases']:
            owners.setdefault(alias, []).append(key)
    for entry in result.values():
        entry['aliases'] = [a for a in entry['aliases'] if len(owners[a]) == 1 and a not in reserved]
    return {k:v for k,v in result.items() if v['aliases']}
