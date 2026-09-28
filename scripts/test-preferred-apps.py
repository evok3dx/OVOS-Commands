#!/usr/bin/env python3
"""Verify friendly app roles resolve to exactly one compatible enabled app."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location(
    "jarvis_preferred_profile",
    ROOT / "ovos_skill_jarvis_dispatcher" / "profile.py",
)
module = module_from_spec(spec)
spec.loader.exec_module(module)
resolve_profile = module.resolve_profile


raw = {
    "name": "preferred-app-test",
    "applications": {
        "brave": "brave",
        "firefox": "firefox",
        "notes": "standard_notes",
        "mail": "default_mail",
        "proton_mail": "proton_mail",
        "calendar": "proton_calendar",
        "system_calendar": "system_calendar",
        "office": "onlyoffice",
    },
    "preferred_apps": {
        "browser": "firefox",
        "mail": "proton_mail",
        "calendar": "system_calendar",
    },
}
profile = resolve_profile(raw)
assert profile["preferred_apps"] == {
    "browser": "firefox",
    "notes": "notes",
    "mail": "proton_mail",
    "calendar": "system_calendar",
    "office": "office",
}

apps = profile["applications"]
assert "browser" in apps["firefox"]["aliases"]
assert "browser" not in apps["brave"]["aliases"]
assert "mail" in apps["proton_mail"]["aliases"]
assert "mail" not in apps["mail"]["aliases"]
assert "default mail" in apps["mail"]["aliases"]
assert "calendar" in apps["system_calendar"]["aliases"]
assert "calendar" not in apps["calendar"]["aliases"]
assert "proton calendar" in apps["calendar"]["aliases"]
assert "notes" in apps["notes"]["aliases"]
assert "office" in apps["office"]["aliases"]

fallback = resolve_profile({
    "name": "fallback-test",
    "applications": {"firefox": "firefox", "mail": "default_mail"},
    "preferred_apps": {"browser": "missing", "mail": "missing"},
})
assert fallback["preferred_apps"] == {"browser": "firefox", "mail": "mail"}

print("PASS: preferred app roles are compatible, unique and safely defaulted")
