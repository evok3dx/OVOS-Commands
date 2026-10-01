"""Two fixed local model endpoints. An unavailable private endpoint never falls back."""
import json
import os
from pathlib import Path
import stat

GENERAL_PORT = 11434
PRIVATE_PORT = 11435


def model_port(home=None):
    home = Path(home or Path.home())
    path = home / '.config/jarvis/router.json'
    if not path.exists() and not path.is_symlink():
        return GENERAL_PORT
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Model endpoint settings must be regular')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_size > 4096:
        raise ValueError('Model endpoint settings need review')
    value = json.loads(path.read_text())
    backend = value.get('backend', 'general')
    if backend not in {'general', 'jarvis'}:
        raise ValueError('Unknown model backend; no endpoint fallback')
    return PRIVATE_PORT if backend == 'jarvis' else GENERAL_PORT
