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
    "MuteJarvisCommand": "system.mute_jarvis",
    "CloseFocusedWindowCommand": "window.close",
    "MinimizeFocusedWindowCommand": "window.minimize",
    "MaximizeFocusedWindowCommand": "window.maximize",
    "RestoreFocusedWindowCommand": "window.restore",
    "ReadLastTypedTextCommand": "reading.last_typed",
    "ReadSelectedTextCommand": "reading.selection",
    "ReadVisiblePageCommand": "reading.page",
    "ReadFullPageCommand": "reading.page",
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
    "NewNoteCommand": "notes.new",
    "SearchNotesCommand": "notes.search",
    "NewEmailCommand": "mail.new",
    "SearchMailCommand": "mail.search",
    "JoinZoomMeetingCommand": "zoom.join",
    "SearchCodexCommand": "codex.search",
    "ReadCodexResponseCommand": "codex.read",
    "ReadClaudeResponseCommand": "claude_agent.read",
    "ReadLatestResponseCommand": "response.read_latest",
    "NaturalDateCommand": "date.today",
}

DESKTOP_ENTITY_OPERATIONS = {
    "OpenDesktopAppCommand": "open",
    "FocusDesktopAppCommand": "focus",
    "MinimizeDesktopAppCommand": "minimize",
    "CloseDesktopAppCommand": "close",
}


def _action(category, label, *examples):
    return {
        "category": category,
        "label": label,
        "examples": tuple(examples),
    }


BASE_ACTIONS = {
    "system.mute_microphone": _action(
        "System", "Mute the system microphone", "mute microphone"
    ),
    "system.mute_jarvis": _action(
        "System", "Mute Jarvis listening", "mute Jarvis"
    ),
    "window.close": _action("Windows", "Close focused window", "close window"),
    "window.minimize": _action(
        "Windows", "Minimize focused window", "minimize window"
    ),
    "window.maximize": _action(
        "Windows", "Maximize focused window", "maximize window"
    ),
    "window.restore": _action(
        "Windows", "Restore focused window", "restore window"
    ),
    "reading.last_typed": _action(
        "Reading", "Read last typed text", "read it back"
    ),
    "reading.selection": _action(
        "Reading", "Read selected text", "read selected text"
    ),
    "reading.page": _action("Reading", "Read visible page", "read this page"),
    "text.select_all": _action("Writing", "Select all text", "select all"),
    "text.delete": _action(
        "Writing", "Delete selected text", "delete selected text"
    ),
    "text.clear": _action("Writing", "Clear all focused text", "clear text"),
    "text.undo": _action("Writing", "Undo", "undo"),
    "text.redo": _action("Writing", "Redo", "redo"),
    "text.copy": _action("Writing", "Copy selected text", "copy"),
    "text.cut": _action("Writing", "Cut selected text", "cut"),
    "text.paste": _action("Writing", "Paste text", "paste"),
    "text.save": _action("Writing", "Save document", "save document"),
    "text.next_field": _action("Writing", "Move to next field", "next field"),
    "text.previous_field": _action(
        "Writing", "Move to previous field", "previous field"
    ),
    "text.search": _action("Writing", "Search focused content", "search this page"),
    "text.write": _action("Writing", "Write into focused field", "write this"),
    "dictation.start": _action("Dictation", "Start dictation", "start dictation"),
    "dictation.pause": _action("Dictation", "Pause dictation", "pause dictation"),
    "dictation.resume": _action(
        "Dictation", "Resume dictation", "resume dictation"
    ),
    "dictation.stop": _action("Dictation", "Stop dictation", "stop dictation"),
    "browser.scroll_down": _action("Browser", "Scroll down", "scroll down"),
    "browser.scroll_up": _action("Browser", "Scroll up", "scroll up"),
    "browser.page_down": _action("Browser", "Page down", "page down"),
    "browser.page_up": _action("Browser", "Page up", "page up"),
    "browser.top": _action("Browser", "Go to page top", "go to the top"),
    "browser.bottom": _action(
        "Browser", "Go to page bottom", "go to the bottom"
    ),
    "browser.back": _action("Browser", "Go back", "go back"),
    "browser.forward": _action("Browser", "Go forward", "go forward"),
    "browser.new_tab": _action("Browser", "Open new tab", "new tab"),
    "browser.close_tab": _action("Browser", "Close current tab", "close tab"),
    "browser.refresh": _action("Browser", "Refresh page", "refresh page"),
    "browser.address": _action(
        "Browser", "Enter an address", "focus the address bar"
    ),
    "browser.search_brave": _action("Browser", "Search with Brave", "search Brave"),
    "browser.search_firefox": _action(
        "Browser", "Search with Firefox", "search Firefox"
    ),
    "notes.new": _action("Notes", "Create a new note", "new note"),
    "notes.search": _action("Notes", "Search notes", "search notes"),
    "mail.new": _action("Mail", "Create a new email", "new email"),
    "mail.search": _action("Mail", "Search mail", "search mail"),
    "zoom.join": _action("Meetings", "Join copied Zoom meeting", "join meeting"),
    "codex.open": _action("AI", "Open Codex agent", "open Codex agent"),
    "codex.focus": _action("AI", "Focus Codex agent", "focus Codex agent"),
    "codex.minimize": _action(
        "AI", "Minimize Codex agent", "minimize Codex agent"
    ),
    "codex.close": _action("AI", "Close Codex agent", "close Codex agent"),
    "codex.message": _action("AI", "Message Codex agent", "message Codex agent"),
    "codex.search": _action("AI", "Research with Codex", "research with Codex"),
    "codex.read": _action("AI", "Read Codex response", "read Codex response"),
    "claude_agent.open": _action(
        "AI", "Open Claude agent", "open Claude agent"
    ),
    "claude_agent.focus": _action(
        "AI", "Focus Claude agent", "focus Claude agent"
    ),
    "claude_agent.minimize": _action(
        "AI", "Minimize Claude agent", "minimize Claude agent"
    ),
    "claude_agent.close": _action(
        "AI", "Close Claude agent", "close Claude agent"
    ),
    "claude_agent.message": _action(
        "AI", "Message Claude agent", "message Claude agent"
    ),
    "claude_agent.read": _action(
        "AI", "Read Claude agent response", "read Claude response"
    ),
    "claude_desktop.message": _action(
        "AI", "Message Claude Desktop", "message Claude"
    ),
    "response.read_latest": _action("AI", "Read latest response", "read it to me"),
    "date.today": _action("Information", "Read today's date", "what is today's date"),
}


class CustomCommandError(ValueError):
    """Raised when a custom-command file is invalid or unsafe."""


def normalize_phrase(value):
    """Return the exact normalized form used for matching and conflicts."""
    phrase = re.sub(r"\s+", " ", str(value).lower()).strip(" .?!,;:")
    return phrase


def action_catalog(profile=None):
    """Return friendly actions, including profile-approved applications."""
    catalog = dict(BASE_ACTIONS)
    applications = (profile or {}).get("applications", {})
    for app_id, definition in applications.items():
        display = definition.get("display_name", app_id.replace("_", " ").title())
        primary_alias = next(iter(definition.get("aliases", (app_id,))), app_id)
        for operation, verb in (
            ("open", "Open"),
            ("focus", "Focus"),
            ("minimize", "Minimize"),
            ("close", "Close"),
        ):
            catalog[f"application.{operation}.{app_id}"] = _action(
                "Applications",
                f"{verb} {display}",
                f"{operation} {primary_alias}",
            )
    return catalog


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
    from .vocabulary import register_skill_vocabulary

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
    from .vocabulary import register_skill_vocabulary

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

        direct_handlers = {
            "system.mute_microphone": "handle_mute_system_microphone",
            "system.mute_jarvis": "handle_mute_jarvis",
            "window.close": "handle_close_focused_window",
            "window.minimize": "handle_minimize_focused_window",
            "window.maximize": "handle_maximize_focused_window",
            "window.restore": "handle_restore_focused_window",
            "reading.last_typed": "handle_read_last_typed_text",
            "reading.selection": "handle_read_selected_text",
            "reading.page": "handle_read_visible_page",
            "text.select_all": "handle_select_all_text",
            "text.delete": "handle_delete_selected_text",
            "text.clear": "handle_clear_focused_text",
            "text.undo": "handle_undo_text_edit",
            "text.redo": "handle_redo_text_edit",
            "text.copy": "handle_copy_selected_text",
            "text.cut": "handle_cut_selected_text",
            "text.paste": "handle_paste_text",
            "text.save": "handle_save_document",
            "text.next_field": "handle_press_tab",
            "text.previous_field": "handle_press_shift_tab",
            "text.search": "handle_search_focused_content",
            "text.write": "handle_write_focused_text",
            "dictation.start": "handle_start_speech_note_dictation",
            "dictation.pause": "handle_pause_speech_note_dictation",
            "dictation.resume": "handle_resume_speech_note_dictation",
            "dictation.stop": "handle_stop_speech_note_dictation",
            "notes.new": "handle_new_note",
            "notes.search": "handle_search_notes",
            "mail.new": "handle_new_email",
            "mail.search": "handle_search_mail",
            "zoom.join": "handle_join_zoom_meeting",
            "date.today": "handle_natural_date",
        }
        handler_name = direct_handlers.get(action_id)
        if handler_name:
            getattr(self, handler_name)(message)
            return

        if action_id.startswith("application."):
            _prefix, operation, app_id = action_id.split(".", 2)
            if app_id not in self._desktop_app_aliases:
                self.log.warning("Unavailable application action was ignored")
                return
            self._run_desktop_app_action(app_id, operation)
            return

        if action_id.startswith("browser."):
            browser_action = action_id.removeprefix("browser.")
            if browser_action == "search_brave":
                self._prompt_browser_search(message, "brave")
            elif browser_action == "search_firefox":
                self._prompt_browser_search(message, "firefox")
            elif browser_action == "address":
                self._custom_address_prompt()
            else:
                self._run_browser_action(browser_action)
            return

        if action_id.startswith("codex."):
            operation = action_id.removeprefix("codex.")
            if operation in {"open", "focus", "minimize", "close"}:
                self._window_action(operation, "codex")
            elif operation == "message":
                self._message_agent("codex")
            elif operation == "search":
                self._search_codex()
            elif operation == "read":
                self._read_agent_response("codex")
            return

        if action_id.startswith("claude_agent."):
            operation = action_id.removeprefix("claude_agent.")
            if operation in {"open", "focus", "minimize", "close"}:
                self._window_action(operation, "claude")
            elif operation == "message":
                self._message_agent("claude")
            elif operation == "read":
                self._read_agent_response("claude")
            return

        if action_id == "claude_desktop.message":
            self._message_claude_desktop()
            return
        if action_id == "response.read_latest":
            self._read_agent_response()
            return

        self.log.error("Unsupported personal action reached dispatcher: %s", action_id)
