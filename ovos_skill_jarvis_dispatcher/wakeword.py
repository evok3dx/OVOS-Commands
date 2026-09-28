from ovos_bus_client import Message


class WakewordActionsMixin:
    """Wakeword barge-in and global skill cancellation hooks."""

    def can_stop(self, _message=None):
        """Report that this skill supports immediate cancellation."""

        return True

    def stop(self):
        """Stop OVOS speech, Speech Note reading and conversation."""

        active_speech_note = bool(
            getattr(self, "_speech_note_reading", False)
            or getattr(self, "_speech_note_dictating", False)
            or getattr(self, "_speech_note_dictation_paused", False)
            or getattr(self, "_message_stage", None)
        )

        router = getattr(self, "_qwen_router", None)
        if router is not None:
            router.cancel()

        self.bus.emit(Message("jarvis.media.cancel"))

        self.bus.emit(
            Message("mycroft.audio.speech.stop")
        )
        if active_speech_note:
            # A bare Stop belongs to the active reading, dictation or prompted
            # writing workflow. Do not also stop unrelated browser media.
            if (getattr(self, "_speech_note_dictating", False) or
                    getattr(self, "_speech_note_dictation_paused", False)):
                self._finish_speech_note_dictation()
            else:
                self._stop_speech_note_reading()
        else:
            # With no active text workflow, retain normal MPRIS Stop behavior.
            self._run_media_action("stop")

        try:
            self._clear_message_state()
        except Exception:
            self.log.exception(
                "Could not clear dispatcher state"
            )

        return True
