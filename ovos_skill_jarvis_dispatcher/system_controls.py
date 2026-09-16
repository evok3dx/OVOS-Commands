import re
import subprocess


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
        """Control the active Cinnamon/MPRIS media player with playerctl."""
        if action not in {"play", "pause", "stop", "next", "previous"}:
            raise ValueError("Unsupported media action")

        try:
            subprocess.run(
                ["/usr/bin/playerctl", action],
                check=True,
                timeout=10,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            self.log.error("playerctl is unavailable")
            self.speak("Media control is not installed.")
        except subprocess.CalledProcessError:
            self.log.info("No controllable media player for action: %s", action)
            self.speak("No media player is available.")
        except Exception:
            self.log.exception("Media action failed: %s", action)
            self.speak("I could not control media playback.")
