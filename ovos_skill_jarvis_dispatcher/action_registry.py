"""Single allowlisted catalogue and dispatcher shared by personal phrases and AI."""

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
    "system.mute_all_audio": _action(
        "System", "Mute all system audio", "mute system", "mute everything"
    ),
    "system.mute_jarvis": _action(
        "System", "Mute Jarvis listening", "mute Jarvis"
    ),
    "system.press_escape": _action("Keyboard", "Press Escape", "press escape"),
    "system.press_enter": _action(
        "System", "Press Enter in the focused app", "press Enter"
    ),
    "system.insert_new_line": _action(
        "Writing", "Insert a new line in the focused app", "new line"
    ),
    "system.caps_lock_on": _action(
        "System", "Turn Caps Lock on", "caps lock on"
    ),
    "system.caps_lock_off": _action(
        "System", "Turn Caps Lock off", "caps lock off"
    ),
    "media.play": _action("Media", "Play media", "play media"),
    "media.pause": _action("Media", "Pause media", "pause media"),
    "media.stop": _action("Media", "Stop media", "stop media"),
    "media.next": _action("Media", "Play next track", "next track"),
    "media.previous": _action(
        "Media", "Play previous track", "previous track"
    ),
    "hermes.focus_composer": _action(
        "Hermes", "Focus the composer", "focus Hermes composer"
    ),
    "hermes.message": _action(
        "Hermes", "Message Hermes",
        "message Hermes", "ask Hermes", "tell Hermes",
        "write to Hermes", "type into Hermes", "talk to Hermes"
    ),
    "hermes.model_picker": _action(
        "Hermes", "Open the model picker", "open Hermes model picker"
    ),
    "hermes.insert_newline": _action(
        "Hermes", "Insert a new line", "new line in Hermes"
    ),
    "hermes.queue_message": _action(
        "Hermes", "Queue the current message", "queue Hermes message"
    ),
    "hermes.send_queued": _action(
        "Hermes", "Send the next queued turn", "send next Hermes message"
    ),
    "hermes.command_palette": _action(
        "Hermes", "Open slash commands", "open Hermes commands"
    ),
    "hermes.reference": _action(
        "Hermes", "Reference a file or folder", "reference file in Hermes"
    ),
    "hermes.cancel": _action(
        "Hermes", "Cancel the run or close a popup", "cancel Hermes run"
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
    "browser.search_youtube": _action(
        "Browser", "Search YouTube", "search YouTube"
    ),
    "files.search": _action("Files", "Search local filenames", "find a file"),
    "browser.youtube_shorts": _action(
        "Browser", "Open YouTube Shorts", "open YouTube Shorts"
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
    "claude_agent.new": _action(
        "AI", "Start a new Claude agent session", "new Claude agent"
    ),
    "claude_agent.create_subagent": _action(
        "AI", "Create a Claude subagent", "create a Claude subagent"
    ),
    "claude_agent.show_agents": _action(
        "AI", "Show Claude agents", "show Claude agents"
    ),
    "claude_agent.resume": _action(
        "AI", "Resume Claude agent", "resume Claude agent"
    ),
    "claude_desktop.message": _action(
        "AI", "Message Claude", "message Claude"
    ),
    "claude_desktop.new_chat": _action(
        "AI", "Start a new Claude chat", "new Claude chat"
    ),
    "response.read_latest": _action("AI", "Read latest response", "read it to me"),
    "date.today": _action("Information", "Read today's date", "what is today's date"),
}


def action_catalog(profile=None):
    """Return friendly actions, including profile-approved applications."""
    catalog = dict(BASE_ACTIONS)
    agents_enabled = bool(
        (profile or {}).get("private_extensions", {}).get("agents", False)
    )
    if not agents_enabled:
        catalog = {
            action_id: definition
            for action_id, definition in catalog.items()
            if not action_id.startswith(("codex.", "claude_agent."))
            and action_id != "response.read_latest"
        }
    applications = (profile or {}).get("applications", {})
    for app_id, definition in applications.items():
        display = definition.get("display_name", app_id.replace("_", " ").title())
        primary_alias = next(iter(definition.get("aliases", (app_id,))), app_id)
        for operation, verb in (
            ("open", "Open"),
            ("focus", "Focus"),
            ("minimize", "Minimize"),
            ("maximize", "Maximize"),
            ("close", "Close"),
        ):
            catalog[f"application.{operation}.{app_id}"] = _action(
                "Applications",
                f"{verb} {display}",
                f"{operation} {primary_alias}",
            )
    return {action_id: dict(details, **action_policy(action_id))
            for action_id, details in catalog.items()}



# Exposure is an explicit allowlist. New actions remain hidden until reviewed.
ROUTER_ACTIONS = frozenset({
    "window.minimize", "window.maximize", "window.restore",
    "reading.page", "reading.selection",
    "media.play", "media.pause", "media.stop", "media.next", "media.previous",
    "browser.scroll_down", "browser.scroll_up", "browser.page_down",
    "browser.page_up", "browser.top", "browser.bottom", "browser.back",
    "browser.forward", "browser.new_tab", "browser.search_brave",
    "browser.search_firefox", "browser.search_youtube", "notes.search", "mail.search",
    "files.search",
})
APP_ROUTER_OPERATIONS = frozenset({"open", "focus", "minimize", "maximize"})

def action_policy(action_id):
    exposed = action_id in ROUTER_ACTIONS
    if action_id.startswith("application."):
        parts = action_id.split(".")
        exposed = len(parts) == 3 and parts[1] in APP_ROUTER_OPERATIONS
    return {"router_exposed": exposed, "risk": "low" if exposed else "restricted",
            "requires_confirmation": not exposed}

def router_catalog(profile):
    catalog = action_catalog(profile)
    apps = profile.get("applications", {})
    allowed = {}
    for action_id, details in catalog.items():
        policy = action_policy(action_id)
        if not policy["router_exposed"]:
            continue
        if action_id.startswith('application.'):
            _prefix, operation, app_id = action_id.split('.')
            definition = apps.get(app_id, {})
            # Generic named window controls need the launcher's exact identity.
            # Opening remains available for visible entries without window metadata.
            if (app_id.startswith('desktop_') and operation != 'open'
                    and not definition.get('wm_class')):
                continue
        if action_id.startswith("browser.search_"):
            app = action_id.removeprefix("browser.search_")
            if app == "youtube":
                if not ({"brave", "firefox"} & apps.keys()):
                    continue
            elif app not in apps:
                continue
        if action_id == "notes.search" and "notes" not in apps:
            continue
        if action_id == "mail.search" and not any(
            a.get("integration") == "proton_mail" for a in apps.values()
        ):
            continue
        allowed[action_id] = dict(details, **policy)
    return allowed

def dispatch_action(skill, action_id, message, *, source="personal"):
    """Return whether an approved handler was invoked; never execute model text."""
    if not isinstance(action_id, str) or source not in {"personal", "router"}:
        return False
    profile = skill._jarvis_profile
    catalog = router_catalog(profile) if source == "router" else action_catalog(profile)
    if action_id not in catalog:
        return False
    if action_id == "files.search":
        from .routing_model import file_search_request
        request = file_search_request(message.data.get('utterance'))
        if not request:
            return False
        from ovos_bus_client import Message
        skill.bus.emit(Message('jarvis.file.search', request))
        return True
    direct_handlers = {
        "system.mute_all_audio": "handle_mute_system_audio",
        "system.mute_microphone": "handle_mute_system_microphone",
        "system.mute_jarvis": "handle_mute_jarvis",
        "system.press_enter": "handle_press_enter",
        "system.insert_new_line": "handle_insert_new_line",
        "system.press_escape": "handle_press_escape",
        "system.caps_lock_on": "handle_caps_lock_on",
        "system.caps_lock_off": "handle_caps_lock_off",
        "media.play": "handle_play_media",
        "media.pause": "handle_pause_media",
        "media.stop": "handle_stop_media",
        "media.next": "handle_next_media",
        "media.previous": "handle_previous_media",
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
        getattr(skill, handler_name)(message)
        return True

    if action_id.startswith("application."):
        _prefix, operation, app_id = action_id.split(".", 2)
        if app_id not in skill._desktop_app_aliases:
            skill.log.warning("Unavailable application action was ignored")
            return False
        return skill._run_desktop_app_action(app_id, operation) is not False

    if action_id.startswith("browser."):
        browser_action = action_id.removeprefix("browser.")
        if browser_action == "search_brave":
            skill._prompt_browser_search(message, "brave")
        elif browser_action == "search_firefox":
            skill._prompt_browser_search(message, "firefox")
        elif browser_action == "search_youtube":
            skill._prompt_youtube_search(message)
        elif browser_action == "youtube_shorts":
            skill._open_youtube_shorts()
        elif browser_action == "address":
            skill._custom_address_prompt()
        else:
            skill._run_browser_action(browser_action)
        return True

    if action_id == "hermes.message":
        skill._message_hermes_desktop()
        return True

    if action_id.startswith("hermes."):
        skill._run_hermes_action(action_id.removeprefix("hermes."))
        return True

    if action_id.startswith("codex."):
        operation = action_id.removeprefix("codex.")
        if operation in {"open", "focus", "minimize", "close"}:
            skill._window_action(operation, "codex")
        elif operation == "message":
            skill._message_agent("codex")
        elif operation == "search":
            skill._search_codex()
        elif operation == "read":
            skill._read_agent_response("codex")
        return True

    if action_id.startswith("claude_agent."):
        operation = action_id.removeprefix("claude_agent.")
        if operation in {"open", "focus", "minimize", "close"}:
            skill._window_action(operation, "claude")
        elif operation == "message":
            skill._message_agent("claude")
        elif operation == "read":
            skill._read_agent_response("claude")
        elif operation == "new":
            skill._launch_claude_session_control("new")
        elif operation == "create_subagent":
            skill._create_claude_subagent()
        elif operation == "show_agents":
            skill._launch_claude_session_control("agents")
        elif operation == "resume":
            skill._window_action("open", "claude")
        return True

    if action_id == "claude_desktop.message":
        skill._message_claude_desktop()
        return True
    if action_id == "claude_desktop.new_chat":
        skill._open_claude_desktop_new_chat()
        return True
    if action_id == "response.read_latest":
        skill._read_agent_response()
        return True

    skill.log.error("Unsupported personal action reached dispatcher: %s", action_id)

    return False
