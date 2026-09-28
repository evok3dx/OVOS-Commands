#!/usr/bin/env python3
"""Offline tests for the reviewed listener safety patch."""

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("listener_guard", ROOT / "install.py")
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


OLD_BEGIN = '''    def _record_begin(self):
        LOG.debug("Record begin")
        if self.fake_barge_in:
            LOG.info(f"fake barge-in lowering volume to: {self.fake_barge_in_volume}")
            self.bus.emit(
                Message(
                    "mycroft.volume.set",
                    {
                        "percent": self.fake_barge_in_volume
                        / 100,  # alsa plugin expects between 0-1
                        "play_sound": False,
                    },
                    {"skill_id": "dinkum-listener"},
                )
            )
        self.bus.emit(Message(SpecMessage.LISTENER_RECORD_STARTED))
'''
OLD_END = '''    def _record_end_signal(self):
        LOG.debug("Record end")
        if self.fake_barge_in:
            LOG.info(f"fake barge-in restoring volume to: {self._default_vol}")
            self.bus.emit(
                Message(
                    "mycroft.volume.set",
                    {
                        "percent": self._default_vol
                        / 100,  # alsa plugin expects between 0-1
                        "play_sound": False,
                    },
                    {"skill_id": "dinkum-listener"},
                )
            )
        self.bus.emit(Message(SpecMessage.LISTENER_RECORD_ENDED))
'''


class ListenerGuardTests(unittest.TestCase):
    def fixture(self):
        return (
            "from threading import Thread, RLock, Event\n"
            "class Service:\n"
            "    def setup(self):\n"
            "        self._default_vol = 70  # for barge-in\n\n"
            '''    def _query_volume(self):
        """get the default volume"""
        response = self.bus.wait_for_response(Message("mycroft.volume.get"))
        if response:
            self._default_vol = int(response.data["percent"] * 100)

'''
            + OLD_BEGIN + "\n" + OLD_END + '''\n    def _handle_sound_played(self, message: Message):
        """Handle response message from audio service."""
        if not self._validate_message_context(message) or not self.voice_loop.running:
            # ignore this sound, it is targeted to an external client
            return
        if self.voice_loop.state == ListeningState.CONFIRMATION:
            self.voice_loop.state = ListeningState.BEFORE_COMMAND
'''
        ).encode()

    def test_patch_keeps_capture_nonblocking_and_restores_volume(self):
        with patch.object(guard, "digest", return_value=guard.ORIGINAL_SHA256):
            updated = guard.patched_source(self.fixture())
        text = updated.decode()
        self.assertIn(guard.MARKER, text)
        self.assertNotIn("Timer(0.35, self._lower_fake_barge_volume)", text)
        self.assertIn("Timer(3, self._finish_listening_cue)", text)
        self.assertIn("Timer(15, self._restore_fake_barge_volume)", text)
        self.assertNotIn("and self._barge_waiting_for_cue", text)
        self.assertIn("if self._barge_waiting_for_cue", text)
        self.assertIn("self._finish_listening_cue()", text)
        with patch.object(guard, "digest", return_value=guard.PATCHED_SHA256):
            self.assertEqual(guard.patched_source(updated), updated)

    def test_voice_loop_restores_upstream_confirmation_timing(self):
        upstream = '''    def _confirmation_sound(self, chunk: bytes):
        self._chunk_info.is_listen_sound = True
        if self.instant_listen:
            LOG.debug("instant_listen is on")
            self.confirmation_seconds_left = 0
            self.state = ListeningState.BEFORE_COMMAND
            LOG.debug(f"STATE: {self.state}")
            self._before_cmd(chunk)
            return

        # skip STT buffer if instant_listen is NOT set
        # Recording voice command, but user has not spoken yet
        self.transformers.feed_audio(chunk)
        self.confirmation_seconds_left -= self.mic.seconds_per_chunk
        if self.confirmation_seconds_left <= 0:
            self.state = ListeningState.BEFORE_COMMAND
            LOG.debug(f"STATE: {self.state}")
'''.encode()
        with patch.object(guard, "digest", return_value=guard.VOICE_LOOP_ORIGINAL_SHA256):
            self.assertEqual(guard.patched_voice_loop(upstream), upstream)
        gated = upstream.decode().replace(
            '''    def _confirmation_sound(self, chunk: bytes):
        self._chunk_info.is_listen_sound = True
        if self.instant_listen:
            LOG.debug("instant_listen is on")
            self.confirmation_seconds_left = 0
            self.state = ListeningState.BEFORE_COMMAND
            LOG.debug(f"STATE: {self.state}")
            self._before_cmd(chunk)
            return

        # skip STT buffer if instant_listen is NOT set
        # Recording voice command, but user has not spoken yet
        self.transformers.feed_audio(chunk)
        self.confirmation_seconds_left -= self.mic.seconds_per_chunk
        if self.confirmation_seconds_left <= 0:
            self.state = ListeningState.BEFORE_COMMAND
            LOG.debug(f"STATE: {self.state}")
''',
            '''    def _confirmation_sound(self, chunk: bytes):
        # Jarvis cue-completion and fake-barge safety: when instant listening is
        # disabled, the audio service response (or its bounded service timer)
        # advances the state. Nominal WAV duration excludes command padding.
        self._chunk_info.is_listen_sound = True
        if self.instant_listen:
            LOG.debug("instant_listen is on")
            self.confirmation_seconds_left = 0
            self.state = ListeningState.BEFORE_COMMAND
            LOG.debug(f"STATE: {self.state}")
            self._before_cmd(chunk)
            return

        self.transformers.feed_audio(chunk)
''',
        ).encode()
        with patch.object(guard, "digest", return_value=guard.VOICE_LOOP_GATED_SHA256):
            self.assertEqual(guard.patched_voice_loop(gated), upstream)

    def test_cue_response_ducks_then_record_end_restores(self):
        with patch.object(guard, "digest", return_value=guard.ORIGINAL_SHA256):
            source = guard.patched_source(self.fixture()).decode()

        class FakeMessage:
            def __init__(self, kind, data=None, context=None):
                self.msg_type = kind
                self.data = data or {}
                self.context = context or {}

        class FakeTimer:
            instances = []
            def __init__(self, seconds, callback):
                self.seconds = seconds
                self.callback = callback
                self.daemon = False
                self.cancelled = False
                self.__class__.instances.append(self)
            def start(self): pass
            def cancel(self): self.cancelled = True

        state = SimpleNamespace(CONFIRMATION="confirmation", BEFORE_COMMAND="before")
        env = {
            "Message": FakeMessage,
            "SpecMessage": SimpleNamespace(LISTENER_RECORD_STARTED="started",
                                           LISTENER_RECORD_ENDED="ended"),
            "ListeningState": state,
            "LOG": SimpleNamespace(debug=lambda *a: None, info=lambda *a: None),
        }
        exec(source, env)
        env["Timer"] = FakeTimer
        service = env["Service"]()
        service._default_vol = 100
        service._barge_restore_timer = None
        service._barge_lower_timer = None
        service._barge_cue_timer = None
        service._barge_waiting_for_cue = False
        service._barge_volume_lowered = False
        service.config = {"confirm_listening": True,
                          "sounds": {"start_listening": "/cue.wav"}}
        service.fake_barge_in = True
        service.fake_barge_in_volume = 20
        service.voice_loop = SimpleNamespace(state=state.CONFIRMATION, running=True)
        service._validate_message_context = lambda message: True
        service.bus = SimpleNamespace(
            events=[],
            emit=lambda message: service.bus.events.append(message),
            wait_for_response=lambda message, timeout=None:
                FakeMessage("response", {"percent": 1.0}),
        )

        service._record_begin()
        self.assertFalse(service._barge_volume_lowered)
        self.assertEqual(FakeTimer.instances[-1].seconds, 3)
        self.assertFalse(any(event.msg_type == "mycroft.volume.set"
                             for event in service.bus.events))
        # The upstream loop may already have opened capture before the audio
        # service confirms cue playback. That must not block volume handling.
        service.voice_loop.state = state.BEFORE_COMMAND
        service._handle_sound_played(FakeMessage("response"))
        self.assertTrue(service._barge_volume_lowered)
        self.assertEqual(service.voice_loop.state, state.BEFORE_COMMAND)
        self.assertEqual(service.bus.events[-1].data["percent"], 0.2)
        service._record_end_signal()
        self.assertFalse(service._barge_volume_lowered)
        self.assertEqual(service.bus.events[-2].data["percent"], 1.0)
        self.assertEqual(service.bus.events[-1].msg_type, "ended")

    def test_missing_fresh_volume_snapshot_never_ducks(self):
        with patch.object(guard, "digest", return_value=guard.ORIGINAL_SHA256):
            text = guard.patched_source(self.fixture()).decode()
        self.assertIn('timeout=0.5', text)
        self.assertIn('fake barge-in skipped: current volume is unavailable', text)
        self.assertIn('elif self.fake_barge_in and self._barge_volume_snapshot_valid:', text)

    def test_unknown_source_is_rejected(self):
        with self.assertRaises(RuntimeError):
            guard.patched_source(b"unknown")

    def test_marker_alone_does_not_bypass_exact_source_check(self):
        with self.assertRaises(RuntimeError):
            guard.patched_source(guard.OLD_MARKER.encode())


if __name__ == "__main__":
    unittest.main(verbosity=2)
