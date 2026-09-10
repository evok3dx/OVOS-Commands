"""Standard Notes-specific actions."""

import subprocess
import time


class StandardNotesIntegrationMixin:
    """Actions available only when Notes maps to Standard Notes."""

    @staticmethod
    def _standard_notes_is_focused():
        """Return whether Standard Notes owns the active X11 window."""

        window = subprocess.run(
            ["/usr/bin/xdotool", "getactivewindow"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        if not window.isdigit():
            return False

        window_class = subprocess.run(
            ["/usr/bin/xprop", "-id", window, "WM_CLASS"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.lower()
        return "standard notes" in window_class

    def _create_new_note(self):
        applications = self._jarvis_profile.get("applications", {})
        notes = applications.get("notes", {})

        if notes.get("integration") != "standard_notes":
            self.speak("A new-note action is not configured.")
            return

        if not self._run_desktop_app_action(
            "notes",
            "focus",
            announce=False,
        ):
            self.speak("I could not open Notes.")
            return

        try:
            time.sleep(0.2)
            if not self._standard_notes_is_focused():
                raise RuntimeError("Standard Notes did not gain focus")

            subprocess.run(
                [
                    "/usr/bin/xdotool",
                    "key",
                    "--clearmodifiers",
                    "alt+shift+n",
                ],
                check=True,
                timeout=5,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            self.log.exception("Standard Notes new-note action failed")
            self.speak("I could not create a new note.")
            return

        self.speak("New note ready.")
