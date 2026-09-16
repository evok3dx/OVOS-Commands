#!/usr/bin/env python3
"""Static safety checks for the modular Jarvis dispatcher."""

import ast
import py_compile
import stat
import sys
import tempfile
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "ovos_skill_jarvis_dispatcher"
EXPECTED_ROOT_MODULES = {
    "__init__.py",
    "agents.py",
    "browser.py",
    "conversation.py",
    "custom_commands.py",
    "desktop.py",
    "dictation.py",
    "helpers.py",
    "profile.py",
    "system_audio.py",
    "system_controls.py",
    "text_editing.py",
    "vocabulary.py",
    "wakeword.py",
}
EXPECTED_INTEGRATION_MODULES = {
    "__init__.py",
    "proton_mail.py",
    "standard_notes.py",
    "zoom.py",
    "claude_desktop.py",
    "hermes_desktop.py",
}
EXPECTED_INTENTS = {
    "CustomCommandIntent",
    "CloseFocusedWindowIntent", "MinimizeFocusedWindowIntent",
    "MaximizeFocusedWindowIntent", "RestoreFocusedWindowIntent",
    "ReadLastTypedTextIntent", "NewNoteIntent",
    "ReadSelectedTextIntent", "ReadVisiblePageIntent", "ReadFullPageIntent",
    "SelectAllTextIntent", "DeleteSelectedTextIntent",
    "ClearFocusedTextIntent", "UndoTextEditIntent", "RedoTextEditIntent",
    "CopySelectedTextIntent", "CutSelectedTextIntent",
    "PasteTextIntent", "SaveDocumentIntent",
    "SearchFocusedContentIntent", "SearchNotesIntent",
    "PressTabIntent", "PressShiftTabIntent",
    "NewEmailIntent", "SearchMailIntent",
    "JoinZoomMeetingIntent",
    "MuteSystemMicrophoneIntent",
    "MuteSystemAudioIntent",
    "MuteJarvisIntent",
    "PressEnterIntent",
    "PlayMediaIntent", "PauseMediaIntent", "StopMediaIntent",
    "NextMediaIntent", "PreviousMediaIntent",
    "CapsLockOnIntent", "CapsLockOffIntent",
    "HermesComposerIntent",
    "StartSpeechNoteDictationIntent", "PauseSpeechNoteDictationIntent",
    "ResumeSpeechNoteDictationIntent", "StopSpeechNoteDictationIntent",
    "WriteFocusedTextIntent", "BraveSearchPromptIntent",
    "FirefoxSearchPromptIntent", "YouTubeSearchPromptIntent",
    "YouTubeShortsIntent", "BrowserNavigationIntent",
    "OpenDesktopAppIntent", "FocusDesktopAppIntent",
    "MinimizeDesktopAppIntent", "CloseDesktopAppIntent",
    "OpenCodexCommandIntent", "FocusCodexCommandIntent",
    "SearchCodexIntent", "ReadCodexResponseIntent",
    "ReadClaudeResponseIntent", "ReadLatestResponseIntent",
    "OpenClaudeAliasIntent", "NaturalDateIntent", "OpenCodexIntent",
    "OpenClaudeIntent", "FocusCodexIntent", "FocusClaudeIntent",
    "NewClaudeChatIntent",
    "NewClaudeAgentIntent", "CreateClaudeSubagentIntent",
    "ShowClaudeAgentsIntent", "ResumeClaudeAgentIntent",
    "MinimizeCodexIntent", "MinimizeClaudeIntent",
    "CloseCodexWindowIntent", "CloseClaudeWindowIntent",
    "MessageCodexIntent", "MessageClaudeIntent", "WriteCodexIntent",
    "WriteClaudeIntent", "TypeCodexIntent", "TypeClaudeIntent",
    "SpeakCodexIntent", "SpeakClaudeIntent", "TalkCodexIntent",
    "TalkClaudeIntent",
    "MessageHermesIntent", "WriteHermesIntent", "TypeHermesIntent",
    "SpeakHermesIntent", "TalkHermesIntent",
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
    namespace["register_skill_vocabulary"](fake, include_custom=False)
    assert len(fake.registrations) == 1259
    for phrase in ("claude", "cloud", "clawed", "called"):
        assert (
            phrase,
            "ClaudeKeyword",
        ) in fake.registrations
    for phrase in (
        "hermes", "hermas", "omos",
        "hermes desktop", "hermes app",
    ):
        assert (phrase, "HermesKeyword") in fake.registrations
    assert (
        "message",
        "MessageKeyword",
    ) in fake.registrations
    for phrase in (
        "new claude chat",
        "new cloud chat",
        "a new cloud chat",
        "open a new clawed chat",
        "start a new chat with called",
    ):
        assert (phrase, "NewClaudeChatCommand") in fake.registrations
    for phrase, entity in (
        ("new claude agent", "NewClaudeAgentCommand"),
        ("start a new cloud agent", "NewClaudeAgentCommand"),
        ("create a clawed subagent", "CreateClaudeSubagentCommand"),
        ("show called agents", "ShowClaudeAgentsCommand"),
        ("resume cloud agent", "ResumeClaudeAgentCommand"),
    ):
        assert (phrase, entity) in fake.registrations
    for phrase, entity in (
        ("write", "WriteKeyword"),
        ("type", "TypeKeyword"),
        ("speak", "SpeakKeyword"),
        ("talk", "TalkKeyword"),
    ):
        assert (phrase, entity) in fake.registrations
    for phrase in ("mute mic", "mute microphone"):
        assert (
            phrase,
            "MuteSystemMicrophoneCommand",
        ) in fake.registrations
    for phrase in ("mute system", "mute everything"):
        assert (
            phrase,
            "MuteSystemAudioCommand",
        ) in fake.registrations
    for phrase in ("mute jarvis", "stop jarvis listening"):
        assert (
            phrase,
            "MuteJarvisCommand",
        ) in fake.registrations
    for phrase in (
        "press enter", "press return", "press send", "hit enter", "hit return",
    ):
        assert (phrase, "PressEnterCommand") in fake.registrations
    media_commands = {
        "PlayMediaCommand": ("play media", "resume playback", "play music"),
        "PauseMediaCommand": ("pause media", "pause playback", "pause music"),
        "StopMediaCommand": ("stop media", "stop playback", "stop playing"),
        "NextMediaCommand": ("next track", "next song", "skip track"),
        "PreviousMediaCommand": (
            "previous track", "previous song", "back track",
        ),
    }
    for entity, phrases in media_commands.items():
        for phrase in phrases:
            assert (phrase, entity) in fake.registrations
    for phrase in ("caps lock on", "enable caps lock"):
        assert (phrase, "CapsLockOnCommand") in fake.registrations
    for phrase in ("caps lock off", "disable caps lock"):
        assert (phrase, "CapsLockOffCommand") in fake.registrations
    for phrase in (
        "focus hermes composer", "open hermes model picker",
        "new line in hermes", "queue hermes message",
        "send next hermes message", "open hermes commands",
        "reference file in hermes", "cancel hermes run",
    ):
        assert (phrase, "HermesComposerCommand") in fake.registrations
    for phrase in (
        "read window",
        "read this window",
        "read current window",
        "read the complete page",
        "please read the complete page",
        "read the whole page",
        "please read the whole page",
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
    for phrase in (
        "search page", "search this page", "search the page",
        "find on page", "find on this page", "search document",
        "search this document", "find in this document",
        "search this note", "find in this note",
        "search this node", "find in this node",
    ):
        assert (phrase, "SearchFocusedContentCommand") in fake.registrations
    for phrase in (
        "search notes", "search my notes", "find a note",
        "find note", "look up a note", "look up notes",
        "look up my notes", "look for a note", "look for notes",
    ):
        assert (phrase, "SearchNotesCommand") in fake.registrations
    for phrase in (
        "press tab", "tab", "next field", "next box",
        "go to next field", "go to the next field",
        "move to next field", "move to the next field",
    ):
        assert (phrase, "PressTabCommand") in fake.registrations
    for phrase in (
        "press shift tab", "shift tab", "previous field", "previous box",
        "go to previous field", "go to the previous field",
        "move to previous field", "move to the previous field",
    ):
        assert (phrase, "PressShiftTabCommand") in fake.registrations
    for phrase in (
        "new email", "create new email", "create an email",
        "compose email", "compose an email", "write a new email",
        "write an email",
    ):
        assert (phrase, "NewEmailCommand") in fake.registrations
    for phrase in (
        "search mail", "search my mail", "search email", "search my email",
        "find an email", "find email", "look up an email", "look through my mail",
    ):
        assert (phrase, "SearchMailCommand") in fake.registrations
    for phrase in (
        "join meeting", "join the meeting", "join zoom meeting",
        "join the zoom meeting", "join copied meeting",
        "join copied zoom meeting",
    ):
        assert (phrase, "JoinZoomMeetingCommand") in fake.registrations
    for phrase in (
        "search youtube", "search you tube", "search on youtube",
        "search in youtube", "youtube search", "you tube search",
    ):
        assert (phrase, "YouTubeSearchPromptCommand") in fake.registrations
    for phrase in (
        "go to youtube shorts", "open youtube shorts", "youtube shorts",
        "show youtube shorts", "go to youtube reels",
        "open youtube reels", "youtube reels", "show youtube reels",
    ):
        assert (phrase, "YouTubeShortsCommand") in fake.registrations
    assert len(fake._browser_navigation_actions) == 68
    assert set(fake._desktop_app_aliases) == {
        "brave", "firefox", "signal", "zoom", "terminal", "notes",
        "office", "claude", "hermes", "mail", "calendar",
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

    from ovos_skill_jarvis_dispatcher.custom_commands import (
        collect_builtin_inventory,
        read_mapping,
        validate_mapping,
        write_mapping,
    )

    assert validate_mapping(
        {"show my notes": "application.open.notes"},
        profile=brain_profile,
        builtin_phrases={"open notes"},
    ) == {"show my notes": "application.open.notes"}
    try:
        validate_mapping(
            {"open notes": "application.open.notes"},
            profile=brain_profile,
            builtin_phrases={"open notes"},
        )
    except ValueError:
        pass
    else:
        raise AssertionError("A built-in phrase collision was accepted")

    inventory = collect_builtin_inventory(brain_profile)
    assert set(inventory["mail.new"]) == {
        "new email", "create new email", "create an email",
        "compose email", "compose an email", "write a new email",
        "write an email",
    }
    assert set(inventory["browser.search_youtube"]) == {
        "search youtube", "search you tube", "search on youtube",
        "search in youtube", "youtube search", "you tube search",
    }
    assert set(inventory["browser.youtube_shorts"]) == {
        "go to youtube shorts", "open youtube shorts", "youtube shorts",
        "show youtube shorts", "go to youtube reels",
        "open youtube reels", "youtube reels", "show youtube reels",
    }
    assert set(inventory["hermes.focus_composer"]) == {
        "focus hermes composer", "go to hermes composer",
        "focus the hermes composer", "focus composer in hermes",
    }
    assert set(inventory["hermes.command_palette"]) == {
        "open hermes commands", "show hermes commands",
        "open hermes slash commands", "show hermes command palette",
    }
    with tempfile.TemporaryDirectory() as directory:
        custom_path = Path(directory) / "custom-commands.json"
        written = write_mapping(
            {"show my notes": "application.open.notes"},
            path=custom_path,
            profile=brain_profile,
            builtin_phrases={"open notes"},
        )
        assert read_mapping(
            path=custom_path,
            profile=brain_profile,
            builtin_phrases={"open notes"},
        ) == written
        assert stat.S_IMODE(custom_path.stat().st_mode) == 0o600

    print(f"PASS: {len(python_files)} Python modules compile")
    print("PASS: 88 intents match the expected inventory")
    print("PASS: 1259 vocabulary registrations are present")
    print("PASS: personal phrase validation rejects built-in collisions")
    print("PASS: personal phrases save atomically with private permissions")
    print("PASS: built-in phrases are grouped by editor action")
    print("PASS: 3 deployment profiles validate")
    print("PASS: package imports and create_skill() succeeds")


if __name__ == "__main__":
    main()
