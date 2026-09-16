"""Proton Mail-specific actions."""

import subprocess
import time


class ProtonMailIntegrationMixin:
    """Actions available only when Mail maps to Proton Mail."""

    @staticmethod
    def _proton_mail_is_focused():
        window = subprocess.run(
            ["/usr/bin/xdotool", "getactivewindow"],
            check=True, capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        if not window.isdigit():
            return False

        window_class = subprocess.run(
            ["/usr/bin/xprop", "-id", window, "WM_CLASS"],
            check=False, capture_output=True, text=True, timeout=5,
        ).stdout.lower()
        return any(
            name in window_class
            for name in ("proton mail", "proton-mail", "protonmail")
        )

    def _prepare_proton_mail(self):
        applications = self._jarvis_profile.get("applications", {})
        mail = applications.get("proton_mail", {})
        if not mail and applications.get("mail", {}).get("integration") == "proton_mail":
            mail = applications["mail"]
        if mail.get("integration") != "proton_mail":
            self.speak("A Proton Mail action is not configured.")
            return False

        category = "proton_mail" if "proton_mail" in applications else "mail"
        if not self._run_desktop_app_action(category, "focus", announce=False):
            self.speak("I could not open Proton Mail.")
            return False

        time.sleep(0.2)
        if not self._proton_mail_is_focused():
            raise RuntimeError("Proton Mail did not gain focus")
        return True

    def _create_new_email(self):
        try:
            if not self._prepare_proton_mail():
                return
            self._send_focused_keys("n")
            self.speak("New email ready.")
        except Exception:
            self.log.exception("Proton Mail compose action failed")
            self.speak("I could not create a new email.")

    def _search_proton_mail(self):
        try:
            if not self._prepare_proton_mail():
                return

            original_window, _ = self._focused_window_details()
            self._send_focused_keys("slash")

            response = self.get_response(
                "What should I search for?", num_retries=0, wait=True,
            )
            if self._cancelled_search(response):
                self.speak("Cancelled.")
                return

            current_window, _ = self._focused_window_details()
            if current_window != original_window or not self._proton_mail_is_focused():
                self.speak("The focused window changed, so I cancelled.")
                return

            self._type_focused_text(response)
            self._send_focused_keys("Return")
        except Exception:
            self.log.exception("Proton Mail search failed")
            self.speak("I could not search Proton Mail.")
