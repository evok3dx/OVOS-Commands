"""Two fixed local model endpoints. An unavailable private endpoint never falls back."""
import json
import os
from pathlib import Path
import stat

GENERAL_PORT = 11434
PRIVATE_PORT = 11435


def model_port(home=None):
    home = Path(home or Path.home())
    choice = home / '.config/jarvis/network-isolation.json'
    private_required = False
    if choice.exists() or choice.is_symlink():
        if any(p.is_symlink() for p in (choice, *choice.parents)):
            raise ValueError('Model isolation preference must be regular')
        info = choice.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_size > 8192):
            raise ValueError('Model isolation preference needs review')
        saved = json.loads(choice.read_text())
        if not isinstance(saved, dict) or saved.get('schema_version') != 1 or type(saved.get('enabled')) is not bool:
            raise ValueError('Invalid isolation preference')
        private_required = saved['enabled'] and bool(saved.get('model_binary'))
    path = home / '.config/jarvis/router.json'
    if not path.exists() and not path.is_symlink():
        if private_required:
            raise ValueError('Private model settings are missing; no endpoint fallback')
        return GENERAL_PORT
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Model endpoint settings must be regular')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_size > 4096:
        raise ValueError('Model endpoint settings need review')
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError('Model endpoint settings must be an object')
    backend = value.get('backend', 'general')
    if backend not in {'general', 'jarvis'}:
        raise ValueError('Unknown model backend; no endpoint fallback')
    if private_required and backend != 'jarvis':
        raise ValueError('Private model preference conflicts with routing; no endpoint fallback')
    return PRIVATE_PORT if backend == 'jarvis' else GENERAL_PORT
