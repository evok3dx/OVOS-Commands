import re
import subprocess
import threading
from urllib.parse import quote_plus
from pathlib import Path

from ovos_bus_client import Message

from ovos_workshop.decorators import intent_handler
from ovos_workshop.intents import IntentBuilder
from ovos_workshop.skills.converse import ConversationalSkill

from .browser import BrowserActionsMixin
from .desktop import DesktopActionsMixin
from .vocabulary import register_skill_vocabulary


class JarvisDispatcherSkill(
    DesktopActionsMixin,
    BrowserActionsMixin,
    ConversationalSkill,
):
    """Allowlisted control of isolated agent windows and messaging."""

    AGENT_NAMES = {
        "codex": "Codex agent",
        "claude": "Claude agent"
    }

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

    def _read_visible_text(self, mode: str) -> None:
        """Read selected text or the focused browser page."""

        helper = Path.home() / ".local/bin/jarvis-read-visible-text"

        if mode == "selection":
            introduction = "Reading the selected text."
            failure = "I could not find any selected text."
        else:
            introduction = "Reading the page."
            failure = "I could not read that page."

        self.speak(introduction, wait=True)

        try:
            subprocess.run(
                [str(helper), mode],
                check=True,
                timeout=12,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            self.log.exception(
                f"Visible text reading failed: {mode}"
            )
            self.speak(failure)

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

    def _speech_note_action(self, action: str) -> bool:
        """Invoke a supported action on the running Speech Note app."""

        try:
            subprocess.run(
                [
                    "/usr/bin/flatpak",
                    "run",
                    "net.mkiol.SpeechNote",
                    "--action",
                    action
                ],
                check=True,
                timeout=5,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except Exception:
            self.log.exception(
                f"Speech Note action failed: {action}"
            )
            return False

    def _pause_speech_note_reading(self, _message=None):
        """Pause reading or dictation when Jarvis wakes."""

        if self._speech_note_dictating:
            if self._speech_note_action("stop-listening"):
                self._speech_note_dictating = False
                self._speech_note_dictation_paused = True
            return

        if self._speech_note_dictation_paused:
            return

        self._speech_note_action("pause-resume-reading")

    def _start_speech_note_dictation(self):
        """Begin active-window dictation after spoken feedback finishes."""

        self.speak("Start speaking.", wait=True)

        if self._speech_note_action("start-listening-active-window"):
            self._speech_note_dictating = True
            self._speech_note_dictation_paused = False
        else:
            self.speak("I could not start dictation.")

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

    def _interrupt_speech_on_wakeword(self, _message):
        """Immediately silence current speech when Jarvis is invoked."""

        self.bus.emit(
            Message("mycroft.audio.speech.stop")
        )


    def can_stop(self, _message=None):
        """Report that this skill supports immediate cancellation."""

        return True


    def stop(self):
        """Stop OVOS speech, Speech Note reading and conversation."""

        self.bus.emit(
            Message("mycroft.audio.speech.stop")
        )
        self._speech_note_action("cancel")
        self._speech_note_dictating = False
        self._speech_note_dictation_paused = False

        try:
            self.deactivate()
        except Exception:
            self.log.exception(
                "Could not deactivate dispatcher"
            )

        return True


    @staticmethod
    def _confirmation_token(response) -> str:
        if not response:
            return ""

        token = str(response).lower().replace("'", "")
        token = re.sub(r"[^a-z0-9 ]+", " ", token)
        return " ".join(token.split())

    def _arm_message_timeout(self, seconds: int) -> None:
        """Start a genuine timeout for the current conversation stage."""

        with self._message_lock:
            if self._message_timer:
                self._message_timer.cancel()

            self._message_generation += 1
            generation = self._message_generation

            self._message_timer = threading.Timer(
                seconds,
                self._message_timeout,
                args=(generation,)
            )
            self._message_timer.daemon = True
            self._message_timer.start()

    def _message_timeout(self, generation: int) -> None:
        """Release conversational mode if the expected reply never arrives."""

        with self._message_lock:
            if generation != self._message_generation:
                return

            if not self._message_stage:
                return

            self._message_timer = None
            self._message_generation += 1
            self._message_stage = None
            self._pending_agent = None
            self._pending_message = None
            self._pending_window_id = None
            self._message_retries = 0
            self._confirmation_retries = 0

        self.deactivate()
        self.speak("Message cancelled.")

    def _clear_message_state(self) -> None:
        """Clear all temporary message data and leave converse mode."""

        with self._message_lock:
            if self._message_timer:
                self._message_timer.cancel()

            self._message_timer = None
            self._message_generation += 1
            self._message_stage = None
            self._pending_agent = None
            self._pending_message = None
            self._pending_window_id = None
            self._message_retries = 0
            self._confirmation_retries = 0

        self.deactivate()

    def _message_agent(self, agent: str) -> None:
        """Begin a non-blocking, time-limited messaging conversation."""

        display = self.AGENT_NAMES[agent]

        with self._message_lock:
            if self._message_stage:
                self.speak("Please finish or cancel the current message.")
                return

            self._message_stage = "message"
            self._pending_agent = agent
            self._pending_message = None
            self._pending_window_id = None
            self._message_retries = 1
            self._confirmation_retries = 1

        self.activate(duration_minutes=1)
        self.speak(
            f"What should I send to {display}?",
            expect_response=True,
            wait=True
        )
        self._arm_message_timeout(20)

    def _search_codex(self) -> None:
        """Collect and confirm a web-search request for Codex."""

        with self._message_lock:
            if self._message_stage:
                self.speak(
                    "Please finish or cancel the current message."
                )
                return

            self._message_stage = "search"
            self._pending_agent = "codex"
            self._pending_message = None
            self._pending_window_id = None
            self._message_retries = 1
            self._confirmation_retries = 1

        self.activate(duration_minutes=1)
        self.speak(
            "What should I search for?",
            expect_response=True,
            wait=True
        )
        self._arm_message_timeout(20)

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

    def _type_into_window(
        self,
        window_id,
        text,
        press_enter=False
    ):
        """Type confirmed text and optionally press Enter safely."""

        try:
            if not str(window_id).isdigit():
                raise RuntimeError("Invalid target window")

            class_result = subprocess.run(
                [
                    "/usr/bin/xprop",
                    "-id",
                    str(window_id),
                    "WM_CLASS"
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=5
            )
            window_class = class_result.stdout.lower()
            is_terminal = "terminal" in window_class

            subprocess.run(
                [
                    "/usr/bin/xdotool",
                    "windowactivate",
                    "--sync",
                    str(window_id)
                ],
                check=True,
                timeout=8
            )

            subprocess.run(
                [
                    "/usr/bin/xdotool",
                    "type",
                    "--clearmodifiers",
                    "--delay",
                    "15",
                    "--",
                    text
                ],
                check=True,
                timeout=30
            )

            self._last_typed_text = text

            if press_enter and is_terminal:
                self.speak(
                    "Written, but I will not press Enter in Terminal."
                )
                return

            if press_enter:
                subprocess.run(
                    [
                        "/usr/bin/xdotool",
                        "key",
                        "--clearmodifiers",
                        "Return"
                    ],
                    check=True,
                    timeout=5
                )
                self.speak("Written and Enter pressed.")
            else:
                self.speak("Written.")

        except Exception:
            self.log.exception("Focused text entry failed")
            self.speak("I could not write into that window.")


    def can_converse(self, message) -> bool:
        """Accept follow-up speech only during an active message flow."""

        with self._message_lock:
            return bool(self._message_stage)

    def converse(self, message):
        """Handle only the next expected message or confirmation."""

        utterances = message.data.get("utterances") or []
        utterance = str(utterances[0]).strip() if utterances else ""
        token = self._confirmation_token(utterance)

        accepted = {
            "confirm",
            "send it",
            "yes do it"
        }

        cancelled = {
            "cancel",
            "cancel it",
            "scratch that",
            "never mind",
            "nevermind",
            "wait",
            "stop"
        }

        send_payload = None
        browser_payload = None
        typing_payload = None

        with self._message_lock:
            stage = self._message_stage

            if not stage:
                return False

            if self._message_timer:
                self._message_timer.cancel()
                self._message_timer = None
                self._message_generation += 1

            if token in cancelled:
                self._clear_message_state()
                self.speak("Cancelled.")
                return True

            if stage == "dictation":
                if not re.search(r"[A-Za-z0-9]", utterance):
                    if self._message_retries > 0:
                        self._message_retries -= 1
                        self.speak(
                            "I did not hear the text. "
                            "Please say it again.",
                            expect_response=True,
                            wait=True
                        )
                        self._arm_message_timeout(20)
                    else:
                        self._clear_message_state()
                        self.speak("Cancelled.")
                    return True

                if len(utterance) > 2000:
                    self._clear_message_state()
                    self.speak("That text is too long.")
                    return True

                text_to_write = utterance.strip()

                spoken_punctuation = (
                    (r"\\s+(?:full stop|period)\\s*$", "."),
                    (r"\\s+question mark\\s*$", "?"),
                    (r"\\s+exclamation mark\\s*$", "!")
                )

                for pattern, replacement in spoken_punctuation:
                    text_to_write = re.sub(
                        pattern,
                        replacement,
                        text_to_write,
                        flags=re.IGNORECASE
                    )

                if not re.search(r"[.!?]$", text_to_write):
                    text_to_write += "."

                self._pending_message = text_to_write
                self._message_stage = "typing_confirmation"

                self.speak(
                    f"I heard: {text_to_write} "
                    "Say write it, send it, or cancel.",
                    expect_response=True,
                    wait=True
                )
                self._arm_message_timeout(20)
                return True

            if stage == "typing_confirmation":
                typing_accepted = {
                    "write it",
                    "type it",
                    "yes write it",
                    "confirm",
                    "yes do it"
                }

                typing_send = {
                    "send it",
                    "write and send it",
                    "write it and send it",
                    "type and send it",
                    "type it and send it",
                    "write it and press enter",
                    "type it and press enter"
                }

                typing_readback = {
                    "read it back",
                    "read it back to me",
                    "read that back",
                    "repeat it"
                }

                if token in typing_readback:
                    spoken_text = re.sub(
                        r"(?<=\d),(?=\d)",
                        "",
                        self._pending_message or ""
                    )
                    self.speak(
                        f"You said: {spoken_text}. "
                        "Say write it, send it, or cancel.",
                        expect_response=True,
                        wait=True
                    )
                    self._arm_message_timeout(20)
                    return True

                if token in typing_send:
                    typing_payload = (
                        self._pending_window_id,
                        self._pending_message,
                        True
                    )
                    self._clear_message_state()
                elif token in typing_accepted:
                    typing_payload = (
                        self._pending_window_id,
                        self._pending_message,
                        False
                    )
                    self._clear_message_state()
                elif self._confirmation_retries > 0:
                    self._confirmation_retries -= 1
                    self.speak(
                        "I did not hear you. "
                        "Say write it, send it, or cancel.",
                        expect_response=True,
                        wait=True
                    )
                    self._arm_message_timeout(15)
                    return True
                else:
                    self._clear_message_state()
                    self.speak("Cancelled.")
                    return True


            if stage in {
                "browser_address",
                "browser_search",
                "browser_search_firefox"
            }:
                if not re.search(r"[A-Za-z0-9]", utterance):
                    if self._message_retries > 0:
                        self._message_retries -= 1
                        self.speak(
                            "I did not hear that. Please say it again.",
                            expect_response=True,
                            wait=True
                        )
                        self._arm_message_timeout(20)
                    else:
                        self._clear_message_state()
                        self.speak("Cancelled.")
                    return True

                if len(utterance) > 500:
                    self._clear_message_state()
                    self.speak("That entry is too long.")
                    return True

                browser_payload = (stage, utterance)
                self._clear_message_state()

            if stage in {"message", "search"}:
                if not re.search(r"[A-Za-z0-9]", utterance):
                    if self._message_retries > 0:
                        self._message_retries -= 1
                        self.speak(
                            "I did not hear the message. Please say it again.",
                            expect_response=True,
                            wait=True
                        )
                        self._arm_message_timeout(20)
                    else:
                        self._clear_message_state()
                        self.speak("Cancelled.")
                    return True

                if len(utterance) > 8000:
                    self._clear_message_state()
                    self.speak("That message is too long.")
                    return True

                if stage == "search":
                    query = re.sub(
                        (
                            r"\b(?:alama|olama|ullama|ulama|llama)"
                            r"(?=\s+FAQ\b)"
                        ),
                        "Ollama",
                        utterance,
                        flags=re.IGNORECASE
                    )

                    self._pending_message = (
                        "Use live web search to research the "
                        "following request:\n\n"
                        f"{query}\n\n"
                        "Begin with exactly 'Spoken summary:' "
                        "on its own line, followed by no more "
                        "than three short plain-text sentences "
                        "suitable for speech. Do not include "
                        "URLs, source names, bullets, markdown, "
                        "or citations in the spoken summary. "
                        "Then add 'Sources:' on its own line "
                        "and list direct source links with brief "
                        "verification notes. Distinguish verified "
                        "facts from inference."
                    )

                    spoken_query = query

                    confirmation = (
                        f"I heard. Search for: "
                        f"{spoken_query}. "
                    )
                else:
                    self._pending_message = utterance
                    confirmation = (
                        f"I heard: {utterance}. "
                    )

                self._message_stage = "confirmation"

                self.speak(
                    confirmation
                    + "Say send it to confirm, or cancel.",
                    expect_response=True,
                    wait=True
                )
                self._arm_message_timeout(15)
                return True

            if stage == "confirmation":
                if token in accepted:
                    send_payload = (
                        self._pending_agent,
                        self._pending_message
                    )
                    self._clear_message_state()
                elif self._confirmation_retries > 0:
                    self._confirmation_retries -= 1
                    self.speak(
                        "I did not hear you. "
                        "Please say that again.",
                        expect_response=True,
                        wait=True
                    )
                    self._arm_message_timeout(15)
                    return True
                else:
                    self._clear_message_state()
                    self.speak("Cancelled.")
                    return True

        if typing_payload:
            window_id, text, press_enter = typing_payload
            self._type_into_window(
                window_id,
                text,
                press_enter
            )
            return True


        if browser_payload:
            stage, browser_text = browser_payload

            if stage == "browser_search":
                self._run_browser_action(
                    "search",
                    browser_text,
                    browser="brave"
                )
            elif stage == "browser_search_firefox":
                self._run_browser_action(
                    "search",
                    browser_text,
                    browser="firefox"
                )
            else:
                self._run_browser_action(
                    "navigate",
                    browser_text
                )

            return True

        if send_payload:
            agent, prompt = send_payload
            self._send_agent_message(agent, prompt)

        return True

    def _send_agent_message(self, agent: str, prompt: str) -> None:
        """Submit a confirmed message through the allowlisted helper."""

        display = self.AGENT_NAMES[agent]

        try:
            subprocess.run(
                [
                    "/usr/bin/sudo",
                    "-n",
                    "/usr/local/sbin/jarvis-agent-message",
                    agent
                ],
                input=prompt + "\n",
                text=True,
                capture_output=True,
                check=True,
                timeout=20
            )
        except Exception:
            self.log.exception("Agent message failed")
            self.speak(f"I could not message {display}.")
            return

        try:
            subprocess.run(
                [
                    str(Path.home() / ".local/bin/jarvis-agent-window"),
                    "open",
                    agent
                ],
                check=True,
                timeout=15,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            self.log.exception("Agent window display failed")

        self.speak(f"Sent to {display}.")






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

    def _read_agent_response(self, agent=None):
        sources = {
            "codex": Path(
                "/var/spool/jarvis-responses/codex/latest.json"
            ),
            "claude": Path(
                "/var/spool/jarvis-responses/claude/latest.json"
            )
        }

        readers = {
            "codex": (
                Path.home() /
                ".local/bin/jarvis-read-codex-response.py"
            ),
            "claude": (
                Path.home() /
                ".local/bin/jarvis-read-claude-response.py"
            )
        }

        if agent is None:
            available = [
                name for name, source in sources.items()
                if source.is_file()
            ]

            if not available:
                self.speak("There is no response to read.")
                return

            agent = max(
                available,
                key=lambda name: sources[name].stat().st_mtime
            )

        if not sources[agent].is_file():
            self.speak(
                f"There is no {self.AGENT_NAMES[agent]} "
                "response to read."
            )
            return

        try:
            subprocess.run(
                [str(readers[agent])],
                check=True,
                timeout=20
            )
        except Exception:
            self.log.exception("Agent response reader failed")
            self.speak(
                f"I could not read the "
                f"{self.AGENT_NAMES[agent]} response."
            )

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
