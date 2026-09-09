#!/usr/bin/env python3
"""Static safety checks for the modular Jarvis dispatcher."""

import ast
import py_compile
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "ovos_skill_jarvis_dispatcher"
EXPECTED_MODULES = {
    "__init__.py",
    "agents.py",
    "browser.py",
    "conversation.py",
    "desktop.py",
    "dictation.py",
    "helpers.py",
    "vocabulary.py",
    "wakeword.py",
}
EXPECTED_INTENTS = {
    "CloseFocusedWindowIntent", "MinimizeFocusedWindowIntent",
    "MaximizeFocusedWindowIntent", "ReadLastTypedTextIntent",
    "ReadSelectedTextIntent", "ReadVisiblePageIntent",
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
    assert found == EXPECTED_MODULES, (found, EXPECTED_MODULES)

    for path in PACKAGE.glob("*.py"):
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

    namespace = {}
    exec((PACKAGE / "vocabulary.py").read_text(), namespace)

    class FakeSkill:
        def __init__(self):
            self.registrations = []

        def register_vocabulary(self, phrase, entity):
            self.registrations.append((phrase, entity))

    fake = FakeSkill()
    namespace["register_skill_vocabulary"](fake)
    assert len(fake.registrations) == 859
    assert len(fake._browser_navigation_actions) == 66
    assert set(fake._desktop_app_aliases) == {
        "brave", "firefox", "signal", "zoom", "terminal", "notes",
        "office", "claude", "mail", "calendar",
    }

    install_import_stubs()
    sys.path.insert(0, str(ROOT))
    package = __import__("ovos_skill_jarvis_dispatcher")
    skill = package.create_skill()
    assert type(skill).__name__ == "JarvisDispatcherSkill"

    print("PASS: 9 modules compile")
    print("PASS: 44 intents match the known-good inventory")
    print("PASS: 859 vocabulary registrations are present")
    print("PASS: package imports and create_skill() succeeds")


if __name__ == "__main__":
    main()
