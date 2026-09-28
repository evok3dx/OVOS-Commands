"""Detection and private configuration for reviewed Jarvis integrations."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path


SCHEMA_VERSION = 1

RECOMMENDED_INTEGRATIONS = {
    "brave", "firefox", "signal", "zoom", "terminal", "calculator",
    "files", "settings", "standard_notes", "claude_desktop",
    "hermes_desktop", "default_mail", "proton_mail", "proton_calendar",
    "system_calendar", "onlyoffice",
}

# Desktop-menu applications remain untrusted until the user enables them.  In
# Recommended mode, offer only familiar everyday families as default-role
# choices. Launching still goes through the reviewed GIO desktop-file path and
# Qwen still receives only the resulting enabled, allowlisted actions.
RECOMMENDED_DYNAMIC_NAMES = {
    "thunderbird", "electronmail", "electron mail",
    "libreoffice", "libreoffice writer", "libreoffice calc",
    "libreoffice impress", "libreoffice start center",
}
RECOMMENDED_DYNAMIC_EXACT_NAMES = {
    "notes", "sticky", "sticky notes", "text editor", "xed",
}

# Detection only decides what setup may offer. Runtime execution remains fixed
# and allowlisted in the desktop helpers.
INTEGRATIONS = {
    "calculator": {"category": "calculator", "desktop_ids": (
        "org.gnome.Calculator.desktop", "gnome-calculator.desktop", "galculator.desktop"
    ), "flatpaks": ("org.gnome.Calculator",)},
    "settings": {"category": "settings", "desktop_ids": ("cinnamon-settings.desktop",)},
    "files": {"category": "files", "desktop_ids": ("nemo.desktop",)},
    "brave": {"category": "brave", "commands": ("brave-browser-stable",),
              "flatpaks": ("com.brave.Browser",)},
    "firefox": {"category": "firefox", "commands": ("firefox",)},
    "signal": {"category": "signal", "commands": ("signal-desktop",),
               "paths": ("/opt/Signal/signal-desktop",),
               "flatpaks": ("org.signal.Signal",)},
    "zoom": {"category": "zoom", "commands": ("zoom",)},
    "terminal": {"category": "terminal", "commands": (
        "x-terminal-emulator", "gnome-terminal", "kgx", "konsole", "xfce4-terminal"
    )},
    "standard_notes": {"category": "notes", "commands": (
                           "standard-notes", "standard-notes-desktop"
                       ),
                       "flatpaks": ("org.standardnotes.standardnotes",),
                       "home_globs": (
                           "Apps/standard-notes*.AppImage",
                           "Apps/Standard-Notes*.AppImage",
                           "Apps/standardnotes*.AppImage",
                           "Apps/StandardNotes*.AppImage",
                           "Applications/standard-notes*.AppImage",
                           "Applications/Standard-Notes*.AppImage",
                           "Applications/standardnotes*.AppImage",
                           "Applications/StandardNotes*.AppImage",
                       ),
                       "desktop_contains": ("standard notes",)},
    "onlyoffice": {"category": "office", "commands": (
        "desktopeditors", "onlyoffice-desktopeditors"
    ), "paths": ("/opt/onlyoffice/desktopeditors/DesktopEditors",),
        "flatpaks": ("org.onlyoffice.desktopeditors",)},
    "claude_desktop": {"category": "claude", "commands": ("claude-desktop",),
                       "desktop_ids": ("com.anthropic.Claude.desktop",)},
    "chatgpt_desktop": {"category": "chatgpt", "commands": ("chatgpt",),
                        "desktop_ids": ("chatgpt.desktop", "com.openai.ChatGPT.desktop")},
    "hermes_desktop": {"category": "hermes", "home_paths": (
        ".hermes/hermes-agent/apps/desktop/release/linux-unpacked/Hermes",
    )},
    "default_mail": {"category": "mail", "mime": "x-scheme-handler/mailto"},
    "proton_mail": {"category": "proton_mail", "commands": ("proton-mail",),
                    "desktop_ids": ("proton-mail.desktop",)},
    "proton_calendar": {"category": "calendar", "desktop_contains": (
        "calendar.proton.me",)},
    "system_calendar": {"category": "system_calendar", "commands": (
        "gnome-calendar", "korganizer",
    ), "desktop_ids": (
        "org.gnome.Calendar.desktop", "gnome-calendar.desktop",
        "org.kde.korganizer.desktop", "io.elementary.calendar.desktop",
    )},
}


def _flatpak_installed(app_id: str) -> bool:
    flatpak = shutil.which("flatpak")
    if not flatpak:
        return False
    try:
        return subprocess.run(
            [flatpak, "info", app_id], stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=5, check=False,
        ).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _desktop_files(home: Path):
    for root in (home / ".local/share/applications", Path("/usr/share/applications")):
        if root.is_dir():
            yield from root.glob("*.desktop")


def _mime_has_default(mime: str) -> bool:
    command = shutil.which("xdg-mime")
    if not command:
        return False
    try:
        result = subprocess.run(
            [command, "query", "default", mime], capture_output=True, text=True,
            timeout=5, check=False,
        )
        return bool(result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return False


def _integration_present(integration: str, home: Path) -> bool:
    rule = INTEGRATIONS[integration]
    if any(shutil.which(name) for name in rule.get("commands", ())):
        return True
    if any(Path(path).is_file() for path in rule.get("paths", ())):
        return True
    if any((home / path).is_file() for path in rule.get("home_paths", ())):
        return True
    if any(any(home.glob(pattern)) for pattern in rule.get("home_globs", ())):
        return True
    if any(_flatpak_installed(app_id) for app_id in rule.get("flatpaks", ())):
        return True
    desktop_files = tuple(_desktop_files(home))
    desktop_names = {path.name for path in desktop_files}
    if any(name in desktop_names for name in rule.get("desktop_ids", ())):
        return True
    needles = tuple(value.lower() for value in rule.get("desktop_contains", ()))
    if needles:
        for path in desktop_files:
            try:
                content = path.read_text(encoding="utf-8", errors="replace").lower()
            except OSError:
                continue
            if any(needle in content for needle in needles):
                return True
    mime = rule.get("mime")
    return bool(mime and _mime_has_default(str(mime)))


def detect_applications(home: Path | None = None) -> dict[str, str]:
    """Return category-to-integration mappings for reviewed detected apps."""
    home = Path(home or Path.home())
    if os.environ.get("JARVIS_TEST_MODE") == "1":
        requested = {
            value.strip() for value in
            os.environ.get("JARVIS_TEST_DETECTED_APPS", "brave,firefox,terminal").split(",")
            if value.strip()
        }
        unknown = requested - set(INTEGRATIONS)
        if unknown:
            raise ValueError(f"Unknown test integrations: {sorted(unknown)}")
        return {
            str(INTEGRATIONS[name]["category"]): name
            for name in INTEGRATIONS if name in requested
        }
    detected = {
        str(rule["category"]): name
        for name, rule in INTEGRATIONS.items()
        if _integration_present(name, home)
    }
    # Proton Calendar is a fixed web application rather than a separate Linux
    # package. Offer it when the Proton desktop suite and reviewed Brave launch
    # path are both present; launching never accepts a spoken URL.
    if (detected.get("proton_mail") == "proton_mail"
            and detected.get("brave") == "brave"):
        detected.setdefault("calendar", "proton_calendar")
    detected.update({key:key for key in _discovered_applications(home)})
    return detected


def _discovered_applications(home: Path) -> dict[str, dict[str, object]]:
    try:
        from .profile import discovered_applications
    except ImportError:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'jarvis_discovery_profile', Path(__file__).with_name('profile.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        discovered_applications = module.discovered_applications
    return discovered_applications(home)


def recommended_applications(
    detected: dict[str, str], home: Path | None = None,
) -> set[str]:
    """Return a small detected everyday set; never install an application."""
    selected = {
        integration for integration in detected.values()
        if integration in RECOMMENDED_INTEGRATIONS
    }
    dynamic = _discovered_applications(Path(home or Path.home()))
    for integration in detected.values():
        definition = dynamic.get(integration)
        if not definition:
            continue
        identity = " ".join((
            str(definition.get("display_name", "")),
            str(definition.get("desktop_id", "")),
            *map(str, definition.get("aliases", ())),
        )).casefold()
        words = set(re.findall(r"[a-z0-9]+", identity))
        display_name = str(definition.get("display_name", "")).casefold().strip()
        if ("telegram" in words
                or any(name in identity for name in RECOMMENDED_DYNAMIC_NAMES)
                or display_name in RECOMMENDED_DYNAMIC_EXACT_NAMES
                or (
            "calendar" in words and "proton" not in words
        )):
            selected.add(integration)
    return selected


def private_agents_available(home: Path | None = None) -> bool:
    """Recognise only the two fixed helpers used by the private agent bridge."""
    if os.environ.get("JARVIS_TEST_MODE") == "1":
        return os.environ.get("JARVIS_TEST_PRIVATE_AGENTS") == "1"
    home = Path(home or Path.home())
    return (
        os.access(home / ".local/bin/jarvis-agent-window", os.X_OK)
        and os.access("/usr/local/sbin/jarvis-agent-message", os.X_OK)
    )


def build_configuration(
    mode: str, detected: dict[str, str], selected: set[str] | None = None,
    *, private_agents: bool = False, home: Path | None = None,
) -> dict[str, object]:
    """Build a stable configuration from a reviewed setup selection."""
    modes = {
        "all": "all-detected", "recommended": "recommended",
        "core": "core-only", "custom": "custom",
    }
    if mode not in modes:
        raise ValueError(f"Unsupported setup mode: {mode}")
    if mode == "all":
        applications = dict(detected)
    elif mode == "recommended":
        recommended = recommended_applications(detected, home)
        applications = {
            category: integration for category, integration in detected.items()
            if integration in recommended
        }
    elif mode == "core":
        applications = {}
    else:
        selected = selected or set()
        applications = {
            category: integration for category, integration in detected.items()
            if integration in selected
        }
        missing = selected - set(detected.values())
        if missing:
            raise ValueError(f"Applications were not detected: {sorted(missing)}")
    preferred_apps = {}
    if "brave" in applications or "firefox" in applications:
        preferred_apps["browser"] = "brave" if "brave" in applications else "firefox"
    for role, choices in {
        "notes": ("notes",),
        "mail": ("proton_mail", "mail"),
        "calendar": ("calendar", "system_calendar"),
        "office": ("office",),
    }.items():
        selected_role = next((key for key in choices if key in applications), None)
        if selected_role:
            preferred_apps[role] = selected_role
    return {
        "schema_version": SCHEMA_VERSION,
        "name": "jarvis",
        "mode": modes[mode],
        "conversation": False,
        "wake_phrase": "hey_jarvis",
        "wake_phrase_spoken": "hey jarvis",
        "listen_shortcut": "<Super>l",
        "microphone_shortcut": "<Shift><Super>l",
        "applications": applications,
        "default_browser": ("brave" if "brave" in applications else
                            "firefox" if "firefox" in applications else None),
        "preferred_apps": preferred_apps,
        "private_extensions": {
            "agents": bool(private_agents and mode in {"all", "recommended"}),
        },
    }
