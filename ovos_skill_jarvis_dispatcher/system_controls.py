import re
import subprocess
from ovos_bus_client import Message


class SystemControlsMixin:
    """Small, explicit keyboard, lock-state and media actions."""

    def _press_enter(self):
        """Press Enter in the currently focused application."""
        try:
            self._focused_window_details()
            self._send_focused_keys("Return")
        except Exception:
            self.log.exception("Enter key action failed")
            self.speak("I could not press Enter.")

    def _insert_new_line(self):
        """Insert a soft line break in the focused app without submitting."""
        try:
            self._focused_window_details()
            self._send_focused_keys("shift+Return")
        except Exception:
            self.log.exception("New-line action failed")
            self.speak("I could not insert a new line.")

    def _press_escape(self):
        """Press Escape in the focused app, for example to dismiss its search."""
        try:
            self._focused_window_details()
            self._send_focused_keys("Escape")
        except Exception:
            self.log.exception("Escape key action failed")
            self.speak("I could not press Escape.")

    def _set_caps_lock(self, enabled):
        """Set Caps Lock to a requested state without blindly toggling it."""
        try:
            status = subprocess.run(
                ["/usr/bin/xset", "q"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            ).stdout
            match = re.search(r"Caps Lock:\s*(on|off)", status, re.I)
            if not match:
                raise RuntimeError("Caps Lock state was unavailable")

            current = match.group(1).lower() == "on"
            if current != bool(enabled):
                # Do not use the normal --clearmodifiers shortcut helper for
                # lock keys. xdotool restores cleared modifiers afterward,
                # which would immediately restore the old Caps Lock state.
                subprocess.run(
                    ["/usr/bin/xdotool", "key", "Caps_Lock"],
                    check=True,
                    timeout=5,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception:
            self.log.exception("Caps Lock state action failed")
            state = "on" if enabled else "off"
            self.speak(f"I could not turn Caps Lock {state}.")

    def _run_media_action(self, action):
        """Delegate allowlisted playback controls to the Media skill."""
        if action not in {"play", "pause", "stop", "next", "previous"}:
            raise ValueError("Unsupported media action")
        self.bus.emit(Message("jarvis.media.control", {"action": action}))
