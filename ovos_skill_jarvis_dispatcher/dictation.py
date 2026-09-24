import re
import subprocess
import threading
import time

from ovos_bus_client import Message

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

    def _speech_note_task_state(self):
        """Return Speech Note's current task state through its session D-Bus."""

        try:
            result = subprocess.run(
                [
                    "/usr/bin/gdbus", "call", "--session",
                    "--dest", "net.mkiol.SpeechNote",
                    "--object-path", "/net/mkiol/SpeechNote",
                    "--method",
                    "org.freedesktop.DBus.Properties.Get",
                    "net.mkiol.SpeechNote", "TaskState"
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=3
            )
            match = re.search(r"<(\d+)>", result.stdout)
            return int(match.group(1)) if match else None
        except Exception:
            return None

    def _mute_listener_for_speech_note(self):
        """Mute only OVOS input while Speech Note is reading aloud."""

        with self._reader_monitor_lock:
            if self._reader_listener_muted:
                return
            self._reader_listener_muted = True

        self.bus.emit(Message(
            "mycroft.mic.mute",
            context={"source": "jarvis.speech-note-reader"},
        ))
        self.log.info("Jarvis listening muted during Speech Note reading")

    def _restore_listener_after_speech_note(self):
        """Restore OVOS input if this skill muted it for page reading."""

        with self._reader_monitor_lock:
            if not self._reader_listener_muted:
                return
            self._reader_listener_muted = False
            self._reader_monitor_generation += 1

        self.bus.emit(Message(
            "mycroft.mic.unmute",
            context={"source": "jarvis.speech-note-reader"},
        ))
        self.log.info("Jarvis listening restored after Speech Note reading")

    def _watch_speech_note_reading(self):
        """Restore listening when Speech Note naturally reaches idle."""

        with self._reader_monitor_lock:
            self._reader_monitor_generation += 1
            generation = self._reader_monitor_generation

        def monitor():
            saw_playback = False
            startup_deadline = time.monotonic() + 4

            while True:
                with self._reader_monitor_lock:
                    if generation != self._reader_monitor_generation:
                        return

                state = self._speech_note_task_state()
                if state in {4, 5, 6}:
                    saw_playback = True
                elif saw_playback or time.monotonic() >= startup_deadline:
                    self._speech_note_reading = False
                    self._restore_listener_after_speech_note()
                    return

                time.sleep(0.2)

        threading.Thread(
            target=monitor,
            name="jarvis-speech-note-monitor",
            daemon=True,
        ).start()

    def _stop_speech_note_reading(self) -> bool:
        """Cancel Speech Note TTS and verify that it reaches idle state."""

        state = self._speech_note_task_state()

        if state is None:
            if self._speech_note_reading:
                stopped = self._speech_note_action("cancel")
                self._speech_note_reading = False
                self._restore_listener_after_speech_note()
                return stopped
            self._restore_listener_after_speech_note()
            return True

        # Task states 4 and 5 are SpeechPlaying and SpeechPaused. State 6 is
        # an in-progress cancellation. Other states are not reader playback.
        if state not in {4, 5, 6}:
            self._speech_note_reading = False
            self._restore_listener_after_speech_note()
            return True

        try:
            if state in {4, 5}:
                subprocess.run(
                    [
                        "/usr/bin/gdbus", "call", "--session",
                        "--dest", "net.mkiol.SpeechNote",
                        "--object-path", "/net/mkiol/SpeechNote",
                        "--method", "net.mkiol.SpeechNote.InvokeAction",
                        "cancel", "{}"
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=3
                )

            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                if self._speech_note_task_state() == 0:
                    self._speech_note_reading = False
                    self._restore_listener_after_speech_note()
                    self.log.info("Speech Note reading stopped")
                    return True
                time.sleep(0.05)
        except Exception:
            self.log.exception("Speech Note D-Bus cancellation failed")

        # Compatibility fallback for older Speech Note releases or an
        # unavailable D-Bus service.
        stopped = self._speech_note_action("cancel")
        self._speech_note_reading = False
        self._restore_listener_after_speech_note()
        return stopped

    def _pause_speech_note_reading(self, _message=None):
        """Stop our reader when listening starts by wake word or hotkey."""

        if self._speech_note_dictating:
            if self._speech_note_action("stop-listening"):
                self._speech_note_dictating = False
                self._speech_note_dictation_paused = True
            return

        if self._speech_note_dictation_paused:
            return

        # Query Speech Note itself instead of trusting local state. This also
        # handles reading that survived a skill restart.
        self._stop_speech_note_reading()

    def _start_speech_note_dictation(self):
        """Begin active-window dictation after spoken feedback finishes."""

        self.speak("Ready.", wait=True)

        if self._speech_note_action("start-listening-active-window"):
            self._speech_note_dictating = True
            self._speech_note_dictation_paused = False
        else:
            self.speak("I could not start dictation.")
