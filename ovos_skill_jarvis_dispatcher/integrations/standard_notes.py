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
        normalised_class = "".join(
            character for character in window_class if character.isalnum()
        )
        return "standardnotes" in normalised_class

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

    def _search_standard_notes(self):
        """Open Standard Notes' universal palette and enter a query."""
        applications = self._jarvis_profile.get("applications", {})
        notes = applications.get("notes", {})

        if notes.get("integration") != "standard_notes":
            self.speak("Notes search is not configured.")
            return

        if not self._run_desktop_app_action("notes", "focus", announce=False):
            self.speak("I could not open Notes.")
            return

        try:
            time.sleep(0.2)
            if not self._standard_notes_is_focused():
                raise RuntimeError("Standard Notes did not gain focus")

            original_window, _ = self._focused_window_details()
            self._send_focused_keys("ctrl+shift+colon")

            response = self.get_response(
                "What should I search for?", num_retries=0, wait=True,
            )
            if self._cancelled_search(response):
                self.speak("Cancelled.")
                return

            current_window, _ = self._focused_window_details()
            if current_window != original_window or not self._standard_notes_is_focused():
                self.speak("The focused window changed, so I cancelled.")
                return

            self._type_focused_text(response)
        except Exception:
            self.log.exception("Standard Notes search failed")
            self.speak("I could not search Notes.")
