"""Private appearance preference; no service or operating-system theme changes."""
import json
from pathlib import Path
from startup_settings import read_file, write_file


def read(home=None):
    path = Path(home or Path.home()) / '.config/jarvis/appearance.json'
    raw = read_file(path)
    value = json.loads(raw) if raw is not None else {}
    if not isinstance(value, dict) or value.get('theme', 'light') not in {'light', 'dark'}:
        raise ValueError('Appearance setting needs review')
    return value


def theme(home=None):
    return read(home).get('theme', 'light')


def save(selected, home=None):
    if selected not in {'light', 'dark'}:
        raise ValueError('Choose Light or Dark')
    value = read(home)
    value.update(schema_version=1, theme=selected)
    write_file(Path(home or Path.home()) / '.config/jarvis/appearance.json',
               json.dumps(value, indent=2) + '\n', 0o600)
    return selected
