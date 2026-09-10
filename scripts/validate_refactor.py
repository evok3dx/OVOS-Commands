#!/usr/bin/env python3
"""Static safety checks for the modular Jarvis dispatcher."""

import ast
import py_compile
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "ovos_skill_jarvis_dispatcher"
EXPECTED_ROOT_MODULES = {
    "__init__.py",
    "agents.py",
    "browser.py",
    "conversation.py",
    "desktop.py",
    "dictation.py",
    "helpers.py",
    "profile.py",
    "vocabulary.py",
    "wakeword.py",
}
EXPECTED_INTEGRATION_MODULES = {
    "__init__.py",
    "standard_notes.py",
}
EXPECTED_INTENTS = {
    "CloseFocusedWindowIntent", "MinimizeFocusedWindowIntent",
    "MaximizeFocusedWindowIntent", "RestoreFocusedWindowIntent",
    "ReadLastTypedTextIntent", "NewNoteIntent",
    "ReadSelectedTextIntent", "ReadVisiblePageIntent", "ReadFullPageIntent",
    "StartSpeechNoteDictationIntent", "PauseSpeechNoteDictationIntent",
    "ResumeSpeechNoteDictationIntent", "StopSpeechNoteDictationIntent",
    "WriteFocusedTextIntent", "BraveSearchPromptIntent",
    "FirefoxSearchPromptIntent", "BrowserNavigationIntent",
    "OpenDesktopAppIntent", "FocusDesktopAppIntent",
    "MinimizeDesktopAppIntent", "CloseDesktopAppIntent",
    "OpenCodexCommandIntent", "FocusCodexCommandIntent",
    "SearchCodexIntent", "ReadCodexResponseIntent",
    "ReadClaudeResponseIntent", "ReadLatestResponseIntent",
    "OpenClaudeAliasIntent", "NaturalDateIntent", "OpenCodexIntent",
    "OpenClaudeIntent", "FocusCodexIntent", "FocusClaudeIntent",
    "MinimizeCodexIntent", "MinimizeClaudeIntent",
    "CloseCodexWindowIntent", "CloseClaudeWindowIntent",
    "MessageCodexIntent", "MessageClaudeIntent", "WriteCodexIntent",
    "WriteClaudeIntent", "TypeCodexIntent", "TypeClaudeIntent",
    "SpeakCodexIntent", "SpeakClaudeIntent", "TalkCodexIntent",
    "TalkClaudeIntent",
}


def install_import_stubs():
    """Provide the minimal OVOS API surface needed for an import check."""

    class IntentBuilder:
        def __init__(self, name):
            self.name = name

        def require(self, _entity):
            return self

    class ConversationalSkill:
        pass

    def intent_handler(_intent):
        return lambda function: function

    modules = {
        "ovos_bus_client": {"Message": type("Message", (), {})},
        "ovos_workshop": {},
        "ovos_workshop.decorators": {"intent_handler": intent_handler},
        "ovos_workshop.intents": {"IntentBuilder": IntentBuilder},
        "ovos_workshop.skills": {},
        "ovos_workshop.skills.converse": {
            "ConversationalSkill": ConversationalSkill,
        },
    }
    for name, attributes in modules.items():
        module = types.ModuleType(name)
        module.__dict__.update(attributes)
        sys.modules[name] = module


def main():
    found = {path.name for path in PACKAGE.glob("*.py")}
    assert found == EXPECTED_ROOT_MODULES, (found, EXPECTED_ROOT_MODULES)

    integrations = PACKAGE / "integrations"
    found_integrations = {path.name for path in integrations.glob("*.py")}
    assert found_integrations == EXPECTED_INTEGRATION_MODULES, (
        found_integrations,
        EXPECTED_INTEGRATION_MODULES,
    )

    python_files = list(PACKAGE.glob("*.py")) + list(integrations.glob("*.py"))
    for path in python_files:
        py_compile.compile(str(path), doraise=True)

    tree = ast.parse((PACKAGE / "__init__.py").read_text())
    intents = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "IntentBuilder"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }
    assert intents == EXPECTED_INTENTS, (intents, EXPECTED_INTENTS)

    profile_namespace = {}
    exec((PACKAGE / "profile.py").read_text(), profile_namespace)
    brain_profile = profile_namespace["resolve_profile"](
        profile_namespace["BRAIN_COMPATIBILITY_PROFILE"]
    )

    namespace = {}
    exec((PACKAGE / "vocabulary.py").read_text(), namespace)

    conversation_namespace = {}
    exec((PACKAGE / "conversation.py").read_text(), conversation_namespace)
    assert "re" in conversation_namespace

    class FakeSkill:
        def __init__(self):
            self.registrations = []

        def register_vocabulary(self, phrase, entity):
            self.registrations.append((phrase, entity))

    fake = FakeSkill()
    fake._jarvis_profile = brain_profile
    namespace["register_skill_vocabulary"](fake)
    assert len(fake.registrations) == 879
    for phrase in (
        "read window",
        "read this window",
        "read current window",
    ):
        assert (
            phrase,
            "ReadVisiblePageCommand",
        ) in fake.registrations
    for phrase in (
        "new note",
        "create a new note",
        "create new note",
        "make a new note",
        "make new note",
    ):
        assert (phrase, "NewNoteCommand") in fake.registrations
    assert len(fake._browser_navigation_actions) == 66
    assert set(fake._desktop_app_aliases) == {
        "brave", "firefox", "signal", "zoom", "terminal", "notes",
        "office", "claude", "mail", "calendar",
    }

    profiles = sorted((ROOT / "profiles").glob("*.json"))
    assert len(profiles) == 3
    for path in profiles:
        raw_profile = __import__("json").loads(path.read_text())
        profile_namespace["resolve_profile"](raw_profile)

    try:
        profile_namespace["resolve_profile"]({
            "applications": {"notes": "terminal"},
        })
    except ValueError:
        pass
    else:
        raise AssertionError("Incompatible category mapping was accepted")

    install_import_stubs()
    sys.path.insert(0, str(ROOT))
    package = __import__("ovos_skill_jarvis_dispatcher")
    skill = package.create_skill()
    assert type(skill).__name__ == "JarvisDispatcherSkill"

    print(f"PASS: {len(python_files)} Python modules compile")
    print("PASS: 47 intents match the expected inventory")
    print("PASS: 879 vocabulary registrations are present")
    print("PASS: 3 deployment profiles validate")
    print("PASS: package imports and create_skill() succeeds")


if __name__ == "__main__":
    main()
