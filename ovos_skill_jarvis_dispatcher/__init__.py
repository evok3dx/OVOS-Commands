import re
import subprocess
import threading
from urllib.parse import quote_plus
from pathlib import Path

from ovos_bus_client import Message

from ovos_workshop.decorators import intent_handler
from ovos_workshop.intents import IntentBuilder
from ovos_workshop.skills.converse import ConversationalSkill

from .agents import AgentActionsMixin
from .browser import BrowserActionsMixin
from .conversation import ConversationMixin
from .desktop import DesktopActionsMixin
from .dictation import DictationActionsMixin
from .helpers import DispatcherHelpersMixin
from .vocabulary import register_skill_vocabulary
from .wakeword import WakewordActionsMixin


class JarvisDispatcherSkill(
    AgentActionsMixin,
    ConversationMixin,
    DispatcherHelpersMixin,
    WakewordActionsMixin,
    DictationActionsMixin,
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
        self._message_retries = 0
        self._confirmation_retries = 0

        self.add_event(
            "recognizer_loop:wakeword",
            self._pause_speech_note_reading
        )

        self.add_event(
            "recognizer_loop:wakeword",
            self._interrupt_speech_on_wakeword
        )

        register_skill_vocabulary(self)


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
            "What should I write?",
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
        IntentBuilder("BrowserNavigationIntent")
        .require("BrowserNavigationCommand")
    )
    def handle_browser_navigation(self, message):
        utterance = str(
            message.data.get("utterance", "")
        ).strip()



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
        utterance = str(
            message.data.get("utterance", "")
        ).strip()



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
    def handle_open_claude(self, _):
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
    def handle_focus_claude(self, _):
        self._window_action("focus", "claude")

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
    def handle_minimize_claude(self, _):
        self._window_action("minimize", "claude")

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
    def handle_close_claude(self, _):
        self._window_action("close", "claude")

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
    def handle_message_claude(self, _):
        self._message_agent("claude")


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
    def handle_write_claude(self, _):
        self._message_agent("claude")

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
    def handle_type_claude(self, _):
        self._message_agent("claude")

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
    def handle_speak_claude(self, _):
        self._message_agent("claude")

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
    def handle_talk_claude(self, _):
        self._message_agent("claude")




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
