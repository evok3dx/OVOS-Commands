"""Zoom-specific actions."""

import html
import re
import subprocess
from urllib.parse import parse_qs, quote, urlparse


class ZoomIntegrationMixin:
    """Strict, local handling of copied Zoom meeting links."""

    @staticmethod
    def _zoom_uri_from_clipboard():
        clipboard = subprocess.run(
            ["/usr/bin/xclip", "-selection", "clipboard", "-o"],
            check=True, capture_output=True, text=True, timeout=5,
        ).stdout[:65536]

        for candidate in re.findall(r"https?://[^\s<>\"']+", clipboard):
            candidate = html.unescape(candidate).rstrip(".,;:!?)]}")
            parsed = urlparse(candidate)
            hostname = (parsed.hostname or "").lower().rstrip(".")
            if hostname != "zoom.us" and not hostname.endswith(".zoom.us"):
                continue

            match = re.fullmatch(r"/(?:j|s)/(\d+)/?", parsed.path)
            if not match:
                continue

            meeting_id = match.group(1)
            password = parse_qs(parsed.query).get("pwd", [""])[0]
            uri = (
                "zoommtg://zoom.us/join?action=join"
                f"&confno={meeting_id}"
            )
            if password:
                uri += f"&pwd={quote(password, safe='')}"
            return uri

        return None

    def _join_zoom_meeting(self):
        applications = self._jarvis_profile.get("applications", {})
        zoom = applications.get("zoom", {})
        if zoom.get("integration") != "zoom":
            self.speak("A Zoom meeting action is not configured.")
            return

        try:
            uri = self._zoom_uri_from_clipboard()
        except Exception:
            self.log.error("Could not read the clipboard for a Zoom meeting")
            self.speak("I could not read the copied meeting link.")
            return

        if not uri:
            self._run_desktop_app_action("zoom", "focus", announce=False)
            self.speak("Copy a Zoom meeting link first.")
            return

        try:
            subprocess.run(
                ["/usr/bin/xdg-open", uri],
                check=True, timeout=10,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception:
            # CalledProcessError contains the URI and its embedded password,
            # so deliberately do not log the exception object.
            self.log.error("Zoom meeting launch failed")
            self.speak("I could not open the Zoom meeting.")
