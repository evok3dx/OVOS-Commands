import subprocess
import time


class HermesDesktopIntegrationMixin:
    """Verified keyboard controls for the Hermes Desktop composer."""

    @staticmethod
    def _is_hermes_desktop_window(window_class):
        return "hermes" in str(window_class or "").lower()

    def _focus_hermes_desktop(self):
        if not self._run_desktop_app_action("hermes", "focus", announce=False):
            return False

        for _ in range(20):
            try:
                window_id, window_class = self._focused_window_details()
            except Exception:
                time.sleep(0.1)
                continue
            if window_id and self._is_hermes_desktop_window(window_class):
                return True
            time.sleep(0.1)

        self.speak("I could not verify Hermes.")
        return False

    def _run_hermes_action(self, action):
        shortcuts = {
            "focus_composer": ("ctrl+l",),
            "model_picker": ("ctrl+shift+m",),
            "insert_newline": ("ctrl+l", "shift+Return"),
            "queue_message": ("ctrl+l", "ctrl+Return"),
            "send_queued": ("ctrl+shift+k",),
            "command_palette": ("ctrl+l", "/"),
            "reference": ("ctrl+l", "@"),
            "cancel": ("Escape",),
        }
        if action not in shortcuts:
            raise ValueError("Unsupported Hermes action")
        if not self._focus_hermes_desktop():
            return

        try:
            for key in shortcuts[action]:
                if key in {"/", "@"}:
                    self._type_focused_text(key)
                else:
                    self._send_focused_keys(key)
        except (OSError, subprocess.SubprocessError):
            self.log.exception("Hermes Desktop action failed: %s", action)
            self.speak("I could not control Hermes.")

    def _message_hermes_desktop(self):
        """Focus the Hermes composer and begin a direct message flow."""
        with self._message_lock:
            if self._message_stage:
                self.speak("Please finish or cancel the current message.")
                return

        if not self._focus_hermes_desktop():
            return

        try:
            window_id, window_class = self._focused_window_details()
            if not self._is_hermes_desktop_window(window_class):
                raise RuntimeError("Hermes is not focused")
            self._send_focused_keys("ctrl+l")
            self._send_focused_keys("ctrl+a")
            self._send_focused_keys("BackSpace")
        except Exception:
            self.log.exception("Could not prepare the Hermes composer")
            self.speak("I could not prepare Hermes.")
            return

        with self._message_lock:
            self._message_stage = "hermes_message"
            self._pending_agent = "hermes_desktop"
            self._pending_message = None
            self._pending_window_id = window_id
            self._message_retries = 1
            self._confirmation_retries = 0

        self.activate(duration_minutes=1)
        self.speak(
            "What should I send to Hermes?",
            expect_response=True,
            wait=True,
        )
        self._arm_message_timeout(20)

    def _send_hermes_desktop_message(self, prompt, window_id):
        """Clear, type and send in the same verified Hermes composer."""
        try:
            current_window, current_class = self._focused_window_details()
            if str(current_window) != str(window_id):
                self.speak("The focused window changed, so I cancelled.")
                return
            if not self._is_hermes_desktop_window(current_class):
                self.speak("Hermes is not focused, so I cancelled.")
                return

            self._send_focused_keys("ctrl+l")
            self._send_focused_keys("ctrl+a")
            self._send_focused_keys("BackSpace")
            self._type_focused_text(str(prompt))
            self._send_focused_keys("Return")
        except Exception:
            self.log.exception("Hermes message failed")
            self.speak("I could not send the Hermes message.")
