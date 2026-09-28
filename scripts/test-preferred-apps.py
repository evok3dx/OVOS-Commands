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
preferred_app_candidates = module.preferred_app_candidates

capability_spec = spec_from_file_location(
    "jarvis_preferred_capabilities",
    ROOT / "ovos_skill_jarvis_dispatcher" / "capabilities.py",
)
capabilities = module_from_spec(capability_spec)
capability_spec.loader.exec_module(capabilities)


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

# Dynamically discovered desktop mail and office applications may be selected
# as friendly defaults, but an unrelated application never enters either role.
dynamic = {
    "desktop_" + "1" * 24: {
        "integration": "desktop_" + "1" * 24,
        "display_name": "Thunderbird",
        "aliases": ["thunderbird"],
        "menu_categories": ["Network", "Email"],
    },
    "desktop_" + "2" * 24: {
        "integration": "desktop_" + "2" * 24,
        "display_name": "ElectronMail",
        "aliases": ["electronmail"],
        "menu_categories": ["Network", "Email"],
    },
    "desktop_" + "3" * 24: {
        "integration": "desktop_" + "3" * 24,
        "display_name": "LibreOffice Writer",
        "aliases": ["libreoffice writer"],
        "menu_categories": ["Office", "WordProcessor"],
    },
    "desktop_" + "4" * 24: {
        "integration": "desktop_" + "4" * 24,
        "display_name": "Music Player",
        "aliases": ["music player"],
        "menu_categories": ["AudioVideo"],
    },
    "desktop_" + "5" * 24: {
        "integration": "desktop_" + "5" * 24,
        "display_name": "Unreviewed Mail Utility",
        "aliases": ["unreviewed mail utility"],
        "menu_categories": ["Network", "Email"],
    },
    "desktop_" + "6" * 24: {
        "integration": "desktop_" + "6" * 24,
        "display_name": "Notes",
        "aliases": ["notes"],
        "menu_categories": ["Utility"],
    },
    "desktop_" + "7" * 24: {
        "integration": "desktop_" + "7" * 24,
        "display_name": "Text Editor",
        "aliases": ["text editor"],
        "menu_categories": ["Utility", "TextEditor"],
    },
}
assert preferred_app_candidates(dynamic, "mail") == [
    "desktop_" + "1" * 24, "desktop_" + "2" * 24,
    "desktop_" + "5" * 24,
]
assert preferred_app_candidates(dynamic, "office") == ["desktop_" + "3" * 24]
assert preferred_app_candidates(dynamic, "notes") == [
    "desktop_" + "6" * 24, "desktop_" + "7" * 24,
]

capabilities._discovered_applications = lambda _home: dynamic
recommended = capabilities.recommended_applications({
    "office": "onlyoffice",
    **{key: key for key in dynamic},
})
assert "onlyoffice" in recommended
assert "desktop_" + "1" * 24 in recommended
assert "desktop_" + "2" * 24 in recommended
assert "desktop_" + "3" * 24 in recommended
assert "desktop_" + "4" * 24 not in recommended
assert "desktop_" + "5" * 24 not in recommended
assert "desktop_" + "6" * 24 in recommended
assert "desktop_" + "7" * 24 in recommended

assert module.APPLICATION_INTEGRATIONS["default_mail"]["display_name"] == (
    "System default mail"
)

setup_source = (ROOT / "scripts" / "setup.py").read_text(encoding="utf-8")
for required in (
    "class DefaultAppPicker(Gtk.Button)",
    "self.set_hexpand(False)",
    "self.set_size_request(380, 38)",
    "pan-down-symbolic",
    "self.connect('clicked', self._open_popover)",
    "self._popover.popup()",
    "self._choices_box.set_size_request(340, 88)",
    "'onlyoffice': ('onlyoffice-desktopeditors', 'x-office-document')",
):
    assert required in setup_source, f"Default Apps picker is missing: {required}"

print("PASS: preferred app roles are compatible, unique and safely defaulted")
