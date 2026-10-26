#!/usr/bin/env python3
"""Offline regression tests for managed Jarvis audio configuration."""

import importlib.util
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave


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


class WakeSoundTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="jarvis-sound-")
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.path = self.root / "jarvis-ready.wav"
        self.previous = b"a known previous default fixture"
        self.path.write_bytes(self.previous)
        self.path.chmod(0o640)
        self.source = PATH.parent.parent / "voice/jarvis-ready.wav"
        self.config = {"confirm_listening": True,
                       "sounds": {"start_listening": str(self.path), "other": "keep"},
                       "private": {"keep": True}}

    def migrate(self, source=None):
        with patch.object(audio, "OLD_WAKE_SOUND_SHA256", hashlib.sha256(self.previous).hexdigest()):
            return audio.migrate_listening_sound(self.config, self.path, source or self.source)

    def test_selected_asset_is_one_exact_short_quiet_chime(self):
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), audio.WAKE_SOUND_SHA256)
        with wave.open(str(self.source), "rb") as sound:
            self.assertEqual((sound.getnchannels(), sound.getsampwidth()), (1, 2))
            self.assertEqual((sound.getframerate(), sound.getnframes()), (48000, 15600))
            samples = sound.readframes(sound.getnframes())
        import struct
        self.assertLess(max(abs(value) for value in struct.unpack("<15600h", samples)), 6000)

    def test_known_default_changes_atomically_without_config_or_mode_changes(self):
        before = json.dumps(self.config, sort_keys=True)
        self.assertTrue(self.migrate())
        self.assertEqual(self.path.read_bytes(), self.source.read_bytes())
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o640)
        self.assertEqual(json.dumps(self.config, sort_keys=True), before)
        self.assertFalse(self.migrate())
        self.assertFalse(list(self.root.glob(".jarvis-ready-*")))

    def test_custom_missing_redirected_and_disabled_cues_are_preserved(self):
        self.path.write_bytes(b"custom sound")
        self.assertFalse(self.migrate(self.root / "missing-source.wav"))
        self.assertEqual(self.path.read_bytes(), b"custom sound")
        self.path.write_bytes(self.previous)
        self.config["sounds"]["start_listening"] = "a custom path"
        self.assertFalse(self.migrate())
        self.config["sounds"]["start_listening"] = str(self.path)
        self.config["confirm_listening"] = False
        self.assertFalse(self.migrate())
        self.assertEqual(self.path.read_bytes(), self.previous)
        self.path.unlink()
        self.config["confirm_listening"] = True
        self.assertFalse(self.migrate())
        self.assertFalse(self.path.exists())

    def test_symlinked_target_or_parent_is_not_followed(self):
        real = self.root / "custom.wav"
        self.path.rename(real)
        self.path.symlink_to(real)
        self.assertFalse(self.migrate())
        self.assertEqual(real.read_bytes(), self.previous)
        self.path.unlink()
        real.rename(self.path)
        link = self.root / "link"
        link.symlink_to(self.root, target_is_directory=True)
        linked_path = link / self.path.name
        self.config["sounds"]["start_listening"] = str(linked_path)
        with patch.object(audio, "OLD_WAKE_SOUND_SHA256", hashlib.sha256(self.previous).hexdigest()):
            self.assertFalse(audio.migrate_listening_sound(self.config, linked_path, self.source))
        self.assertEqual(self.path.read_bytes(), self.previous)

    def test_bad_source_and_failed_atomic_replace_keep_previous_sound(self):
        corrupt = self.root / "corrupt.wav"
        corrupt.write_bytes(b"not the selected sound")
        with self.assertRaises(ValueError):
            self.migrate(corrupt)
        with patch.object(Path, "replace", side_effect=OSError("fixture")):
            with self.assertRaises(OSError):
                self.migrate()
        self.assertEqual(self.path.read_bytes(), self.previous)
        self.assertFalse(list(self.root.glob(".jarvis-ready-*")))

    def test_sound_changed_during_write_is_not_overwritten(self):
        def changed(_descriptor):
            self.path.write_bytes(b"a newer user sound")
        with patch.object(os, "fsync", side_effect=changed):
            with self.assertRaises(ValueError):
                self.migrate()
        self.assertEqual(self.path.read_bytes(), b"a newer user sound")
        self.assertFalse(list(self.root.glob(".jarvis-ready-*")))

    def test_actual_485_sound_upgrades_through_cli_when_history_is_available(self):
        repo = PATH.parent.parent
        if not (repo / ".git").exists():
            self.skipTest("Clean archive: legacy identity covered by fixture tests")
        old = subprocess.run(["git", "show", "v4.8.5:voice/jarvis-ready.wav"], cwd=repo,
                             capture_output=True, check=False, timeout=10)
        if old.returncode:
            self.skipTest("Shallow checkout: retained release job checks the actual old asset")
        self.assertEqual(hashlib.sha256(old.stdout).hexdigest(), audio.OLD_WAKE_SOUND_SHA256)
        self.path.write_bytes(old.stdout)
        config_path = self.root / "mycroft.conf"
        before = json.dumps(self.config, sort_keys=True).encode()
        config_path.write_bytes(before)
        result = subprocess.run([sys.executable, str(PATH), "--config", str(config_path),
                                 "--listening-sound", str(self.path),
                                 "--refresh-listening-sound", str(self.source)],
                                capture_output=True, check=False, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.path.read_bytes(), self.source.read_bytes())
        self.assertEqual(config_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
