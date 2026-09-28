#!/usr/bin/env python3
"""Install the reviewed Dinkum fake-barge-in volume restoration guard."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import os
from pathlib import Path
import py_compile
import shutil
import tempfile
from datetime import datetime, timezone


VERSION = "0.10.5a1"
ORIGINAL_SHA256 = "dd78724a217b5910bd282f1df432f050c8cda1ed330236b6c9d1b5f96ce9440b"
OLD_PATCHED_SHA256 = "75dec81583a719e26b150dd1ba6e8009e74e8890704e3ccf4e5ebae33af038fc"
RC7_PATCHED_SHA256 = "2eefc8a61cce77b14a2e5adc825b0aa6de75be993d5655946ffd013aa1eb1821"
RC8_PATCHED_SHA256 = "1dff82d88dd291c8ce99d0e00b186e48af7d8c6114b35fdde65969c3fa31a755"
RC9_PATCHED_SHA256 = "8e406591204e6866488cf395461f922ba6ab3ed3fff50cf62eb63f4352f92df4"
PATCHED_SHA256 = "74558ed26f6ade629da5483a177ea6f061f438eef315f8de42b141cdd16338aa"
VOICE_LOOP_ORIGINAL_SHA256 = "80ed4151bdd50678934f67c022a4dd8672621e98f03b095db14350d8f89c7b89"
VOICE_LOOP_GATED_SHA256 = "07168c0c775220689de0632ba7d14cd1e9b8033663c85321902eb65c38a40423"
OLD_MARKER = "Jarvis fake-barge-in safety timeout"
RC7_MARKER = "Jarvis audible cue and fake-barge safety"
RC9_MARKER = "Jarvis cue-completion and fake-barge safety"
MARKER = "Jarvis nonblocking cue and fake-barge safety"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_paths() -> tuple[Path, Path]:
    spec = importlib.util.find_spec("ovos_dinkum_listener.service")
    if spec is None or not spec.origin:
        raise RuntimeError("ovos_dinkum_listener.service is not installed")
    service = Path(spec.origin).resolve()
    voice_loop = service.parent / "voice_loop" / "voice_loop.py"
    if not voice_loop.is_file():
        raise RuntimeError("ovos_dinkum_listener voice loop is not installed")
    return service, voice_loop.resolve()


def rc7_source(original: bytes) -> bytes:
    source_digest = digest(original)
    if source_digest == RC7_PATCHED_SHA256 and RC7_MARKER.encode() in original:
        return original
    if source_digest not in {ORIGINAL_SHA256, OLD_PATCHED_SHA256}:
        raise RuntimeError("Dinkum listener source differs from the reviewed 0.10.5a1 file")
    text = original.decode("utf-8")
    already_guarded = source_digest == OLD_PATCHED_SHA256
    if not already_guarded:
        text = text.replace(
            "from threading import Thread, RLock, Event",
            "from threading import Thread, RLock, Event, Timer",
            1,
        )
        text = text.replace(
            "        self._default_vol = 70  # for barge-in\n",
            "        self._default_vol = 70  # for barge-in\n"
            "        self._barge_restore_timer = None\n"
            "        self._barge_volume_lowered = False\n",
            1,
        )
    old_begin = '''    def _record_begin(self):
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
    new_begin = '''    def _restore_fake_barge_volume(self):
        # Jarvis fake-barge-in safety timeout: STT failure must not leave the
        # desktop at the temporary recording volume.
        timer = self._barge_restore_timer
        self._barge_restore_timer = None
        if timer is not None:
            timer.cancel()
        if not self._barge_volume_lowered:
            return
        self._barge_volume_lowered = False
        LOG.info(f"fake barge-in restoring volume to: {self._default_vol}")
        self.bus.emit(
            Message(
                "mycroft.volume.set",
                {"percent": self._default_vol / 100, "play_sound": False},
                {"skill_id": "dinkum-listener"},
            )
        )

    def _record_begin(self):
        LOG.debug("Record begin")
        if self.fake_barge_in:
            if self._barge_restore_timer is not None:
                self._barge_restore_timer.cancel()
            self._barge_volume_lowered = True
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
            self._barge_restore_timer = Timer(15, self._restore_fake_barge_volume)
            self._barge_restore_timer.daemon = True
            self._barge_restore_timer.start()
        self.bus.emit(Message(SpecMessage.LISTENER_RECORD_STARTED))
'''
    if not already_guarded:
        if old_begin not in text:
            raise RuntimeError("Reviewed record-begin block was not found")
        text = text.replace(old_begin, new_begin, 1)
    old_end = '''    def _record_end_signal(self):
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
    new_end = '''    def _record_end_signal(self):
        LOG.debug("Record end")
        if self.fake_barge_in:
            self._restore_fake_barge_volume()
        self.bus.emit(Message(SpecMessage.LISTENER_RECORD_ENDED))
'''
    if not already_guarded:
        if old_end not in text:
            raise RuntimeError("Reviewed record-end block was not found")
        text = text.replace(old_end, new_end, 1)

    text = text.replace(
        "        self._barge_restore_timer = None\n"
        "        self._barge_volume_lowered = False\n",
        "        self._barge_restore_timer = None\n"
        "        self._barge_lower_timer = None\n"
        "        self._barge_volume_lowered = False\n",
        1,
    )
    guarded_begin = '''    def _restore_fake_barge_volume(self):
        # Jarvis fake-barge-in safety timeout: STT failure must not leave the
        # desktop at the temporary recording volume.
        timer = self._barge_restore_timer
        self._barge_restore_timer = None
        if timer is not None:
            timer.cancel()
        if not self._barge_volume_lowered:
            return
        self._barge_volume_lowered = False
        LOG.info(f"fake barge-in restoring volume to: {self._default_vol}")
        self.bus.emit(
            Message(
                "mycroft.volume.set",
                {"percent": self._default_vol / 100, "play_sound": False},
                {"skill_id": "dinkum-listener"},
            )
        )

    def _record_begin(self):
        LOG.debug("Record begin")
        if self.fake_barge_in:
            if self._barge_restore_timer is not None:
                self._barge_restore_timer.cancel()
            self._barge_volume_lowered = True
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
            self._barge_restore_timer = Timer(15, self._restore_fake_barge_volume)
            self._barge_restore_timer.daemon = True
            self._barge_restore_timer.start()
        self.bus.emit(Message(SpecMessage.LISTENER_RECORD_STARTED))
'''
    audible_begin = '''    def _lower_fake_barge_volume(self):
        # Jarvis audible cue and fake-barge safety: give the 0.11-second
        # listening cue (including its configured lead-in) time to play before
        # lowering other playback. Confirmation state excludes the cue from STT.
        self._barge_lower_timer = None
        if self._barge_volume_lowered or not self.fake_barge_in:
            return
        self._barge_volume_lowered = True
        LOG.info(f"fake barge-in lowering volume to: {self.fake_barge_in_volume}")
        self.bus.emit(
            Message(
                "mycroft.volume.set",
                {"percent": self.fake_barge_in_volume / 100, "play_sound": False},
                {"skill_id": "dinkum-listener"},
            )
        )
        self._barge_restore_timer = Timer(15, self._restore_fake_barge_volume)
        self._barge_restore_timer.daemon = True
        self._barge_restore_timer.start()

    def _restore_fake_barge_volume(self):
        # STT failure must not leave the desktop at the temporary volume.
        lower_timer = self._barge_lower_timer
        self._barge_lower_timer = None
        if lower_timer is not None:
            lower_timer.cancel()
        timer = self._barge_restore_timer
        self._barge_restore_timer = None
        if timer is not None:
            timer.cancel()
        if not self._barge_volume_lowered:
            return
        self._barge_volume_lowered = False
        LOG.info(f"fake barge-in restoring volume to: {self._default_vol}")
        self.bus.emit(
            Message(
                "mycroft.volume.set",
                {"percent": self._default_vol / 100, "play_sound": False},
                {"skill_id": "dinkum-listener"},
            )
        )

    def _record_begin(self):
        LOG.debug("Record begin")
        if self.fake_barge_in:
            if self._barge_lower_timer is not None:
                self._barge_lower_timer.cancel()
            if self._barge_restore_timer is not None:
                self._barge_restore_timer.cancel()
            if self._barge_volume_lowered:
                # A repeated trigger during capture stays ducked but receives
                # a fresh safety deadline.
                self._barge_restore_timer = Timer(15, self._restore_fake_barge_volume)
                self._barge_restore_timer.daemon = True
                self._barge_restore_timer.start()
            else:
                self._barge_lower_timer = Timer(0.35, self._lower_fake_barge_volume)
                self._barge_lower_timer.daemon = True
                self._barge_lower_timer.start()
        self.bus.emit(Message(SpecMessage.LISTENER_RECORD_STARTED))
'''
    if guarded_begin not in text:
        raise RuntimeError("Reviewed guarded record-begin block was not found")
    return text.replace(guarded_begin, audible_begin, 1).encode("utf-8")


def rc8_source(original: bytes) -> bytes:
    """Return the event-driven service patch from a reviewed source revision."""
    source_digest = digest(original)
    if source_digest == RC8_PATCHED_SHA256 and MARKER.encode() in original:
        return original
    if source_digest == RC7_PATCHED_SHA256:
        rc7 = original
    else:
        rc7 = rc7_source(original)
    text = rc7.decode("utf-8")
    text = text.replace(
        "        self._barge_lower_timer = None\n"
        "        self._barge_volume_lowered = False\n",
        "        self._barge_lower_timer = None\n"
        "        self._barge_cue_timer = None\n"
        "        self._barge_waiting_for_cue = False\n"
        "        self._barge_volume_lowered = False\n",
        1,
    )
    old_begin = '''    def _lower_fake_barge_volume(self):
        # Jarvis audible cue and fake-barge safety: give the 0.11-second
        # listening cue (including its configured lead-in) time to play before
        # lowering other playback. Confirmation state excludes the cue from STT.
        self._barge_lower_timer = None
        if self._barge_volume_lowered or not self.fake_barge_in:
            return
        self._barge_volume_lowered = True
        LOG.info(f"fake barge-in lowering volume to: {self.fake_barge_in_volume}")
        self.bus.emit(
            Message(
                "mycroft.volume.set",
                {"percent": self.fake_barge_in_volume / 100, "play_sound": False},
                {"skill_id": "dinkum-listener"},
            )
        )
        self._barge_restore_timer = Timer(15, self._restore_fake_barge_volume)
        self._barge_restore_timer.daemon = True
        self._barge_restore_timer.start()

    def _restore_fake_barge_volume(self):
        # STT failure must not leave the desktop at the temporary volume.
        lower_timer = self._barge_lower_timer
        self._barge_lower_timer = None
        if lower_timer is not None:
            lower_timer.cancel()
        timer = self._barge_restore_timer
        self._barge_restore_timer = None
        if timer is not None:
            timer.cancel()
        if not self._barge_volume_lowered:
            return
        self._barge_volume_lowered = False
        LOG.info(f"fake barge-in restoring volume to: {self._default_vol}")
        self.bus.emit(
            Message(
                "mycroft.volume.set",
                {"percent": self._default_vol / 100, "play_sound": False},
                {"skill_id": "dinkum-listener"},
            )
        )

    def _record_begin(self):
        LOG.debug("Record begin")
        if self.fake_barge_in:
            if self._barge_lower_timer is not None:
                self._barge_lower_timer.cancel()
            if self._barge_restore_timer is not None:
                self._barge_restore_timer.cancel()
            if self._barge_volume_lowered:
                # A repeated trigger during capture stays ducked but receives
                # a fresh safety deadline.
                self._barge_restore_timer = Timer(15, self._restore_fake_barge_volume)
                self._barge_restore_timer.daemon = True
                self._barge_restore_timer.start()
            else:
                self._barge_lower_timer = Timer(0.35, self._lower_fake_barge_volume)
                self._barge_lower_timer.daemon = True
                self._barge_lower_timer.start()
        self.bus.emit(Message(SpecMessage.LISTENER_RECORD_STARTED))
'''
    new_begin = '''    def _lower_fake_barge_volume(self):
        # Jarvis cue-completion and fake-barge safety: duck only after the audio
        # service confirms that the listening cue has finished.
        self._barge_lower_timer = None
        if self._barge_volume_lowered or not self.fake_barge_in:
            return
        self._barge_volume_lowered = True
        LOG.info(f"fake barge-in lowering volume to: {self.fake_barge_in_volume}")
        self.bus.emit(
            Message(
                "mycroft.volume.set",
                {"percent": self.fake_barge_in_volume / 100, "play_sound": False},
                {"skill_id": "dinkum-listener"},
            )
        )
        self._barge_restore_timer = Timer(15, self._restore_fake_barge_volume)
        self._barge_restore_timer.daemon = True
        self._barge_restore_timer.start()

    def _finish_listening_cue(self):
        timer = self._barge_cue_timer
        self._barge_cue_timer = None
        if timer is not None:
            timer.cancel()
        if not self._barge_waiting_for_cue:
            return
        self._barge_waiting_for_cue = False
        self._lower_fake_barge_volume()
        if self.voice_loop.state == ListeningState.CONFIRMATION:
            self.voice_loop.state = ListeningState.BEFORE_COMMAND

    def _restore_fake_barge_volume(self):
        # STT failure must not leave the desktop at the temporary volume.
        cue_timer = self._barge_cue_timer
        self._barge_cue_timer = None
        if cue_timer is not None:
            cue_timer.cancel()
        self._barge_waiting_for_cue = False
        lower_timer = self._barge_lower_timer
        self._barge_lower_timer = None
        if lower_timer is not None:
            lower_timer.cancel()
        timer = self._barge_restore_timer
        self._barge_restore_timer = None
        if timer is not None:
            timer.cancel()
        if not self._barge_volume_lowered:
            return
        self._barge_volume_lowered = False
        LOG.info(f"fake barge-in restoring volume to: {self._default_vol}")
        self.bus.emit(
            Message(
                "mycroft.volume.set",
                {"percent": self._default_vol / 100, "play_sound": False},
                {"skill_id": "dinkum-listener"},
            )
        )

    def _record_begin(self):
        LOG.debug("Record begin")
        if self._barge_volume_lowered:
            # A repeated trigger must restore normal volume for its own cue.
            self._restore_fake_barge_volume()
        else:
            if self._barge_cue_timer is not None:
                self._barge_cue_timer.cancel()
            if self._barge_restore_timer is not None:
                self._barge_restore_timer.cancel()
        sound = self.config.get("sounds", {}).get("start_listening")
        self._barge_waiting_for_cue = bool(
            self.config.get("confirm_listening") and sound
        )
        if self._barge_waiting_for_cue:
            # The response event is authoritative. This timer is only a
            # bounded recovery path if the audio service never responds.
            self._barge_cue_timer = Timer(3, self._finish_listening_cue)
            self._barge_cue_timer.daemon = True
            self._barge_cue_timer.start()
        elif self.fake_barge_in:
            self._lower_fake_barge_volume()
        self.bus.emit(Message(SpecMessage.LISTENER_RECORD_STARTED))
'''
    if old_begin not in text:
        raise RuntimeError("Reviewed rc7 record-begin block was not found")
    text = text.replace(old_begin, new_begin, 1)
    text = text.replace(RC7_MARKER, MARKER, 1)
    old_sound = '''    def _handle_sound_played(self, message: Message):
        """Handle response message from audio service."""
        if not self._validate_message_context(message) or not self.voice_loop.running:
            # ignore this sound, it is targeted to an external client
            return
        if self.voice_loop.state == ListeningState.CONFIRMATION:
            self.voice_loop.state = ListeningState.BEFORE_COMMAND
'''
    new_sound = '''    def _handle_sound_played(self, message: Message):
        """Handle response message from audio service."""
        if not self._validate_message_context(message) or not self.voice_loop.running:
            # ignore this sound, it is targeted to an external client
            return
        if (self.voice_loop.state == ListeningState.CONFIRMATION
                and self._barge_waiting_for_cue):
            self._finish_listening_cue()
'''
    if old_sound not in text:
        raise RuntimeError("Reviewed sound-completion handler was not found")
    return text.replace(old_sound, new_sound, 1).encode("utf-8")


def rc9_source(original: bytes) -> bytes:
    """Add a fresh, fail-closed volume snapshot to the cue-completion guard."""
    source_digest = digest(original)
    if source_digest == RC9_PATCHED_SHA256 and RC9_MARKER.encode() in original:
        return original
    if source_digest == RC8_PATCHED_SHA256:
        rc8 = original
    else:
        rc8 = rc8_source(original)
    text = rc8.decode("utf-8")
    text = text.replace(
        "        self._barge_waiting_for_cue = False\n"
        "        self._barge_volume_lowered = False\n",
        "        self._barge_waiting_for_cue = False\n"
        "        self._barge_volume_snapshot_valid = False\n"
        "        self._barge_volume_lowered = False\n",
        1,
    )
    old_query = '''    def _query_volume(self):
        """get the default volume"""
        response = self.bus.wait_for_response(Message("mycroft.volume.get"))
        if response:
            self._default_vol = int(response.data["percent"] * 100)
'''
    new_query = '''    def _query_volume(self):
        """Snapshot the real sink volume immediately before one capture."""
        response = self.bus.wait_for_response(
            Message("mycroft.volume.get"), timeout=0.5
        )
        if not response or "percent" not in response.data:
            LOG.warning("fake barge-in skipped: current volume is unavailable")
            return False
        self._default_vol = int(round(response.data["percent"] * 100))
        return True
'''
    if old_query not in text:
        raise RuntimeError("Reviewed volume-query block was not found")
    text = text.replace(old_query, new_query, 1)
    text = text.replace(
        "        self._barge_waiting_for_cue = False\n"
        "        self._lower_fake_barge_volume()\n",
        "        self._barge_waiting_for_cue = False\n"
        "        if self._barge_volume_snapshot_valid:\n"
        "            self._lower_fake_barge_volume()\n",
        1,
    )
    text = text.replace(
        "        if self._barge_volume_lowered:\n"
        "            # A repeated trigger must restore normal volume for its own cue.\n",
        "        restored_active_duck = self._barge_volume_lowered\n"
        "        if restored_active_duck:\n"
        "            # A repeated trigger must restore normal volume for its own cue.\n",
        1,
    )
    text = text.replace(
        "        sound = self.config.get(\"sounds\", {}).get(\"start_listening\")\n"
        "        self._barge_waiting_for_cue = bool(\n",
        "        self._barge_volume_snapshot_valid = (\n"
        "            not self.fake_barge_in\n"
        "            or (not restored_active_duck and self._query_volume())\n"
        "        )\n"
        "        sound = self.config.get(\"sounds\", {}).get(\"start_listening\")\n"
        "        self._barge_waiting_for_cue = bool(\n",
        1,
    )
    text = text.replace(
        "        elif self.fake_barge_in:\n"
        "            self._lower_fake_barge_volume()\n",
        "        elif self.fake_barge_in and self._barge_volume_snapshot_valid:\n"
        "            self._lower_fake_barge_volume()\n",
        1,
    )
    required = (
        "self._barge_volume_snapshot_valid = (",
        "not restored_active_duck and self._query_volume()",
        "if self._barge_volume_snapshot_valid:",
        'timeout=0.5',
    )
    if not all(item in text for item in required):
        raise RuntimeError("Reviewed fresh-volume snapshot points were not found")
    return text.encode("utf-8")


def patched_source(original: bytes) -> bytes:
    """Keep cue-volume safety without delaying microphone capture."""
    source_digest = digest(original)
    if source_digest == PATCHED_SHA256 and MARKER.encode() in original:
        return original
    if source_digest == RC9_PATCHED_SHA256:
        rc9 = original
    else:
        rc9 = rc9_source(original)
    text = rc9.decode("utf-8")
    old = '''    def _handle_sound_played(self, message: Message):
        """Handle response message from audio service."""
        if not self._validate_message_context(message) or not self.voice_loop.running:
            # ignore this sound, it is targeted to an external client
            return
        if (self.voice_loop.state == ListeningState.CONFIRMATION
                and self._barge_waiting_for_cue):
            self._finish_listening_cue()
'''
    new = '''    def _handle_sound_played(self, message: Message):
        """Handle response message from audio service."""
        if not self._validate_message_context(message) or not self.voice_loop.running:
            # ignore this sound, it is targeted to an external client
            return
        # Jarvis nonblocking cue and fake-barge safety: cue completion controls
        # only background-volume ducking. The upstream voice loop independently
        # advances microphone capture, so prompted follow-ups cannot be clipped
        # by a delayed audio-service response.
        if self._barge_waiting_for_cue:
            self._finish_listening_cue()
'''
    if old not in text:
        raise RuntimeError("Reviewed cue-completion handler was not found")
    text = text.replace(old, new, 1)
    text = text.replace(RC9_MARKER, MARKER)
    return text.encode("utf-8")


def patched_voice_loop(original: bytes) -> bytes:
    """Restore upstream confirmation timing if the rejected gate is present."""
    source_digest = digest(original)
    if source_digest == VOICE_LOOP_ORIGINAL_SHA256:
        return original
    if source_digest != VOICE_LOOP_GATED_SHA256:
        raise RuntimeError("Dinkum voice loop differs from the reviewed 0.10.5a1 file")
    text = original.decode("utf-8")
    gated = '''    def _confirmation_sound(self, chunk: bytes):
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
'''
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
'''
    if gated not in text:
        raise RuntimeError("Reviewed rejected confirmation gate was not found")
    return text.replace(gated, upstream, 1).encode("utf-8")


def atomic_write(path: Path, data: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".new", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        temporary.chmod(path.stat().st_mode & 0o777)
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    installed = importlib.metadata.version("ovos-dinkum-listener")
    if installed != VERSION:
        raise RuntimeError(f"Expected ovos-dinkum-listener {VERSION}; found {installed}")
    service_path, voice_loop_path = source_paths()
    originals = {
        service_path: service_path.read_bytes(),
        voice_loop_path: voice_loop_path.read_bytes(),
    }
    updates = {
        service_path: patched_source(originals[service_path]),
        voice_loop_path: patched_voice_loop(originals[voice_loop_path]),
    }
    if args.check:
        print("PASS: reviewed listener keeps capture nonblocking and restores volume safely.")
        return 0
    if updates == originals:
        print("Listener nonblocking cue and volume guard is already installed.")
        return 0
    state = Path.home() / ".local/state/jarvis/listener-safety"
    backup = state / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup.mkdir(parents=True, mode=0o700)
    shutil.copy2(service_path, backup / "service.py")
    shutil.copy2(voice_loop_path, backup / "voice_loop.py")
    temporary = backup / "compile"
    temporary.mkdir(mode=0o700)
    for path, data in updates.items():
        candidate = temporary / path.name
        candidate.write_bytes(data)
        py_compile.compile(str(candidate), doraise=True)
    written = []
    try:
        for path, data in updates.items():
            if data != originals[path]:
                atomic_write(path, data)
                written.append(path)
    except BaseException:
        for path in reversed(written):
            atomic_write(path, originals[path])
        raise
    print(f"Installed listener nonblocking cue and volume guard. Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
