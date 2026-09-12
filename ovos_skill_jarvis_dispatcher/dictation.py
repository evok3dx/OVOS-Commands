import subprocess



class DictationActionsMixin:
    """Speech Note control and immediate voice interruption hooks."""

    def _speech_note_action(self, action: str) -> bool:
        """Invoke a supported action on the running Speech Note app."""

        try:
            subprocess.run(
                [
                    "/usr/bin/flatpak",
                    "run",
                    "net.mkiol.SpeechNote",
                    "--action",
                    action
                ],
                check=True,
                timeout=5,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except Exception:
            self.log.exception(
                f"Speech Note action failed: {action}"
            )
            return False

    def _pause_speech_note_reading(self, _message=None):
        """Pause reading or dictation when Jarvis wakes."""

        if self._speech_note_dictating:
            if self._speech_note_action("stop-listening"):
                self._speech_note_dictating = False
                self._speech_note_dictation_paused = True
            return

        if self._speech_note_dictation_paused:
            return

        self._speech_note_action("pause-resume-reading")

    def _start_speech_note_dictation(self):
        """Begin active-window dictation after spoken feedback finishes."""

        self.speak("I'm listening.", wait=True)

        if self._speech_note_action("start-listening-active-window"):
            self._speech_note_dictating = True
            self._speech_note_dictation_paused = False
        else:
            self.speak("I could not start dictation.")


