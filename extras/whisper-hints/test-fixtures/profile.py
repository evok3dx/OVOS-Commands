"""Validated deployment profiles for Jarvis application categories."""

import copy
import json
from pathlib import Path

try:
    from . import discovery
except ImportError:  # Setup loads this module with the distribution Python.
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        'jarvis_desktop_discovery', Path(__file__).with_name('discovery.py'))
    discovery = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(discovery)


APPLICATION_INTEGRATIONS = {
    "calculator": {"display_name": "Calculator", "aliases": ["calculator"]},
    "settings": {"display_name": "Settings", "aliases": ["system settings", "settings"]},
    "files": {"display_name": "Files", "aliases": ["file manager", "files", "my files", "nemo"]},
    "brave": {
        "display_name": "Brave",
        "aliases": ["brave browser", "brave", "break"],
    },
    "firefox": {
        "display_name": "Firefox",
        "aliases": ["firefox browser", "fire fox", "firefox"],
    },
    "signal": {
        "display_name": "Signal",
        "aliases": ["signal app", "signal"],
    },
    "zoom": {
        "display_name": "Zoom",
        "aliases": ["zoom app", "xoom", "zome", "zoom"],
    },
    "terminal": {
        "display_name": "Terminal",
        "aliases": ["command line", "terminal app", "terminal", "console"],
    },
    "standard_notes": {
        "display_name": "Notes",
        "aliases": [
            "standard notes", "standard note",
            "standard nodes", "standard node",
            "notes app", "notes", "nodes", "a note", "note",
        ],
    },
    "onlyoffice": {
        "display_name": "Office",
        "aliases": ["only office", "onlyoffice", "office app", "office"],
    },
    "claude_desktop": {
        "display_name": "Claude",
        "aliases": [
            "claude desktop", "claude app", "clawed desktop",
            "clawed app", "claude", "clawed",
        ],
    },
    "chatgpt_desktop": {
        "display_name": "ChatGPT",
        "aliases": [
            "chat g p t", "chatgpt desktop", "chatgpt app",
            "chatgpt", "g p t", "gpt", "chat",
        ],
    },
    "hermes_desktop": {
        "display_name": "Hermes",
        "aliases": ["hermes desktop", "hermes app", "hermes"],
    },
    "default_mail": {
        "display_name": "Mail",
        "aliases": ["default mail", "email app", "mail app", "email", "mail"],
    },
    "proton_mail": {
        "display_name": "Proton Mail",
        "aliases": ["proton mail app", "proton email", "proton mail"],
    },
    "proton_calendar": {
        "display_name": "Proton Calendar",
        "aliases": [
            "proton calendar", "calendar app", "my calendar", "calendar",
        ],
    },
}

APPLICATION_CATEGORIES = {
    "calculator", "settings", "files",
    "brave", "firefox", "signal", "zoom", "terminal", "notes",
    "office", "claude", "chatgpt", "hermes", "mail", "proton_mail",
    "calendar",
}

# Keep each generic command category constrained to compatible integrations.
# New alternatives can be added deliberately without allowing profiles to map
# a category such as Notes to an unrelated application such as Terminal.
CATEGORY_INTEGRATIONS = {
    "calculator": {"calculator"},
    "settings": {"settings"},
    "files": {"files"},
    "brave": {"brave"},
    "firefox": {"firefox"},
    "signal": {"signal"},
    "zoom": {"zoom"},
    "terminal": {"terminal"},
    "notes": {"standard_notes"},
    "office": {"onlyoffice"},
    "claude": {"claude_desktop"},
    "chatgpt": {"chatgpt_desktop"},
    "hermes": {"hermes_desktop"},
    "mail": {"default_mail", "proton_mail"},
    "proton_mail": {"proton_mail"},
    "calendar": {"proton_calendar"},
}

BRAIN_COMPATIBILITY_PROFILE = {
    "name": "brain-compatibility",
    "conversation": True,
    "wake_phrase": "hey_jarvis",
    "applications": {
        "brave": "brave",
        "firefox": "firefox",
        "signal": "signal",
        "zoom": "zoom",
        "terminal": "terminal",
        "notes": "standard_notes",
        "office": "onlyoffice",
        "claude": "claude_desktop",
        "chatgpt": "chatgpt_desktop",
        "hermes": "hermes_desktop",
        "mail": "default_mail",
        "proton_mail": "proton_mail",
        "calendar": "proton_calendar",
    },
    "private_extensions": {"agents": True},
}

SAFE_DEFAULT_PROFILE = {
    "name": "jarvis-safe-default",
    "conversation": False,
    "wake_phrase": "hey_jarvis",
    "applications": {},
    "private_extensions": {"agents": False},
}


def discovered_applications(home=None):
    return discovery.available_apps(APPLICATION_INTEGRATIONS, home)


def validate_spoken_names(raw, definitions=None):
    """Validate additional app names; originals remain registered."""
    import re
    definitions = definitions if definitions is not None else {
        **APPLICATION_INTEGRATIONS, **discovered_applications()}
    if not isinstance(raw, dict):
        raise ValueError('Spoken names must be an object')
    owners = {}
    for key, definition in definitions.items():
        for alias in definition['aliases']:
            owners.setdefault(discovery.normalise(alias), set()).add(key)
    names = {}
    for key, value in raw.items():
        if not isinstance(key, str) or (key not in APPLICATION_INTEGRATIONS and
                not re.fullmatch(r'desktop_[0-9a-f]{24}', key)):
            raise ValueError('Unknown app for spoken name')
        if not isinstance(value, str) or len(value) > 48 or any(
                not (c.isalnum() or c in " -'") for c in value):
            raise ValueError('Use a short name with letters, numbers, spaces, hyphens or apostrophes')
        name = discovery.normalise(value)
        if not name:
            continue  # Clearing a name restores the defaults.
        if name in {'stop', 'cancel', 'never mind', 'nevermind', 'wait'} or name.split()[0] in {
                'open', 'launch', 'start', 'close', 'quit', 'exit', 'focus', 'show',
                'minimise', 'minimize', 'maximise', 'maximize', 'hide'}:
            raise ValueError('Enter only the app name, for example Mega')
        conflicts = owners.get(name, set()) - {key}
        if conflicts:
            other = next(iter(sorted(conflicts)))
            raise ValueError(f'“{value}” is already used by {definitions.get(other, {}).get("display_name", other)}')
        owners.setdefault(name, set()).add(key)
        names[key] = name
    return names


def apply_spoken_names(resolved, raw_names, definitions):
    # A newly installed app must not make all existing commands disappear if
    # its default name conflicts with an older personal name. Ignore only the
    # conflicting override; the original app aliases stay usable.
    accepted = {}
    for key, value in (raw_names.items() if isinstance(raw_names, dict) else ()):
        try:
            accepted = validate_spoken_names({**accepted, key: value}, definitions)
        except ValueError:
            continue
    for definition in resolved.values():
        alias = accepted.get(definition['integration'])
        if alias and alias not in definition['aliases']:
            definition['aliases'].append(alias)
        if alias:
            definition['spoken_name'] = alias
    return accepted


def resolve_profile(raw_profile):
    """Validate a profile and expand its allowlisted integrations."""

    if not isinstance(raw_profile, dict):
        raise ValueError("Profile must be a JSON object")

    applications = raw_profile.get("applications")
    if not isinstance(applications, dict):
        raise ValueError("Profile applications must be an object")

    dynamic_ids = {key for key in applications if isinstance(key, str) and
                   key.startswith('desktop_')}
    import re
    if any(not re.fullmatch(r'desktop_[0-9a-f]{24}', key) for key in dynamic_ids):
        raise ValueError('Invalid discovered application ID')
    discovered = discovered_applications() if dynamic_ids else {}
    unknown_categories = set(applications) - APPLICATION_CATEGORIES - dynamic_ids
    if unknown_categories:
        raise ValueError(
            f"Unsupported application categories: {sorted(unknown_categories)}"
        )

    resolved = {}
    for category, integration in applications.items():
        if category in dynamic_ids:
            if integration != category:
                raise ValueError('Discovered application IDs must match')
            if category not in discovered:
                continue  # Uninstalled/hidden entries do not disable other apps.
            definition = copy.deepcopy(discovered[category])
            definition['integration'] = category
            resolved[category] = definition
            continue
        if not isinstance(integration, str):
            raise ValueError(f"Integration for {category} must be a string")
        if integration not in APPLICATION_INTEGRATIONS:
            raise ValueError(
                f"Unsupported integration for {category}: {integration}"
            )
        if integration not in CATEGORY_INTEGRATIONS[category]:
            raise ValueError(
                f"Integration {integration} is incompatible with {category}"
            )

        definition = copy.deepcopy(APPLICATION_INTEGRATIONS[integration])
        definition["integration"] = integration
        resolved[category] = definition

    names = raw_profile.get('spoken_names', {})
    accepted_names = {}
    if names:
        # Include disabled integrations when checking names, so enabling one
        # later cannot silently redirect an existing phrase.
        definitions = {**APPLICATION_INTEGRATIONS, **(discovered or discovered_applications())}
        accepted_names = apply_spoken_names(resolved, names, definitions)

    wake_phrase = raw_profile.get("wake_phrase", "hey_jarvis")
    if not isinstance(wake_phrase, str) or not wake_phrase.strip():
        raise ValueError("wake_phrase must be a non-empty string")

    private_extensions = raw_profile.get("private_extensions", {})
    if not isinstance(private_extensions, dict):
        raise ValueError("private_extensions must be an object")

    return {
        "name": str(raw_profile.get("name", "unnamed")),
        "conversation": bool(raw_profile.get("conversation", False)),
        "wake_phrase": wake_phrase.strip(),
        "applications": resolved,
        "spoken_names": accepted_names,
        "private_extensions": {
            "agents": private_extensions.get("agents") is True,
        },
    }


def load_profile(path=None, logger=None):
    """Load the user profile, falling back to current Brain behaviour."""

    if path is None:
        capabilities = Path.home() / ".config/jarvis/capabilities.json"
        profile_path = capabilities if capabilities.is_file() else (
            Path.home() / ".config/jarvis/profile.json"
        )
    else:
        profile_path = Path(path)

    if not profile_path.is_file():
        return resolve_profile(SAFE_DEFAULT_PROFILE)

    try:
        raw_profile = json.loads(profile_path.read_text(encoding="utf-8"))
        if raw_profile.get('mode') == 'all-detected':
            raw_profile['applications'] = dict(raw_profile.get('applications', {}))
            raw_profile['applications'].update({key:key for key in discovered_applications()})
        return resolve_profile(raw_profile)
    except Exception as error:
        if logger:
            logger.error(
                f"Invalid Jarvis profile at {profile_path}; "
                f"using safe defaults: {error}"
            )
        return resolve_profile(SAFE_DEFAULT_PROFILE)
