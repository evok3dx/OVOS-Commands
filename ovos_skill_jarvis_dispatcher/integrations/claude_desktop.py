import re


class ClaudeDesktopIntegrationMixin:
    """Route ordinary Claude requests to the verified desktop application."""

    @staticmethod
    def _explicit_claude_agent(message):
        utterance = str(message.data.get("utterance", "")).lower()
        return bool(re.search(r"\bagent\b", utterance))

    @staticmethod
    def _is_claude_desktop_window(window_class):
        value = str(window_class or "").lower()
        return "com.anthropic.claude" in value

    def _route_claude_window_action(self, message, action):
        if self._explicit_claude_agent(message):
            self._window_action(action, "claude")
            return

        self._run_desktop_app_action("claude", action)

    def _route_claude_message(self, message):
        if self._explicit_claude_agent(message):
            self._message_agent("claude")
            return

        self._message_claude_desktop()

    def _message_claude_desktop(self):
        """Focus Claude Desktop and begin its guarded message flow."""

        with self._message_lock:
            if self._message_stage:
                self.speak("Please finish or cancel the current message.")
                return

        if not self._run_desktop_app_action("claude", "focus", announce=False):
            self.speak("I could not open Claude Desktop.")
            return

        try:
            window_id, window_class = self._focused_window_details()
        except Exception:
            self.log.exception("Could not identify the Claude Desktop window")
            self.speak("I could not verify Claude Desktop.")
            return

        if not self._is_claude_desktop_window(window_class):
            self.speak("Claude Desktop did not receive focus, so I cancelled.")
            return

        with self._message_lock:
            self._message_stage = "message"
            self._pending_agent = "claude_desktop"
            self._pending_message = None
            self._pending_window_id = window_id
            self._message_retries = 1
            self._confirmation_retries = 1

        self.activate(duration_minutes=1)
        self.speak(
            "What should I send to Claude Desktop?",
            expect_response=True,
            wait=True,
        )
        self._arm_message_timeout(20)

    def _send_claude_desktop_message(self, prompt, window_id):
        try:
            current_window, current_class = self._focused_window_details()
            if current_window != str(window_id):
                self.speak("The focused window changed, so I cancelled.")
                return
            if not self._is_claude_desktop_window(current_class):
                self.speak("Claude Desktop is not focused, so I cancelled.")
                return

            self._type_into_window(window_id, prompt, press_enter=True)
        except Exception:
            self.log.exception("Claude Desktop message failed")
            self.speak("I could not message Claude Desktop.")
