import re
import subprocess
import threading

from ovos_workshop.decorators import intent_handler
from ovos_workshop.intents import IntentBuilder
from ovos_workshop.skills.converse import ConversationalSkill

from .agents import AgentActionsMixin
from .browser import BrowserActionsMixin
from .conversation import ConversationMixin
from .custom_commands import CustomCommandsMixin
from .desktop import DesktopActionsMixin
from .dictation import DictationActionsMixin
from .helpers import DispatcherHelpersMixin
from .profile import load_profile
from .system_audio import SystemAudioActionsMixin
from .system_controls import SystemControlsMixin
from .text_editing import TextEditingActionsMixin
from .vocabulary import register_skill_vocabulary
from .wakeword import WakewordActionsMixin

try:
    from .integrations.claude_desktop import ClaudeDesktopIntegrationMixin
except Exception as error:
    _claude_desktop_import_error = str(error)

    class ClaudeDesktopIntegrationMixin:
        """Fail-safe replacement for an unavailable optional integration."""

        def _route_claude_window_action(self, _message, _action):
            self.log.error(
                f"Claude Desktop integration unavailable: "
                f"{_claude_desktop_import_error}"
            )
            self.speak("Claude control is unavailable.")

        def _route_claude_message(self, _message):
            self._message_claude_desktop()

        def _message_claude_desktop(self):
            self.log.error(
                f"Claude Desktop integration unavailable: "
                f"{_claude_desktop_import_error}"
            )
            self.speak("Claude messaging is unavailable.")

        def _open_claude_desktop_new_chat(self):
            self.log.error(
                f"Claude Desktop integration unavailable: "
                f"{_claude_desktop_import_error}"
            )
            self.speak("Claude control is unavailable.")
            return None

try:
    from .integrations.hermes_desktop import HermesDesktopIntegrationMixin
except Exception as error:
    _hermes_desktop_import_error = str(error)

    class HermesDesktopIntegrationMixin:
        """Fail-safe replacement for an unavailable optional integration."""

        def _run_hermes_action(self, _action):
            self.log.error(
                f"Hermes integration unavailable: "
                f"{_hermes_desktop_import_error}"
            )
            self.speak("Hermes control is unavailable.")

        def _message_hermes_desktop(self):
            self.log.error(
                f"Hermes integration unavailable: "
                f"{_hermes_desktop_import_error}"
            )
            self.speak("Hermes messaging is unavailable.")

try:
    from .integrations.zoom import ZoomIntegrationMixin
except Exception as error:
    _zoom_import_error = str(error)

    class ZoomIntegrationMixin:
        """Fail-safe replacement for an unavailable optional integration."""

        def _join_zoom_meeting(self):
            self.log.error(
                f"Zoom integration unavailable: {_zoom_import_error}"
            )
            self.speak("The Zoom meeting action is unavailable.")

try:
    from .integrations.proton_mail import ProtonMailIntegrationMixin
except Exception as error:
    _proton_mail_import_error = str(error)

    class ProtonMailIntegrationMixin:
        """Fail-safe replacement for an unavailable optional integration."""

        def _create_new_email(self):
            self.log.error(
                f"Proton Mail integration unavailable: {_proton_mail_import_error}"
            )
            self.speak("The new-email action is unavailable.")

        def _search_proton_mail(self):
            self.log.error(
                f"Proton Mail integration unavailable: {_proton_mail_import_error}"
            )
            self.speak("Mail search is unavailable.")

try:
    from .integrations.standard_notes import StandardNotesIntegrationMixin
except Exception as error:
    _standard_notes_import_error = str(error)

    class StandardNotesIntegrationMixin:
        """Fail-safe replacement for an unavailable optional integration."""

        def _create_new_note(self):
            self.log.error(
                f"Standard Notes integration unavailable: "
                f"{_standard_notes_import_error}"
            )
            self.speak("The new-note action is unavailable.")

        def _search_standard_notes(self):
            self.log.error(
                f"Standard Notes integration unavailable: "
                f"{_standard_notes_import_error}"
            )
            self.speak("Notes search is unavailable.")


class JarvisDispatcherSkill(
    AgentActionsMixin,
    ConversationMixin,
    CustomCommandsMixin,
    DispatcherHelpersMixin,
    WakewordActionsMixin,
    DictationActionsMixin,
    SystemAudioActionsMixin,
    SystemControlsMixin,
    TextEditingActionsMixin,
    ClaudeDesktopIntegrationMixin,
    HermesDesktopIntegrationMixin,
    ZoomIntegrationMixin,
    ProtonMailIntegrationMixin,
    StandardNotesIntegrationMixin,
    DesktopActionsMixin,
    BrowserActionsMixin,
    ConversationalSkill,
):
    """Allowlisted control of isolated agent windows and messaging."""

    def initialize(self):
        """Register vocabulary and initialise non-blocking message state."""

        self._message_lock = threading.RLock()
        self._message_timer = None
        self._message_generation = 0
        self._message_stage = None
        self._pending_agent = None
        self._pending_message = None
        self._pending_window_id = None
        self._last_typed_text = None
        self._speech_note_dictating = False
        self._speech_note_dictation_paused = False
        self._speech_note_reading = False
        self._reader_listener_muted = False
        self._reader_monitor_generation = 0
        self._reader_monitor_lock = threading.RLock()
        self._message_retries = 0
        self._confirmation_retries = 0
        self._jarvis_profile = load_profile(logger=self.log)

        self.add_event(
            "recognizer_loop:wakeword",
            self._pause_speech_note_reading
        )
        # Keyboard/listen-button activation does not emit the wake-word event.
        # record_begin is the common boundary for both wake-word and manually
        # requested listening, so reader interruption behaves the same either
        # way.  The handler is idempotent when both events are emitted.
        self.add_event(
            "recognizer_loop:record_begin",
            self._pause_speech_note_reading
        )

        register_skill_vocabulary(self)

        from .routing_runtime import RouterRuntime
        self._qwen_router = RouterRuntime(self)
        from . import launcher  # Verify the launch backend is importable at startup.
        self.log.info("Jarvis configuration ready")

    def shutdown(self):
        router = getattr(self, "_qwen_router", None)
        if router is not None:
            router.close()
        return super().shutdown()

    @intent_handler(
        IntentBuilder("CustomCommandIntent").require("CustomCommandPhrase")
    )
    def handle_custom_command(self, message):
        self._run_custom_command(message)

    @intent_handler(
        IntentBuilder("MuteSystemMicrophoneIntent")
        .require("MuteSystemMicrophoneCommand")
    )
    def handle_mute_system_microphone(self, _message):
        self._mute_system_microphone()

    @intent_handler(
        IntentBuilder("MuteSystemAudioIntent")
        .require("MuteSystemAudioCommand")
    )
    def handle_mute_system_audio(self, _message):
        self._mute_all_system_audio()

    @intent_handler(
        IntentBuilder("MuteJarvisIntent")
        .require("MuteJarvisCommand")
    )
    def handle_mute_jarvis(self, _message):
        self._mute_jarvis_listener()

    @intent_handler(
        IntentBuilder("PressEnterIntent").require("PressEnterCommand")
    )
    def handle_press_enter(self, _message):
        self._press_enter()

    @intent_handler(
        IntentBuilder("InsertNewLineIntent").require("InsertNewLineCommand")
    )
    def handle_insert_new_line(self, _message):
        self._insert_new_line()

    @intent_handler(
        IntentBuilder("PressEscapeIntent").require("PressEscapeCommand")
    )
    def handle_press_escape(self, _message):
        self._press_escape()

    @intent_handler(
        IntentBuilder("PlayMediaIntent").require("PlayMediaCommand")
    )
    def handle_play_media(self, _message):
        self._run_media_action("play")

    @intent_handler(
        IntentBuilder("PauseMediaIntent").require("PauseMediaCommand")
    )
    def handle_pause_media(self, _message):
        self._run_media_action("pause")

    @intent_handler(
        IntentBuilder("StopMediaIntent").require("StopMediaCommand")
    )
    def handle_stop_media(self, _message):
        self._run_media_action("stop")

    @intent_handler(
        IntentBuilder("NextMediaIntent").require("NextMediaCommand")
    )
    def handle_next_media(self, _message):
        self._run_media_action("next")

    @intent_handler(
        IntentBuilder("PreviousMediaIntent").require("PreviousMediaCommand")
    )
    def handle_previous_media(self, _message):
        self._run_media_action("previous")

    @intent_handler(
        IntentBuilder("CapsLockOnIntent").require("CapsLockOnCommand")
    )
    def handle_caps_lock_on(self, _message):
        self._set_caps_lock(True)

    @intent_handler(
        IntentBuilder("CapsLockOffIntent").require("CapsLockOffCommand")
    )
    def handle_caps_lock_off(self, _message):
        self._set_caps_lock(False)

    @intent_handler(
        IntentBuilder("HermesComposerIntent")
        .require("HermesComposerCommand")
    )
    def handle_hermes_composer(self, message):
        phrase = next(
            (
                value for key, value in message.data.items()
                if key.endswith("HermesComposerCommand")
            ),
            "",
        )
        action = self._hermes_composer_actions.get(
            " ".join(str(phrase).lower().split()).strip(" .")
        )
        if not action:
            self.speak("I did not recognise that Hermes command.")
            return
        self._run_hermes_action(action)


    @intent_handler(
        IntentBuilder("CloseFocusedWindowIntent")
        .require("CloseFocusedWindowCommand")
    )
    def handle_close_focused_window(self, _message):
        self._focused_window_action("close")

    @intent_handler(
        IntentBuilder("MinimizeFocusedWindowIntent")
        .require("MinimizeFocusedWindowCommand")
    )
    def handle_minimize_focused_window(self, _message):
        self._focused_window_action("minimize")

    @intent_handler(
        IntentBuilder("MaximizeFocusedWindowIntent")
        .require("MaximizeFocusedWindowCommand")
    )
    def handle_maximize_focused_window(self, _message):
        self._focused_window_action("maximize")

    @intent_handler(
        IntentBuilder("RestoreFocusedWindowIntent")
        .require("RestoreFocusedWindowCommand")
    )
    def handle_restore_focused_window(self, _message):
        self._focused_window_action("restore")

    @intent_handler(
        IntentBuilder("ReadLastTypedTextIntent")
        .require("ReadLastTypedTextCommand")
    )
    def handle_read_last_typed_text(self, _message):
        """Read the last short text captured by the writing flow."""

        with self._message_lock:
            if (
                self._message_stage == "typing_confirmation"
                and self._pending_message
            ):
                text = self._pending_message
            else:
                text = self._last_typed_text

        if not text:
            self.speak("There is no recent written text to read.")
            return

        spoken_text = re.sub(
            r"(?<=\d),(?=\d)",
            "",
            text
        )
        self.speak(f"You wrote: {spoken_text}")


    @intent_handler(
        IntentBuilder("ReadSelectedTextIntent")
        .require("ReadSelectedTextCommand")
    )
    def handle_read_selected_text(self, _message):
        self._read_visible_text("selection")

    @intent_handler(
        IntentBuilder("ReadVisiblePageIntent")
        .require("ReadVisiblePageCommand")
    )
    def handle_read_visible_page(self, _message):
        self._read_visible_text("page")

    @intent_handler(
        IntentBuilder("ReadSelectedTextDoubleSpeedIntent")
        .require("ReadSelectedTextDoubleSpeedCommand")
    )
    def handle_read_selected_text_double_speed(self, _message):
        self._read_visible_text("selection", speed=2)

    @intent_handler(
        IntentBuilder("ReadVisiblePageDoubleSpeedIntent")
        .require("ReadVisiblePageDoubleSpeedCommand")
    )
    def handle_read_visible_page_double_speed(self, _message):
        self._read_visible_text("page", speed=2)

    @intent_handler(IntentBuilder("SelectAllTextIntent").require("SelectAllTextCommand"))
    def handle_select_all_text(self, _message):
        self._select_all_text()

    @intent_handler(IntentBuilder("DeleteSelectedTextIntent").require("DeleteSelectedTextCommand"))
    def handle_delete_selected_text(self, _message):
        self._delete_selected_text()

    @intent_handler(IntentBuilder("ClearFocusedTextIntent").require("ClearFocusedTextCommand"))
    def handle_clear_focused_text(self, _message):
        self._clear_focused_text()

    @intent_handler(IntentBuilder("UndoTextEditIntent").require("UndoTextEditCommand"))
    def handle_undo_text_edit(self, _message):
        self._undo_text_edit()

    @intent_handler(IntentBuilder("RedoTextEditIntent").require("RedoTextEditCommand"))
    def handle_redo_text_edit(self, _message):
        self._redo_text_edit()

    @intent_handler(IntentBuilder("CopySelectedTextIntent").require("CopySelectedTextCommand"))
    def handle_copy_selected_text(self, _message):
        self._copy_selected_text()

    @intent_handler(IntentBuilder("CutSelectedTextIntent").require("CutSelectedTextCommand"))
    def handle_cut_selected_text(self, _message):
        self._cut_selected_text()

    @intent_handler(IntentBuilder("PasteTextIntent").require("PasteTextCommand"))
    def handle_paste_text(self, _message):
        self._paste_text()

    @intent_handler(IntentBuilder("SaveDocumentIntent").require("SaveDocumentCommand"))
    def handle_save_document(self, _message):
        self._save_document()

    @intent_handler(IntentBuilder("PressTabIntent").require("PressTabCommand"))
    def handle_press_tab(self, _message):
        self._press_tab()

    @intent_handler(
        IntentBuilder("PressShiftTabIntent")
        .require("PressShiftTabCommand")
    )
    def handle_press_shift_tab(self, _message):
        self._press_shift_tab()

    @intent_handler(
        IntentBuilder("SearchFocusedContentIntent")
        .require("SearchFocusedContentCommand")
    )
    def handle_search_focused_content(self, _message):
        self._search_focused_content()

    @intent_handler(
        IntentBuilder("StartSpeechNoteDictationIntent")
        .require("StartSpeechNoteDictationCommand")
    )
    def handle_start_speech_note_dictation(self, _message):
        self._start_speech_note_dictation()

    @intent_handler(
        IntentBuilder("PauseSpeechNoteDictationIntent")
        .require("PauseSpeechNoteDictationCommand")
    )
    def handle_pause_speech_note_dictation(self, _message):
        if self._speech_note_dictating:
            self._speech_note_action("stop-listening")

        if (
            self._speech_note_dictating
            or self._speech_note_dictation_paused
        ):
            self._speech_note_dictating = False
            self._speech_note_dictation_paused = True
            self.speak("Dictation paused.")
        else:
            self.speak("Dictation is not running.")

    @intent_handler(
        IntentBuilder("ResumeSpeechNoteDictationIntent")
        .require("ResumeSpeechNoteDictationCommand")
    )
    def handle_resume_speech_note_dictation(self, _message):
        self.speak("Continue speaking.", wait=True)

        if self._speech_note_action("start-listening-active-window"):
            self._speech_note_dictating = True
            self._speech_note_dictation_paused = False
        else:
            self.speak("I could not resume dictation.")

    @intent_handler(
        IntentBuilder("StopSpeechNoteDictationIntent")
        .require("StopSpeechNoteDictationCommand")
    )
    def handle_stop_speech_note_dictation(self, _message):
        if self._speech_note_dictating:
            self._speech_note_action("stop-listening")

        self._speech_note_dictating = False
        self._speech_note_dictation_paused = False
        self.speak("Dictation stopped.")

    @intent_handler(
        IntentBuilder("WriteFocusedTextIntent")
        .require("WriteFocusedTextCommand")
    )
    def handle_write_focused_text(self, _):
        """Collect text and type it into the currently focused window."""

        with self._message_lock:
            if self._message_stage:
                self.speak(
                    "Please finish or cancel the current request."
                )
                return

        try:
            result = subprocess.run(
                ["/usr/bin/xdotool", "getactivewindow"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            window_id = result.stdout.strip()

            if not window_id.isdigit():
                raise RuntimeError("No valid focused window")
        except Exception:
            self.log.exception("Could not identify focused window")
            self.speak("I could not identify the current window.")
            return

        with self._message_lock:
            self._message_stage = "dictation"
            self._pending_message = None
            self._pending_window_id = window_id
            self._message_retries = 1
            self._confirmation_retries = 1

        self.activate(duration_minutes=1)
        self.speak(
            "Ready.",
            expect_response=True,
            wait=True
        )
        self._arm_message_timeout(20)

    @intent_handler(
        IntentBuilder("BraveSearchPromptIntent")
        .require("BraveSearchPromptCommand")
    )
    def handle_brave_search_prompt(self, message):
        self._prompt_browser_search(
            message,
            "brave"
        )

    @intent_handler(
        IntentBuilder("FirefoxSearchPromptIntent")
        .require("FirefoxSearchPromptCommand")
    )
    def handle_firefox_search_prompt(self, message):
        self._prompt_browser_search(
            message,
            "firefox"
        )

    @intent_handler(
        IntentBuilder("YouTubeSearchPromptIntent")
        .require("YouTubeSearchPromptCommand")
    )
    def handle_youtube_search_prompt(self, message):
        self._prompt_youtube_search(message)

    @intent_handler(
        IntentBuilder("YouTubeShortsIntent")
        .require("YouTubeShortsCommand")
    )
    def handle_youtube_shorts(self, _message):
        self._open_youtube_shorts()

    @intent_handler(
        IntentBuilder("BrowserNavigationIntent")
        .require("BrowserNavigationCommand")
    )
    def handle_browser_navigation(self, message):
        phrase = next(
            (
                value
                for key, value in message.data.items()
                if key.endswith("BrowserNavigationCommand")
            ),
            ""
        )

        phrase = re.sub(
            r"\s+",
            " ",
            str(phrase).lower()
        ).strip(" .")

        action = self._browser_navigation_actions.get(phrase)

        if not action:
            self.speak("I did not recognise that browser command.")
            return

        if action == "address":
            self._run_browser_action("address")

            with self._message_lock:
                self._clear_message_state()
                self._message_stage = "browser_address"
                self._message_retries = 1

            self.activate(duration_minutes=1)

            self.speak(
                "What should I enter?",
                expect_response=True,
                wait=True
            )
            self._arm_message_timeout(20)
            return

        self._run_browser_action(action)

    @intent_handler(
        IntentBuilder("OpenDesktopAppIntent")
        .require("OpenDesktopAppCommand")
    )
    def handle_open_desktop_app(self, message):
        self._desktop_app_action(message, "open")

    @intent_handler(
        IntentBuilder("FocusDesktopAppIntent")
        .require("FocusDesktopAppCommand")
    )
    def handle_focus_desktop_app(self, message):
        self._desktop_app_action(message, "focus")

    @intent_handler(
        IntentBuilder("MinimizeDesktopAppIntent")
        .require("MinimizeDesktopAppCommand")
    )
    def handle_minimize_desktop_app(self, message):
        self._desktop_app_action(message, "minimize")

    @intent_handler(
        IntentBuilder("CloseDesktopAppIntent")
        .require("CloseDesktopAppCommand")
    )
    def handle_close_desktop_app(self, message):
        self._desktop_app_action(message, "close")

    @intent_handler(
        IntentBuilder("MaximizeDesktopAppIntent")
        .require("MaximizeDesktopAppCommand")
    )
    def handle_maximize_desktop_app(self, message):
        self._desktop_app_action(message, "maximize")

    @intent_handler(
        IntentBuilder("OpenChatGPTWebsiteIntent")
        .require("OpenChatGPTWebsiteCommand")
    )
    def handle_open_chatgpt_website(self, _message):
        self._open_fixed_website("ChatGPT", "https://chatgpt.com/")

    @intent_handler(
        IntentBuilder("OpenClaudeWebsiteIntent")
        .require("OpenClaudeWebsiteCommand")
    )
    def handle_open_claude_website(self, _message):
        self._open_fixed_website("Claude", "https://claude.ai/")

    @intent_handler(
        IntentBuilder("NewNoteIntent")
        .require("NewNoteCommand")
    )
    def handle_new_note(self, _message):
        self._create_new_note()

    @intent_handler(
        IntentBuilder("SearchNotesIntent")
        .require("SearchNotesCommand")
    )
    def handle_search_notes(self, _message):
        self._search_standard_notes()

    @intent_handler(
        IntentBuilder("NewEmailIntent")
        .require("NewEmailCommand")
    )
    def handle_new_email(self, _message):
        self._create_new_email()

    @intent_handler(
        IntentBuilder("SearchMailIntent")
        .require("SearchMailCommand")
    )
    def handle_search_mail(self, _message):
        self._search_proton_mail()

    @intent_handler(
        IntentBuilder("JoinZoomMeetingIntent")
        .require("JoinZoomMeetingCommand")
    )
    def handle_join_zoom_meeting(self, _message):
        self._join_zoom_meeting()

    @intent_handler(
        IntentBuilder("OpenCodexCommandIntent")
        .require("OpenCodexCommand")
    )
    def handle_open_codex_command(self, _):
        self._window_action("open", "codex")

    @intent_handler(
        IntentBuilder("FocusCodexCommandIntent")
        .require("FocusCodexCommand")
    )
    def handle_focus_codex_command(self, _):
        self._window_action("focus", "codex")

    @intent_handler(
        IntentBuilder("OpenCodexIntent")
        .require("OpenKeyword")
        .require("CodexKeyword")
    )
    def handle_open_codex(self, _):
        self._window_action("open", "codex")

    @intent_handler(
        IntentBuilder("OpenClaudeIntent")
        .require("OpenKeyword")
        .require("ClaudeKeyword")
    )
    def handle_open_claude(self, message):
        utterance = str(message.data.get("utterance", "")).lower()
        if "website" in utterance or "online" in utterance:
            self._open_fixed_website("Claude", "https://claude.ai/")
            return
        self._route_claude_window_action(message, "open")

    @intent_handler(
        IntentBuilder("NewClaudeChatIntent")
        .require("NewClaudeChatCommand")
    )
    def handle_new_claude_chat(self, _message):
        self._open_claude_desktop_new_chat()

    @intent_handler(
        IntentBuilder("NewClaudeAgentIntent")
        .require("NewClaudeAgentCommand")
    )
    def handle_new_claude_agent(self, _message):
        self._launch_claude_session_control("new")

    @intent_handler(
        IntentBuilder("CreateClaudeSubagentIntent")
        .require("CreateClaudeSubagentCommand")
    )
    def handle_create_claude_subagent(self, _message):
        self._create_claude_subagent()

    @intent_handler(
        IntentBuilder("ShowClaudeAgentsIntent")
        .require("ShowClaudeAgentsCommand")
    )
    def handle_show_claude_agents(self, _message):
        self._launch_claude_session_control("agents")

    @intent_handler(
        IntentBuilder("ResumeClaudeAgentIntent")
        .require("ResumeClaudeAgentCommand")
    )
    def handle_resume_claude_agent(self, _message):
        self._window_action("open", "claude")

    @intent_handler(
        IntentBuilder("FocusCodexIntent")
        .require("FocusKeyword")
        .require("CodexKeyword")
    )
    def handle_focus_codex(self, _):
        self._window_action("focus", "codex")

    @intent_handler(
        IntentBuilder("FocusClaudeIntent")
        .require("FocusKeyword")
        .require("ClaudeKeyword")
    )
    def handle_focus_claude(self, message):
        self._route_claude_window_action(message, "focus")

    @intent_handler(
        IntentBuilder("MinimizeCodexIntent")
        .require("MinimizeKeyword")
        .require("CodexKeyword")
    )
    def handle_minimize_codex(self, _):
        self._window_action("minimize", "codex")

    @intent_handler(
        IntentBuilder("MinimizeClaudeIntent")
        .require("MinimizeKeyword")
        .require("ClaudeKeyword")
    )
    def handle_minimize_claude(self, message):
        self._route_claude_window_action(message, "minimize")

    @intent_handler(
        IntentBuilder("CloseCodexWindowIntent")
        .require("CloseKeyword")
        .require("CodexKeyword")
    )
    def handle_close_codex(self, _):
        self._window_action("close", "codex")

    @intent_handler(
        IntentBuilder("CloseClaudeWindowIntent")
        .require("CloseKeyword")
        .require("ClaudeKeyword")
    )
    def handle_close_claude(self, message):
        self._route_claude_window_action(message, "close")

    @intent_handler(
        IntentBuilder("MessageCodexIntent")
        .require("MessageKeyword")
        .require("CodexKeyword")
    )
    def handle_message_codex(self, _):
        self._message_agent("codex")

    @intent_handler(
        IntentBuilder("MessageClaudeIntent")
        .require("MessageKeyword")
        .require("ClaudeKeyword")
    )
    def handle_message_claude(self, message):
        self._route_claude_message(message)

    @intent_handler(
        IntentBuilder("WriteCodexIntent")
        .require("WriteKeyword")
        .require("CodexKeyword")
    )
    def handle_write_codex(self, _):
        self._message_agent("codex")

    @intent_handler(
        IntentBuilder("WriteClaudeIntent")
        .require("WriteKeyword")
        .require("ClaudeKeyword")
    )
    def handle_write_claude(self, message):
        self._route_claude_message(message)

    @intent_handler(
        IntentBuilder("TypeCodexIntent")
        .require("TypeKeyword")
        .require("CodexKeyword")
    )
    def handle_type_codex(self, _):
        self._message_agent("codex")

    @intent_handler(
        IntentBuilder("TypeClaudeIntent")
        .require("TypeKeyword")
        .require("ClaudeKeyword")
    )
    def handle_type_claude(self, message):
        self._route_claude_message(message)

    @intent_handler(
        IntentBuilder("SpeakCodexIntent")
        .require("SpeakKeyword")
        .require("CodexKeyword")
    )
    def handle_speak_codex(self, _):
        self._message_agent("codex")

    @intent_handler(
        IntentBuilder("SpeakClaudeIntent")
        .require("SpeakKeyword")
        .require("ClaudeKeyword")
    )
    def handle_speak_claude(self, message):
        self._route_claude_message(message)

    @intent_handler(
        IntentBuilder("TalkCodexIntent")
        .require("TalkKeyword")
        .require("CodexKeyword")
    )
    def handle_talk_codex(self, _):
        self._message_agent("codex")

    @intent_handler(
        IntentBuilder("TalkClaudeIntent")
        .require("TalkKeyword")
        .require("ClaudeKeyword")
    )
    def handle_talk_claude(self, message):
        self._route_claude_message(message)

    @intent_handler(
        IntentBuilder("MessageHermesIntent")
        .require("MessageKeyword")
        .require("HermesKeyword")
    )
    def handle_message_hermes(self, _message):
        self._message_hermes_desktop()

    @intent_handler(
        IntentBuilder("WriteHermesIntent")
        .require("WriteKeyword")
        .require("HermesKeyword")
    )
    def handle_write_hermes(self, _message):
        self._message_hermes_desktop()

    @intent_handler(
        IntentBuilder("TypeHermesIntent")
        .require("TypeKeyword")
        .require("HermesKeyword")
    )
    def handle_type_hermes(self, _message):
        self._message_hermes_desktop()

    @intent_handler(
        IntentBuilder("SpeakHermesIntent")
        .require("SpeakKeyword")
        .require("HermesKeyword")
    )
    def handle_speak_hermes(self, _message):
        self._message_hermes_desktop()

    @intent_handler(
        IntentBuilder("TalkHermesIntent")
        .require("TalkKeyword")
        .require("HermesKeyword")
    )
    def handle_talk_hermes(self, _message):
        self._message_hermes_desktop()

    @intent_handler(
        IntentBuilder("SearchCodexIntent")
        .require("SearchCodexCommand")
    )
    def handle_search_codex(self, _):
        self._search_codex()

    @intent_handler(
        IntentBuilder("ReadCodexResponseIntent")
        .require("ReadCodexResponseCommand")
    )
    def handle_read_codex_response(self, _):
        self._read_agent_response("codex")

    @intent_handler(
        IntentBuilder("ReadClaudeResponseIntent")
        .require("ReadClaudeResponseCommand")
    )
    def handle_read_claude_response(self, _):
        self._read_agent_response("claude")

    @intent_handler(
        IntentBuilder("ReadLatestResponseIntent")
        .require("ReadLatestResponseCommand")
    )
    def handle_read_latest_response(self, _):
        self._read_agent_response()

    @intent_handler(
        IntentBuilder("OpenClaudeAliasIntent")
        .require("OpenClaudeCommand")
    )
    def handle_open_claude_alias(self, _):
        self._window_action("open", "claude")

    @intent_handler(
        IntentBuilder("NaturalDateIntent")
        .require("NaturalDateCommand")
    )
    def handle_natural_date(self, message):
        self.bus.emit(
            message.forward(
                "recognizer_loop:utterance",
                {
                    "utterances": ["what's the date"],
                    "lang": "en-US"
                }
            )
        )


def create_skill():
    return JarvisDispatcherSkill()
