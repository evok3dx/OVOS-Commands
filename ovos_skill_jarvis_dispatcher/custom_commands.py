"""Safe, user-managed phrases for existing Jarvis actions."""

import json
import os
import re
import tempfile
from pathlib import Path


CONFIG_VERSION = 1
MAX_CUSTOM_PHRASES = 200
MAX_PHRASE_LENGTH = 80
DEFAULT_CONFIG_PATH = Path.home() / ".config/jarvis/custom-commands.json"
RESERVED_PHRASES = {"cancel", "never mind", "nevermind", "stop", "wait"}

ENTITY_ACTIONS = {
    "MuteSystemMicrophoneCommand": "system.mute_microphone",
    "MuteSystemAudioCommand": "system.mute_all_audio",
    "MuteJarvisCommand": "system.mute_jarvis",
    "PressEnterCommand": "system.press_enter",
    "InsertNewLineCommand": "system.insert_new_line",
    "PressEscapeCommand": "system.press_escape",
    "PlayMediaCommand": "media.play",
    "PauseMediaCommand": "media.pause",
    "StopMediaCommand": "media.stop",
    "NextMediaCommand": "media.next",
    "PreviousMediaCommand": "media.previous",
    "CapsLockOnCommand": "system.caps_lock_on",
    "CapsLockOffCommand": "system.caps_lock_off",
    "CloseFocusedWindowCommand": "window.close",
    "MinimizeFocusedWindowCommand": "window.minimize",
    "MaximizeFocusedWindowCommand": "window.maximize",
    "RestoreFocusedWindowCommand": "window.restore",
    "ReadLastTypedTextCommand": "reading.last_typed",
    "ReadSelectedTextCommand": "reading.selection",
    "ReadVisiblePageCommand": "reading.page",
    "SelectAllTextCommand": "text.select_all",
    "DeleteSelectedTextCommand": "text.delete",
    "ClearFocusedTextCommand": "text.clear",
    "UndoTextEditCommand": "text.undo",
    "RedoTextEditCommand": "text.redo",
    "CopySelectedTextCommand": "text.copy",
    "CutSelectedTextCommand": "text.cut",
    "PasteTextCommand": "text.paste",
    "SaveDocumentCommand": "text.save",
    "PressTabCommand": "text.next_field",
    "PressShiftTabCommand": "text.previous_field",
    "SearchFocusedContentCommand": "text.search",
    "WriteFocusedTextCommand": "text.write",
    "StartSpeechNoteDictationCommand": "dictation.start",
    "PauseSpeechNoteDictationCommand": "dictation.pause",
    "ResumeSpeechNoteDictationCommand": "dictation.resume",
    "StopSpeechNoteDictationCommand": "dictation.stop",
    "BraveSearchPromptCommand": "browser.search_brave",
    "FirefoxSearchPromptCommand": "browser.search_firefox",
    "YouTubeSearchPromptCommand": "browser.search_youtube",
    "YouTubeShortsCommand": "browser.youtube_shorts",
    "NewNoteCommand": "notes.new",
    "SearchNotesCommand": "notes.search",
    "NewEmailCommand": "mail.new",
    "SearchMailCommand": "mail.search",
    "JoinZoomMeetingCommand": "zoom.join",
    "SearchCodexCommand": "codex.search",
    "ReadCodexResponseCommand": "codex.read",
    "ReadClaudeResponseCommand": "claude_agent.read",
    "ReadLatestResponseCommand": "response.read_latest",
    "NewClaudeChatCommand": "claude_desktop.new_chat",
    "NewClaudeAgentCommand": "claude_agent.new",
    "CreateClaudeSubagentCommand": "claude_agent.create_subagent",
    "ShowClaudeAgentsCommand": "claude_agent.show_agents",
    "ResumeClaudeAgentCommand": "claude_agent.resume",
    "NaturalDateCommand": "date.today",
}

DESKTOP_ENTITY_OPERATIONS = {
    "OpenDesktopAppCommand": "open",
    "FocusDesktopAppCommand": "focus",
    "MinimizeDesktopAppCommand": "minimize",
    "CloseDesktopAppCommand": "close",
    "MaximizeDesktopAppCommand": "maximize",
}


try:
    from .action_registry import BASE_ACTIONS, action_catalog, dispatch_action
except ImportError:
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "jarvis_action_registry", Path(__file__).with_name("action_registry.py")
    )
    _registry = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_registry)
    BASE_ACTIONS = _registry.BASE_ACTIONS
    action_catalog = _registry.action_catalog
    dispatch_action = _registry.dispatch_action


class CustomCommandError(ValueError):
    """Raised when a custom-command file is invalid or unsafe."""


def normalize_phrase(value):
    """Return the exact normalized form used for matching and conflicts."""
    phrase = re.sub(r"\s+", " ", str(value).lower()).strip(" .?!,;:")
    return phrase


def validate_mapping(raw, profile=None, builtin_phrases=()):
    """Validate and normalize one custom phrase-to-action mapping."""
    if not isinstance(raw, dict):
        raise CustomCommandError("The phrases section must be an object.")
    if len(raw) > MAX_CUSTOM_PHRASES:
        raise CustomCommandError(
            f"At most {MAX_CUSTOM_PHRASES} personal phrases are allowed."
        )

    catalog = action_catalog(profile)
    builtins = {normalize_phrase(phrase) for phrase in builtin_phrases}
    normalized = {}

    for original_phrase, action_id in raw.items():
        if not isinstance(original_phrase, str) or not isinstance(action_id, str):
            raise CustomCommandError("Every phrase and action must be text.")
        if any(character in original_phrase for character in "\r\n\t"):
            raise CustomCommandError("A phrase cannot contain tabs or line breaks.")

        phrase = normalize_phrase(original_phrase)
        if len(phrase) < 2 or len(phrase) > MAX_PHRASE_LENGTH:
            raise CustomCommandError(
                f"Phrases must contain 2 to {MAX_PHRASE_LENGTH} characters."
            )
        if not phrase.isprintable() or not any(character.isalnum() for character in phrase):
            raise CustomCommandError(f"Invalid phrase: {original_phrase!r}")
        if phrase in RESERVED_PHRASES:
            raise CustomCommandError(f"Reserved conversation phrase: {phrase!r}")
        if phrase in builtins:
            raise CustomCommandError(f"Already a built-in phrase: {phrase!r}")
        if phrase in normalized:
            raise CustomCommandError(f"Duplicate personal phrase: {phrase!r}")
        if action_id not in catalog:
            raise CustomCommandError(f"Unknown or unavailable action: {action_id}")
        normalized[phrase] = action_id

    return dict(sorted(normalized.items()))


def read_mapping(path=None, profile=None, builtin_phrases=()):
    """Read a custom-command file; absence means no personal phrases."""
    selected_path = Path(path or os.environ.get(
        "JARVIS_CUSTOM_COMMANDS_PATH", DEFAULT_CONFIG_PATH
    ))
    if not selected_path.exists():
        return {}

    try:
        payload = json.loads(selected_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CustomCommandError(f"Could not read personal phrases: {error}") from error

    if not isinstance(payload, dict) or payload.get("version") != CONFIG_VERSION:
        raise CustomCommandError("Unsupported personal-phrases file version.")

    return validate_mapping(
        payload.get("phrases", {}),
        profile=profile,
        builtin_phrases=builtin_phrases,
    )


def write_mapping(mapping, path=None, profile=None, builtin_phrases=()):
    """Validate and atomically save personal phrases with private permissions."""
    normalized = validate_mapping(
        mapping, profile=profile, builtin_phrases=builtin_phrases
    )
    selected_path = Path(path or os.environ.get(
        "JARVIS_CUSTOM_COMMANDS_PATH", DEFAULT_CONFIG_PATH
    ))
    selected_path.parent.mkdir(parents=True, exist_ok=True)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix="custom-commands.", suffix=".tmp", dir=selected_path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(
                {"version": CONFIG_VERSION, "phrases": normalized},
                output,
                indent=2,
                sort_keys=True,
            )
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, selected_path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return normalized


def collect_builtin_phrases(profile):
    """Collect the installed built-in vocabulary without loading custom data."""
    try:
        from .vocabulary import register_skill_vocabulary
    except ImportError:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'jarvis_vocabulary', Path(__file__).with_name('vocabulary.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        register_skill_vocabulary = module.register_skill_vocabulary

    class Collector:
        def __init__(self, selected_profile):
            self._jarvis_profile = selected_profile
            self.registrations = []

        def register_vocabulary(self, phrase, entity):
            self.registrations.append((str(phrase), str(entity)))

    collector = Collector(profile)
    register_skill_vocabulary(collector, include_custom=False)
    return {normalize_phrase(phrase) for phrase, _entity in collector.registrations}


def collect_builtin_inventory(profile):
    """Group complete registered phrases by the action shown in the editor."""
    try:
        from .vocabulary import register_skill_vocabulary
    except ImportError:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'jarvis_vocabulary', Path(__file__).with_name('vocabulary.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        register_skill_vocabulary = module.register_skill_vocabulary

    class Collector:
        def __init__(self, selected_profile):
            self._jarvis_profile = selected_profile
            self.registrations = []

        def register_vocabulary(self, phrase, entity):
            self.registrations.append((normalize_phrase(phrase), str(entity)))

    collector = Collector(profile)
    register_skill_vocabulary(collector, include_custom=False)
    inventory = {
        action_id: set(details["examples"])
        for action_id, details in action_catalog(profile).items()
    }

    for phrase, entity in collector.registrations:
        action_id = ENTITY_ACTIONS.get(entity)
        if action_id:
            inventory[action_id].add(phrase)
            continue

        if entity == "BrowserNavigationCommand":
            browser_action = collector._browser_navigation_actions.get(phrase)
            action_id = f"browser.{browser_action}"
            if action_id in inventory:
                inventory[action_id].add(phrase)
            continue

        if entity == "HermesComposerCommand":
            hermes_action = collector._hermes_composer_actions.get(phrase)
            action_id = f"hermes.{hermes_action}"
            if action_id in inventory:
                inventory[action_id].add(phrase)
            continue

        operation = DESKTOP_ENTITY_OPERATIONS.get(entity)
        if operation:
            matches = []
            for app_id, definition in profile["applications"].items():
                for alias in definition["aliases"]:
                    if phrase.endswith(f" {normalize_phrase(alias)}"):
                        matches.append((len(alias), app_id))
            if matches:
                _length, app_id = max(matches)
                inventory[f"application.{operation}.{app_id}"].add(phrase)

    return {
        action_id: sorted(normalize_phrase(phrase) for phrase in phrases)
        for action_id, phrases in inventory.items()
    }


def register_custom_vocabulary(skill, builtin_phrases):
    """Load valid personal phrases without risking built-in skill startup."""
    try:
        mapping = read_mapping(
            profile=skill._jarvis_profile,
            builtin_phrases=builtin_phrases,
        )
    except CustomCommandError as error:
        skill.log.error("Personal command phrases were ignored: %s", error)
        mapping = {}

    skill._custom_command_actions = mapping
    for phrase in mapping:
        skill.register_vocabulary(phrase, "CustomCommandPhrase")


class CustomCommandsMixin:
    """Dispatch personal phrases only to explicitly implemented actions."""

    def _custom_address_prompt(self):
        self._run_browser_action("address")
        with self._message_lock:
            self._clear_message_state()
            self._message_stage = "browser_address"
            self._message_retries = 1
        self.activate(duration_minutes=1)
        self.speak("What should I enter?", expect_response=True, wait=True)
        self._arm_message_timeout(20)

    def _run_custom_command(self, message):
        matched = next(
            (
                value for key, value in message.data.items()
                if key.endswith("CustomCommandPhrase")
            ),
            message.data.get("utterance", ""),
        )
        phrase = normalize_phrase(matched)
        action_id = getattr(self, "_custom_command_actions", {}).get(phrase)
        if not action_id:
            self.log.warning("Unregistered personal phrase was ignored")
            return

        return dispatch_action(self, action_id, message)
