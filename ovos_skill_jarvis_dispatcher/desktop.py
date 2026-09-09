import re
import subprocess
from pathlib import Path


class DesktopActionsMixin:
    """Allowlisted desktop application and window actions."""

    def _focused_window_action(self, action: str) -> None:
        """Close or minimise the currently focused normal window."""

        helper = Path.home() / ".local/bin/jarvis-focused-window"

        try:
            subprocess.run(
                [str(helper), action],
                check=True,
                timeout=10,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            self.log.exception(
                f"Focused window action failed: {action}"
            )
            self.speak("I could not control that window.")
            return

        spoken_actions = {
            "close": "Window closed.",
            "minimize": "Window minimized.",
            "maximize": "Window maximized."
        }
        self.speak(spoken_actions[action])

    def _window_action(self, action: str, agent: str) -> None:
        helper = Path.home() / ".local/bin/jarvis-agent-window"
        display = self.AGENT_NAMES[agent]

        try:
            subprocess.run(
                [str(helper), action, agent],
                check=True,
                timeout=15
            )
        except Exception:
            self.log.exception("Agent window action failed")
            self.speak(f"I could not {action} {display}.")
            return

        responses = {
            "open": f"{display} is ready.",
            "focus": f"Showing {display}.",
            "minimize": f"{display} is minimized.",
            "close": f"{display} is hidden. Its work continues."
        }
        self.speak(responses[action])

    def _desktop_app_from_message(self, message):
        utterance = str(
            message.data.get("utterance", "")
        ).lower()

        for app, aliases in self._desktop_app_aliases.items():
            for alias in sorted(aliases, key=len, reverse=True):
                if re.search(
                    rf"\b{re.escape(alias)}\b",
                    utterance
                ):
                    return app

        return None

    def _desktop_app_action(self, message, action):
        utterance = str(
            message.data.get("utterance", "")
        ).lower()

        # Keep Claude Agent separate from Claude Desktop.
        if "agent" in utterance and (
            "claude" in utterance or "clawed" in utterance
        ):
            self._window_action(action, "claude")
            return

        app = self._desktop_app_from_message(message)

        if not app:
            self.speak("I could not identify the application.")
            return

        display_names = {
            "brave": "Brave",
            "firefox": "Firefox",
            "signal": "Signal",
            "zoom": "Zoom",
            "terminal": "Terminal",
            "notes": "Notes",
            "office": "Office",
            "claude": "Claude"
        }

        display_names.update({
            "mail": "Proton Mail",
            "calendar": "Proton Calendar",
        })

        spoken_actions = {
            "open": "Opening",
            "focus": "Showing",
            "minimize": "Minimizing",
            "close": "Closing"
        }

        try:
            subprocess.run(
                [
                    str(
                        Path.home()
                        / ".local/bin/jarvis-app-window"
                    ),
                    action,
                    app
                ],
                check=True,
                timeout=15,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            self.log.exception(
                f"Desktop application action failed: "
                f"{action} {app}"
            )

            if action in ("minimize", "close"):
                self.speak(
                    f"{display_names[app]} is not open."
                )
            else:
                self.speak(
                    f"I could not open {display_names[app]}."
                )
            return

        self.speak(
            f"{spoken_actions[action]} {display_names[app]}."
        )
