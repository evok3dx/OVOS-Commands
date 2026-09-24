from ovos_bus_client import Message


class WakewordActionsMixin:
    """Wakeword barge-in and global skill cancellation hooks."""

    def can_stop(self, _message=None):
        """Report that this skill supports immediate cancellation."""

        return True

    def stop(self):
        """Stop OVOS speech, Speech Note reading and conversation."""

        router = getattr(self, "_qwen_router", None)
        if router is not None:
            router.cancel()

        self.bus.emit(
            Message("mycroft.audio.speech.stop")
        )
        self._stop_speech_note_reading()
        self._speech_note_dictating = False
        self._speech_note_dictation_paused = False

        try:
            self._clear_message_state()
        except Exception:
            self.log.exception(
                "Could not clear dispatcher state"
            )

        return True
