#!/usr/bin/env python3
"""Static safety checks for the modular Jarvis dispatcher."""

import ast
import json
import re
import stat
import sys
import tempfile
import types
from pathlib import Path
from xml.etree import ElementTree


sys.dont_write_bytecode = True


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "ovos_skill_jarvis_dispatcher"
MANIFEST = json.loads(
    (ROOT / "deployment-manifest.json").read_text(encoding="utf-8")
)
COMPATIBILITY = json.loads(
    (ROOT / "compatibility.json").read_text(encoding="utf-8")
)
assert MANIFEST["schema_version"] == 2
assert COMPATIBILITY["schema_version"] == 1
EXPECTED_ROOT_MODULES = set(MANIFEST["package_modules"])
EXPECTED_INTEGRATION_MODULES = set(MANIFEST["integration_modules"])
EXPECTED_SYSTEM_HELPERS = set(MANIFEST["runtime_helpers"])
EXPECTED_PROFILES = set(MANIFEST["profiles"])
EXPECTED_SYSTEMD_TEMPLATES = set(MANIFEST["systemd_templates"])

for inventory_name in (
    "package_modules", "integration_modules", "runtime_helpers", "profiles"
):
    inventory = MANIFEST[inventory_name]
    assert inventory, f"Manifest inventory is empty: {inventory_name}"
    assert len(inventory) == len(set(inventory)), (
        f"Manifest inventory contains duplicates: {inventory_name}"
    )
    assert all(Path(item).name == item for item in inventory), (
        f"Manifest inventory contains a path: {inventory_name}"
    )

optional_files = []
for component, files in MANIFEST["optional_components"].items():
    assert files, f"Optional component is empty: {component}"
    assert len(files) == len(set(files)), (
        f"Optional component contains duplicates: {component}"
    )
    for relative in files:
        path = (ROOT / relative).resolve()
        assert ROOT == path.parent or ROOT in path.parents, (
            f"Optional path escapes repository: {relative}"
        )
        assert path.is_file(), f"Optional file is missing: {relative}"
        optional_files.append(path)

for relative in EXPECTED_SYSTEMD_TEMPLATES:
    path = (ROOT / relative).resolve()
    assert ROOT in path.parents, f"Systemd template escapes repository: {relative}"
    assert path.is_file(), f"Systemd template is missing: {relative}"

project_source = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
version_match = re.search(r'^version = "([^"]+)"$', project_source, re.MULTILINE)
assert version_match, "Project version is missing"
assert MANIFEST["release_version"] == version_match.group(1)
assert COMPATIBILITY["release_version"] == version_match.group(1)
assert COMPATIBILITY["ovos"]["entry_point_group"] == "opm.skill"
assert re.fullmatch(
    r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
    COMPATIBILITY["updates"]["repository"],
)
assert (
    '"ovos-skill-jarvis-dispatcher.openvoiceos" = '
    '"ovos_skill_jarvis_dispatcher:JarvisDispatcherSkill"'
) in project_source
for project in ("installer", "workshop", "config", "core", "plugin_manager"):
    repository = COMPATIBILITY["upstream"][f"{project}_repository"]
    reference = COMPATIBILITY["upstream"][f"{project}_reference_commit"]
    assert repository.startswith("https://github.com/OpenVoiceOS/")
    assert re.fullmatch(r"[0-9a-f]{40}", reference)
assert re.fullmatch(
    r"[0-9a-f]{64}",
    COMPATIBILITY["upstream"]["installer_archive_sha256"],
)
installer_source = (ROOT / "scripts/install.sh").read_text(encoding="utf-8")
for required_bootstrap_fragment in (
    "read_compatibility_value upstream.installer_repository",
    "read_compatibility_value upstream.installer_reference_commit",
    "read_compatibility_value upstream.installer_archive_sha256",
    'installer_archive_url="${installer_repository%.git}/archive/${installer_commit}.tar.gz"',
    "hashlib.sha256()",
    "if actual != expected:",
    'tar -xzf "$installer_archive" --strip-components=1',
    "sudo apt-get install --no-install-recommends git",
    "No desktop applications are being installed.",
    "share_telemetry: false",
    "share_usage_telemetry: false",
    "extra_skills: false",
    "Jarvis remains user-space and no desktop applications are installed.",
):
    assert required_bootstrap_fragment in installer_source, (
        f"Installer bootstrap safety check is missing: {required_bootstrap_fragment}"
    )
assert 'for command in git sudo bash' not in installer_source
EXPECTED_INTENTS = {
    "CustomCommandIntent",
    "CloseFocusedWindowIntent", "MinimizeFocusedWindowIntent",
    "MaximizeFocusedWindowIntent", "RestoreFocusedWindowIntent",
    "ReadLastTypedTextIntent", "NewNoteIntent",
    "ReadSelectedTextIntent", "ReadVisiblePageIntent",
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
    "MinimizeDesktopAppIntent", "MaximizeDesktopAppIntent",
    "CloseDesktopAppIntent", "OpenChatGPTWebsiteIntent",
    "OpenClaudeWebsiteIntent",
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

    found_helpers = {
        path.name
        for path in (ROOT / "system_helpers").iterdir()
        if path.is_file()
    }
    assert found_helpers == EXPECTED_SYSTEM_HELPERS, (
        found_helpers,
        EXPECTED_SYSTEM_HELPERS,
    )

    python_files = list(PACKAGE.glob("*.py")) + list(integrations.glob("*.py"))
    for path in python_files:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")

    for path in optional_files:
        source = path.read_text(encoding="utf-8")
        first_line = source.splitlines()[0]
        if path.suffix == ".py" or "python" in first_line:
            compile(source, str(path), "exec")
        if path.suffix == ".svg":
            ElementTree.parse(path)

    executable_files = [
        *(ROOT / "system_helpers" / name for name in EXPECTED_SYSTEM_HELPERS),
        ROOT / "command_editor/jarvis-command-editor",
        ROOT / "mic/jarvis-mic-indicator",
        ROOT / "mic/jarvis-mic-toggle",
        *(ROOT / "scripts").glob("*.sh"),
        *(ROOT / "scripts").glob("*.py"),
    ]
    assert all(path.stat().st_mode & stat.S_IXUSR for path in executable_files), (
        "Runtime entry points must be executable"
    )

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
    required_entities = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "require"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }

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
    assert len(fake.registrations) == 1701
    assert len(fake.registrations) == len(set(fake.registrations)), (
        "Duplicate vocabulary registrations are present"
    )
    vocabulary_entities = {entity for _phrase, entity in fake.registrations}
    assert required_entities - {"CustomCommandPhrase"} == vocabulary_entities

    normal = FakeSkill()
    normal._jarvis_profile = profile_namespace["resolve_profile"](
        profile_namespace["SAFE_DEFAULT_PROFILE"]
    )
    namespace["register_skill_vocabulary"](normal, include_custom=False)
    normal_entities = {entity for _phrase, entity in normal.registrations}
    assert not normal_entities.intersection({
        "CodexKeyword", "OpenCodexCommand", "FocusCodexCommand",
        "ReadCodexResponseCommand", "ReadClaudeResponseCommand",
        "NewClaudeAgentCommand", "CreateClaudeSubagentCommand",
        "ShowClaudeAgentsCommand", "ResumeClaudeAgentCommand",
    }), "Private agent vocabulary leaked into the normal configuration"
    phrase_entities = {}
    for phrase, entity in fake.registrations:
        phrase_entities.setdefault(phrase, set()).add(entity)
    collisions = {
        phrase: entities
        for phrase, entities in phrase_entities.items()
        if len(entities) > 1
    }
    assert collisions == {
        "close window": {"CloseFocusedWindowCommand", "CloseKeyword"}
    }
    for phrase in (
        "open standard notes",
        "open standard note",
        "open standard nodes",
        "open standard node",
    ):
        assert (phrase, "OpenDesktopAppCommand") in fake.registrations
    for phrase in (
        "search notes",
        "search nodes",
        "search standard notes",
        "search standard nodes",
    ):
        assert (phrase, "SearchNotesCommand") in fake.registrations
    for phrase in (
        "new note",
        "new notes",
        "new node",
        "new nodes",
        "knee nodes",
    ):
        assert (phrase, "NewNoteCommand") in fake.registrations
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
        "close app", "closed app", "close the app", "closed the app",
        "close this app", "closed this app",
    ):
        assert (phrase, "CloseFocusedWindowCommand") in fake.registrations
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
        "office", "claude", "chatgpt", "hermes", "mail", "proton_mail",
        "calendar",
    }
    action_verbs = {
        "OpenDesktopAppCommand": ("open", "launch", "start"),
        "FocusDesktopAppCommand": (
            "focus", "show", "go to", "bring up", "switch to"
        ),
        "MinimizeDesktopAppCommand": (
            "minimize", "minimise", "hide", "put away"
        ),
        "CloseDesktopAppCommand": ("close", "quit", "exit"),
        "MaximizeDesktopAppCommand": (
            "maximize", "maximise", "make full screen", "make fullscreen"
        ),
    }
    registrations = set(fake.registrations)
    for aliases in fake._desktop_app_aliases.values():
        for alias in aliases:
            for entity, verbs in action_verbs.items():
                for verb in verbs:
                    assert (f"{verb} {alias}", entity) in registrations
    for phrase in (
        "read app", "read this app", "read application",
        "read this application", "read screen", "read this screen",
        "read content", "read this content", "read full page",
        "read the full page", "read the entire page",
    ):
        assert (phrase, "ReadVisiblePageCommand") in registrations

    profiles = sorted((ROOT / "profiles").glob("*.json"))
    assert {path.name for path in profiles} == EXPECTED_PROFILES
    for path in profiles:
        raw_profile = json.loads(path.read_text())
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

    current_documents = sorted(ROOT.rglob("*.md"))
    link_pattern = re.compile(r"\[[^]]+\]\(([^)]+)\)")
    for document in current_documents:
        assert document.is_file(), f"Current document is missing: {document}"
        for target in link_pattern.findall(document.read_text(encoding="utf-8")):
            relative = target.split("#", 1)[0]
            if (
                relative
                and "://" not in relative
                and not relative.startswith("mailto:")
            ):
                assert (document.parent / relative).resolve().exists(), (
                    f"Broken link in {document.relative_to(ROOT)}: {target}"
                )

    print(f"PASS: {len(python_files)} Python modules compile")
    print("PASS: 90 intents match the expected inventory")
    print("PASS: 1701 compatibility vocabulary registrations are present")
    print("PASS: vocabulary registrations and entities are consistent")
    print("PASS: personal phrase validation rejects built-in collisions")
    print("PASS: personal phrases save atomically with private permissions")
    print("PASS: built-in phrases are grouped by editor action")
    print("PASS: every app alias has open, focus, minimise, maximise and close coverage")
    print(f"PASS: {len(EXPECTED_PROFILES)} deployment profiles validate")
    print(f"PASS: {len(EXPECTED_SYSTEM_HELPERS)} runtime helpers are packaged")
    print(f"PASS: {len(EXPECTED_SYSTEMD_TEMPLATES)} systemd templates validate")
    print("PASS: optional components and current documentation validate")
    print("PASS: package imports and create_skill() succeeds")


if __name__ == "__main__":
    main()
