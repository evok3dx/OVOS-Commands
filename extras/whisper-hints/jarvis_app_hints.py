"""Bounded proper-name hints from the existing Jarvis profile. No audio/log storage."""
import hashlib
import importlib.util
import json
from pathlib import Path
import threading

ORIGINAL = 'Jarvis, Brave, Claude, Hermes, ChatGPT, Proton Mail, Standard Notes, ONLYOFFICE, RustDesk.'
MEDIA_HINT = 'Pause music. Next track. Previous track. Resume playback. Write this. Type this. Start writing. Start dictation.'
TOKEN_LIMIT = 192
NAME_LIMIT = 40
PROPER_NAMES = {'standard_notes':'Standard Notes', 'onlyoffice':'ONLYOFFICE',
                'claude_desktop':'Claude', 'chatgpt_desktop':'ChatGPT',
                'hermes_desktop':'Hermes', 'proton_calendar':'Proton Calendar'}
_lock = threading.RLock()
_cached_key = None
_cached_names = ()
_profile_module = None
_profile_path = None


def clean_name(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 72:
        return None
    if any(not (c.isalnum() or c in " &+.-'()") for c in value):
        return None
    name = ' '.join(value.split())
    return name if name and any(c.isalnum() for c in name) else None


def names_from_profile(profile):
    apps = profile['applications']
    names = ['Jarvis']
    # Prefer saved spoken names over menu names when the list needs limiting.
    ordered = sorted(apps.items())
    names.extend(value.get('spoken_name') for _, value in ordered)
    names.extend(PROPER_NAMES.get(value['integration'], value['display_name'])
                 for _, value in ordered)
    result, seen = [], set()
    for value in names:
        name = clean_name(value)
        if name and name.casefold() not in seen:
            seen.add(name.casefold())
            result.append(name)
    return result


def enabled_names(home=None):
    global _cached_key, _cached_names, _profile_module, _profile_path
    home = Path(home) if home is not None else Path.home()
    path = home / '.config/jarvis/capabilities.json'
    if not path.is_file():
        path = home / '.config/jarvis/profile.json'
    with path.open('rb') as stream:
        data = stream.read(65537)
    if len(data) > 65536:
        raise ValueError('Oversized Jarvis profile')
    source = home / '.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher/profile.py'
    key = (str(source), hashlib.sha256(data).hexdigest())
    with _lock:
        if key == _cached_key:
            return list(_cached_names)
        if _profile_module is None or source != _profile_path:
            # Load only the existing profile module, not the OVOS skill itself.
            spec = importlib.util.spec_from_file_location('jarvis_whisper_profile', source)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _profile_module, _profile_path = module, source
        raw = json.loads(data)
        if raw.get('mode') == 'all-detected':
            raw['applications'] = dict(raw.get('applications', {}))
            raw['applications'].update({k:k for k in _profile_module.discovered_applications()})
        resolved = _profile_module.resolve_profile(raw)
        names = names_from_profile(resolved)
        _cached_key, _cached_names = key, tuple(names)
        return list(names)


def build_prompt(names, base=None, tokenizer=None):
    if base is not None and not isinstance(base, str):
        raise ValueError('Existing initial_prompt is not text')
    # Replace only our known earlier fixed list, never an unrelated custom prompt.
    custom = base if base and base.strip() != ORIGINAL else ''
    def count(text):
        if tokenizer is not None:
            return len(tokenizer.encode(' ' + text.strip()).ids)
        # UTF-8 bytes conservatively bound byte-BPE tokens without a model load.
        return len((' ' + text.strip()).encode('utf-8'))
    if custom and count(custom) > TOKEN_LIMIT:
        raise ValueError('Existing custom prompt exceeds the dynamic hint budget')
    prefix = (custom.rstrip() + ' ' if custom else '') + MEDIA_HINT
    if count(prefix) > TOKEN_LIMIT:
        raise ValueError('Media vocabulary exceeds the dynamic hint budget')
    selected = []
    result = prefix
    for name in names:
        if len(selected) >= NAME_LIMIT:
            break
        candidate_names = [*selected, name]
        candidate = prefix.rstrip() + ' ' + ', '.join(candidate_names) + '.'
        if count(candidate) <= TOKEN_LIMIT:
            selected = candidate_names
            result = candidate
    return result, {'names':len(selected), 'available_names':len(names), 'media':True,
                    'tokens':count(result) if result else 0,
                    'limited':len(selected) < len(names)}


def prompt_for(base=None, tokenizer=None, home=None, strict=False):
    try:
        return build_prompt(enabled_names(home), base, tokenizer)
    except Exception:
        if strict:
            raise
        # A bad/missing profile must never stop speech recognition.
        return base, {'names':0, 'unavailable':True}
