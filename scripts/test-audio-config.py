#!/usr/bin/env python3
"""Offline regression tests for managed Jarvis audio configuration."""

import importlib.util
from pathlib import Path
import unittest


PATH = Path(__file__).with_name("configure-audio-stack.py")
SPEC = importlib.util.spec_from_file_location("jarvis_audio_config", PATH)
audio = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audio)


class AudioConfigTests(unittest.TestCase):
    def test_fresh_defaults_use_event_gate_and_vad(self):
        result = audio.configure({}, Path("/tmp/jarvis-ready.wav"))
        listener = result["listener"]
        self.assertIs(listener["instant_listen"], False)
        self.assertIs(listener["fake_barge_in"], True)
        self.assertEqual(listener["barge_in_volume"], 20)
        self.assertNotIn("barge_in_delay", listener)
        self.assertIs(result["stt"][audio.STT_MODULE]["vad_filter"], True)

    def test_exact_old_default_migrates_without_replacing_other_settings(self):
        config = {
            "private": {"keep": True},
            "listener": {**audio.MANAGED_OLD_LISTENER, "microphone": {"device": 7}},
            "stt": {"module": audio.STT_MODULE,
                    audio.STT_MODULE: {"model": "small.en", "beam_size": 3}},
        }
        result, changed = audio.migrate_managed(config)
        self.assertTrue(changed)
        self.assertEqual(result["private"], {"keep": True})
        self.assertEqual(result["listener"]["microphone"], {"device": 7})
        self.assertIs(result["listener"]["instant_listen"], False)
        self.assertEqual(result["listener"]["barge_in_volume"], 20)
        self.assertNotIn("barge_in_delay", result["listener"])
        self.assertEqual(result["stt"][audio.STT_MODULE]["beam_size"], 3)
        self.assertIs(result["stt"][audio.STT_MODULE]["vad_filter"], True)

    def test_custom_audio_and_explicit_vad_choice_are_preserved(self):
        config = {
            "listener": {**audio.MANAGED_OLD_LISTENER, "barge_in_volume": 35},
            "stt": {"module": audio.STT_MODULE,
                    audio.STT_MODULE: {"model": "small.en", "vad_filter": False}},
        }
        result, changed = audio.migrate_managed(config)
        self.assertFalse(changed)
        self.assertEqual(result["listener"]["barge_in_volume"], 35)
        self.assertIs(result["listener"]["instant_listen"], True)
        self.assertIs(result["stt"][audio.STT_MODULE]["vad_filter"], False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
