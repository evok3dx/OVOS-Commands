import re
import subprocess
from pathlib import Path


class DesktopActionsMixin:
    """Allowlisted desktop application and window actions."""

    def _focused_window_action(self, action: str) -> None:
        """Control the currently focused normal window."""

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

        if action == "close":
            self.speak("Window closed.")


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

        if action == "open" and ("website" in utterance or "online" in utterance):
            if any(name in utterance for name in (
                "chatgpt", "gpt", "chat g p t", "chat website", "chat online"
            )):
                self._open_fixed_website("ChatGPT", "https://chatgpt.com/")
                return
            if any(name in utterance for name in ("claude", "cloud", "clawed")):
                self._open_fixed_website("Claude", "https://claude.ai/")
                return

        app = self._desktop_app_from_message(message)

        if not app:
            self.speak("I could not identify the application.")
            return

        self._run_desktop_app_action(app, action)

    def _run_desktop_app_action(self, app, action, announce=True):
        """Run one resolved application action and report success."""

        display_name = self._desktop_app_display_names.get(
            app,
            app.replace("_", " ").title(),
        )
        integration = self._desktop_app_integrations.get(app, app)
        timeout = 40 if integration == "hermes_desktop" else 15

        try:
            subprocess.run(
                [
                    str(
                        Path.home()
                        / ".local/bin/jarvis-app-window"
                    ),
                    action,
                    integration
                ],
                check=True,
                timeout=timeout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            self.log.exception(
                f"Desktop application action failed: "
                f"{action} {app}"
            )

            if announce:
                if action in ("minimize", "maximize", "close"):
                    self.speak(f"{display_name} is not open.")
                else:
                    self.speak(f"I could not open {display_name}.")
            return False

        if announce and action == "open":
            self.speak(f"Opening {display_name}.")
        elif announce and action == "close":
            self.speak(f"{display_name} closed.")
        return True
