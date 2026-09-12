import subprocess
from pathlib import Path


class SystemAudioActionsMixin:
    """Explicit, allowlisted control of the system microphone."""

    def _mute_system_microphone(self):
        helper = Path.home() / ".local/bin/jarvis-system-microphone"

        try:
            subprocess.run(
                [str(helper), "mute"],
                check=True,
                timeout=10,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            self.log.exception("System microphone mute failed")
            self.speak("I could not mute the system microphone.")
            return

        self.speak(
            "System microphone muted. Use the keyboard or sound settings "
            "to unmute it."
        )

    def _mute_jarvis_listener(self):
        """Stop only Jarvis listening through the existing tray helper."""
        helper = Path.home() / ".local/bin/jarvis-mic-toggle"

        try:
            active = subprocess.run(
                [
                    "/usr/bin/systemctl", "--user", "is-active", "--quiet",
                    "ovos-listener",
                ],
                check=False,
                timeout=5,
            ).returncode == 0
            if not active:
                self.speak("Jarvis listening is already muted.")
                return

            subprocess.run(
                [str(helper)],
                check=True,
                timeout=15,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            self.log.exception("Jarvis listener mute failed")
            self.speak("I could not mute Jarvis listening.")
            return

        self.speak("Jarvis listening muted. Use the microphone icon to reactivate me.")
