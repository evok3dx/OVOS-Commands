#!/usr/bin/env python3
"""Atomically configure Jarvis's reviewed local OVOS audio stack."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path


STT_MODULE = "ovos-stt-plugin-fasterwhisper"
TTS_MODULE = "ovos-tts-plugin-phoonnx"
VAD_MODULE = "ovos-vad-plugin-silero"
BELLA_VOICE = "kokoro/af_bella"


def load_config(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("OVOS configuration root must be a JSON object")
    return value


def configure(config: dict[str, object], listening_sound: Path) -> dict[str, object]:
    listener = config.setdefault("listener", {})
    sounds = config.setdefault("sounds", {})
    if not isinstance(listener, dict) or not isinstance(sounds, dict):
        raise ValueError("OVOS listener and sounds settings must be JSON objects")

    listener.update({
        "instant_listen": True,
        "fake_barge_in": True,
        "barge_in_delay": 0.25,
        "barge_in_volume": 15,
        "VAD": {"module": VAD_MODULE},
    })
    config["stt"] = {
        "module": STT_MODULE,
        STT_MODULE: {
            "model": "small.en",
            "use_cuda": False,
            "compute_type": "int8",
            "beam_size": 1,
            "cpu_threads": 8,
        },
    }
    config["tts"] = {
        "module": TTS_MODULE,
        TTS_MODULE: {
            "voice": BELLA_VOICE,
        },
    }
    sounds["start_listening"] = str(listening_sound)
    config["play_wav_cmdline"] = "play %1 pad 0.15 0.25"
    config["play_mp3_cmdline"] = "play %1 pad 0.15 0.25"
    return config


def atomic_write(path: Path, config: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".new", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(config, output, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        temporary.chmod(mode)
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path,
        default=Path.home() / ".config/mycroft/mycroft.conf",
    )
    parser.add_argument(
        "--listening-sound", type=Path,
        default=Path.home() / ".local/share/ovos/sounds/jarvis-ready.wav",
    )
    args = parser.parse_args()
    if not args.listening_sound.is_file():
        parser.error(f"listening sound is missing: {args.listening_sound}")
    atomic_write(args.config, configure(load_config(args.config), args.listening_sound))
    print("Configured local Faster Whisper STT, Silero VAD, Bella voice and listening beep.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
