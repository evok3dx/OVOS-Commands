"""Validated deployment profiles for Jarvis application categories."""

import copy
import json
from pathlib import Path


APPLICATION_INTEGRATIONS = {
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
            "standard notes", "standard note", "standard node",
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
    "proton_mail": {
        "display_name": "Proton Mail",
        "aliases": ["proton mail", "email app", "mail app", "email", "mail"],
    },
    "proton_calendar": {
        "display_name": "Proton Calendar",
        "aliases": [
            "proton calendar", "calendar app", "my calendar", "calendar",
        ],
    },
}

APPLICATION_CATEGORIES = {
    "brave", "firefox", "signal", "zoom", "terminal", "notes",
    "office", "claude", "mail", "calendar",
}

# Keep each generic command category constrained to compatible integrations.
# New alternatives can be added deliberately without allowing profiles to map
# a category such as Notes to an unrelated application such as Terminal.
CATEGORY_INTEGRATIONS = {
    "brave": {"brave"},
    "firefox": {"firefox"},
    "signal": {"signal"},
    "zoom": {"zoom"},
    "terminal": {"terminal"},
    "notes": {"standard_notes"},
    "office": {"onlyoffice"},
    "claude": {"claude_desktop"},
    "mail": {"proton_mail"},
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
        "mail": "proton_mail",
        "calendar": "proton_calendar",
    },
}


def resolve_profile(raw_profile):
    """Validate a profile and expand its allowlisted integrations."""

    if not isinstance(raw_profile, dict):
        raise ValueError("Profile must be a JSON object")

    applications = raw_profile.get("applications")
    if not isinstance(applications, dict) or not applications:
        raise ValueError("Profile applications must be a non-empty object")

    unknown_categories = set(applications) - APPLICATION_CATEGORIES
    if unknown_categories:
        raise ValueError(
            f"Unsupported application categories: {sorted(unknown_categories)}"
        )

    resolved = {}
    for category, integration in applications.items():
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

    wake_phrase = raw_profile.get("wake_phrase", "hey_jarvis")
    if not isinstance(wake_phrase, str) or not wake_phrase.strip():
        raise ValueError("wake_phrase must be a non-empty string")

    return {
        "name": str(raw_profile.get("name", "unnamed")),
        "conversation": bool(raw_profile.get("conversation", False)),
        "wake_phrase": wake_phrase.strip(),
        "applications": resolved,
    }


def load_profile(path=None, logger=None):
    """Load the user profile, falling back to current Brain behaviour."""

    profile_path = path or Path.home() / ".config/jarvis/profile.json"
    profile_path = Path(profile_path)

    if not profile_path.is_file():
        return resolve_profile(BRAIN_COMPATIBILITY_PROFILE)

    try:
        raw_profile = json.loads(profile_path.read_text(encoding="utf-8"))
        return resolve_profile(raw_profile)
    except Exception as error:
        if logger:
            logger.error(
                f"Invalid Jarvis profile at {profile_path}; "
                f"using compatibility defaults: {error}"
            )
        return resolve_profile(BRAIN_COMPATIBILITY_PROFILE)
