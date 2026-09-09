from ovos_bus_client import Message


class WakewordActionsMixin:
    """Wakeword barge-in and global skill cancellation hooks."""

    def _interrupt_speech_on_wakeword(self, _message):
        """Immediately silence current speech when Jarvis is invoked."""

        self.bus.emit(
            Message("mycroft.audio.speech.stop")
        )

    def can_stop(self, _message=None):
        """Report that this skill supports immediate cancellation."""

        return True

    def stop(self):
        """Stop OVOS speech, Speech Note reading and conversation."""

        self.bus.emit(
            Message("mycroft.audio.speech.stop")
        )
        self._speech_note_action("cancel")
        self._speech_note_dictating = False
        self._speech_note_dictation_paused = False

        try:
            self.deactivate()
        except Exception:
            self.log.exception(
                "Could not deactivate dispatcher"
            )

        return True
