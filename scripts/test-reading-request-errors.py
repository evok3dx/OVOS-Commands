#!/usr/bin/env python3
"""Check that a reader startup never masquerades as a missing selection."""
import importlib.util
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch


source = Path(__file__).resolve().parents[1] / "ovos_skill_jarvis_dispatcher/helpers.py"
spec = importlib.util.spec_from_file_location("reader_error_mapping", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Reader(module.DispatcherHelpersMixin):
    def __init__(self):
        self.spoken = []
        self.log = Mock()
        self._speech_note_reading = False
        self.watch = Mock()
        self.restore = Mock()

    def speak(self, words):
        self.spoken.append(words)

    def _mute_listener_for_speech_note(self):
        pass

    def _restore_listener_after_speech_note(self):
        self.restore()

    def _watch_speech_note_reading(self):
        self.watch()


for status, mode, expected in (
    (0, "selection", None),
    (20, "selection", "I could not find any selected text."),
    (22, "selection", "Speech Note could not start reading."),
    (22, "page", "Speech Note could not start reading."),
    (1, "page", "I could not read content from that window."),
):
    reader = Reader()
    with patch.object(module.subprocess, "run", return_value=subprocess.CompletedProcess([], status)):
        reader._read_visible_text(mode, speed=2)
    assert reader.spoken == ([] if expected is None else [expected]), (status, reader.spoken)
    assert reader.watch.call_count == int(status == 0)
    assert reader.restore.call_count == int(status != 0)

reader = Reader()
with patch.object(module.subprocess, "run", side_effect=subprocess.TimeoutExpired("reader", 12)):
    reader._read_visible_text("selection")
assert reader.spoken == ["Speech Note could not start reading."]
assert reader.restore.call_count == 1
print("PASS: Speech Note startup, empty selection and timeout have distinct feedback")
