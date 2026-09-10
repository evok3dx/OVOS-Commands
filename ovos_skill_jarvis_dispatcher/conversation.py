import re
import threading


class ConversationMixin:
    """Non-blocking, time-limited multi-turn command state."""

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

    def can_converse(self, message) -> bool:
        """Accept follow-up speech only during an active message flow."""

        with self._message_lock:
            return bool(self._message_stage)

    def converse(self, message):
        """Handle a follow-up without allowing a failure to trap the skill."""

        try:
            return self._converse_impl(message)
        except Exception:
            self.log.exception("Dispatcher conversation failed")

            try:
                self._clear_message_state()
            except Exception:
                self.log.exception(
                    "Could not clear failed dispatcher conversation"
                )

            self.speak("That command failed, but Jarvis is still available.")
            return True

    def _converse_impl(self, message):
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
