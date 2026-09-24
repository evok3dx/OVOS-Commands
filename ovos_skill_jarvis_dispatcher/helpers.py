import re
import subprocess
from pathlib import Path


class DispatcherHelpersMixin:
    """Shared text, window and visible-content helpers."""

    def _read_visible_text(
        self,
        mode: str,
        speed: int = 1
    ) -> None:
        """Read selected text or useful content from the focused app."""

        helper = Path.home() / ".local/bin/jarvis-read-visible-text"

        if mode == "selection":
            failure = "I could not find any selected text."
        else:
            failure = "I could not read content from that window."

        # Speech Note plays through the same speakers heard by the microphone.
        # Mute only the OVOS listener before playback starts so that page text
        # cannot be mistaken for the wake word. The physical microphone and
        # desktop audio remain unchanged.
        self._mute_listener_for_speech_note()

        try:
            subprocess.run(
                [str(helper), mode, str(speed)],
                check=True,
                timeout=12,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self._speech_note_reading = True
            self._watch_speech_note_reading()
        except Exception:
            self._restore_listener_after_speech_note()
            self.log.exception(
                f"Visible text reading failed: {mode}"
            )
            self.speak(failure)

    @staticmethod
    def _confirmation_token(response) -> str:
        if not response:
            return ""

        token = str(response).lower().replace("'", "")
        token = re.sub(r"[^a-z0-9 ]+", " ", token)
        return " ".join(token.split())

    def _type_into_window(
        self,
        window_id,
        text,
        press_enter=False
    ):
        """Type confirmed text and optionally press Enter safely."""

        try:
            if not str(window_id).isdigit():
                raise RuntimeError("Invalid target window")

            class_result = subprocess.run(
                [
                    "/usr/bin/xprop",
                    "-id",
                    str(window_id),
                    "WM_CLASS"
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=5
            )
            window_class = class_result.stdout.lower()
            is_terminal = "terminal" in window_class

            subprocess.run(
                [
                    "/usr/bin/xdotool",
                    "windowactivate",
                    "--sync",
                    str(window_id)
                ],
                check=True,
                timeout=8
            )

            subprocess.run(
                [
                    "/usr/bin/xdotool",
                    "type",
                    "--clearmodifiers",
                    "--delay",
                    "15",
                    "--",
                    text
                ],
                check=True,
                timeout=30
            )

            self._last_typed_text = text

            if press_enter and is_terminal:
                self.speak(
                    "Written, but I will not press Enter in Terminal."
                )
                return

            if press_enter:
                subprocess.run(
                    [
                        "/usr/bin/xdotool",
                        "key",
                        "--clearmodifiers",
                        "Return"
                    ],
                    check=True,
                    timeout=5
                )
                self.speak("Written and Enter pressed.")
            else:
                self.speak("Written.")

        except Exception:
            self.log.exception("Focused text entry failed")
            self.speak("I could not write into that window.")
