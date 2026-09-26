import re
import subprocess
import time


class ClaudeDesktopIntegrationMixin:
    """Route ordinary Claude requests to the verified desktop application."""

    @staticmethod
    def _is_claude_desktop_window(window_class):
        value = str(window_class or "").lower()
        return "com.anthropic.claude" in value

    def _route_claude_window_action(self, message, action):
        self._run_desktop_app_action("claude", action)

    def _route_claude_message(self, message):
        data = getattr(message, "data", {}) or {}
        utterances = data.get("utterances") or []
        phrase = str(data.get("utterance") or (utterances[0] if utterances else ""))
        if re.search(r"\b(?:claude|cloud|clawed|called)\s+agent\b", phrase, re.I):
            if not (getattr(self, "_jarvis_profile", {})
                    .get("private_extensions", {}).get("agents") is True):
                self.speak("Claude agent is not enabled on this computer.")
                return
            self._message_agent("claude")
        else:
            self._message_claude_desktop()

    def _open_claude_desktop_new_chat(self):
        """Open and verify a clean Claude Desktop chat."""

        try:
            subprocess.run(
                [
                    "/usr/bin/xdg-open",
                    "claude://claude.ai/new",
                ],
                check=True,
                timeout=10,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            self.log.exception("Could not open a new Claude chat")
            self.speak("I could not open Claude.")
            return None

        window_id = None
        window_class = None
        for _ in range(40):
            try:
                time.sleep(0.1)
                window_id, window_class = self._focused_window_details()
            except Exception:
                continue
            if self._is_claude_desktop_window(window_class):
                break

        if not window_id or not self._is_claude_desktop_window(window_class):
            self.speak("I could not verify Claude.")
            return None

        return window_id

    def _message_claude_desktop(self):
        """Open a clean Claude composer and begin a direct message flow."""

        with self._message_lock:
            if self._message_stage:
                self.speak("Please finish or cancel the current message.")
                return

        window_id = self._open_claude_desktop_new_chat()
        if not window_id:
            return

        with self._message_lock:
            self._message_stage = "claude_message"
            self._pending_agent = "claude_desktop"
            self._pending_message = None
            self._pending_window_id = window_id
            self._message_retries = 1
            self._confirmation_retries = 1

        self.activate(duration_minutes=1)
        self.speak(
            "Ready.",
            expect_response=True,
            wait=True,
        )
        self._arm_message_timeout(20)

    def _send_claude_desktop_message(self, prompt, window_id):
        """Clear, type and send in the verified fresh Claude composer."""

        try:
            current_window, current_class = self._focused_window_details()
            if str(current_window) != str(window_id):
                self.speak("The focused window changed, so I cancelled.")
                return
            if not self._is_claude_desktop_window(current_class):
                self.speak("Claude is not focused, so I cancelled.")
                return

            subprocess.run(
                [
                    "/usr/bin/xdotool",
                    "key",
                    "--clearmodifiers",
                    "ctrl+a",
                    "BackSpace",
                ],
                check=True,
                timeout=5,
            )
            subprocess.run(
                [
                    "/usr/bin/xdotool",
                    "type",
                    "--clearmodifiers",
                    "--delay",
                    "15",
                    "--",
                    str(prompt),
                ],
                check=True,
                timeout=30,
            )

            current_window, current_class = self._focused_window_details()
            if str(current_window) != str(window_id) or not self._is_claude_desktop_window(current_class):
                self.speak("Claude focus changed, so I did not send it.")
                return

            subprocess.run(
                [
                    "/usr/bin/xdotool",
                    "key",
                    "--clearmodifiers",
                    "Return",
                ],
                check=True,
                timeout=5,
            )
            self.speak("Message sent.")
        except Exception:
            self.log.exception("Claude message failed")
            self.speak("I could not send the Claude message.")
