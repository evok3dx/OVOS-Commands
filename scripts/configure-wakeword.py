#!/usr/bin/env python3
"""Atomically configure the reviewed local Jarvis wake word for OVOS."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path


DEFAULT_WAKE_PHRASE = "hey_jarvis"
OPENWAKEWORD_MODULE = "ovos-ww-plugin-openwakeword"
VOSK_MODULE = "ovos-ww-plugin-vosk"
MANAGED_MODULES = {OPENWAKEWORD_MODULE, VOSK_MODULE}


def load_config(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("OVOS configuration root must be a JSON object")
    return value


def configure(
    config: dict[str, object],
    wake_phrase: str,
    spoken_phrase: str | None = None,
    previous_phrase: str | None = None,
) -> dict[str, object]:
    listener = config.setdefault("listener", {})
    hotwords = config.setdefault("hotwords", {})
    if not isinstance(listener, dict) or not isinstance(hotwords, dict):
        raise ValueError("OVOS listener and hotwords settings must be JSON objects")

    if previous_phrase and previous_phrase != wake_phrase:
        previous = hotwords.get(previous_phrase)
        if isinstance(previous, dict) and previous.get("module") in MANAGED_MODULES:
            hotwords.pop(previous_phrase)

    spoken_phrase = spoken_phrase or wake_phrase.replace("_", " ")
    listener["wake_word"] = wake_phrase
    if wake_phrase == DEFAULT_WAKE_PHRASE and spoken_phrase == "hey jarvis":
        # The reviewed OpenWakeWord plugin resolves its built-in trained model
        # when no explicit model path is supplied. Arbitrary typed phrases do
        # not have trained OpenWakeWord models and therefore use Vosk below.
        hotwords[wake_phrase] = {
            "module": OPENWAKEWORD_MODULE,
            "listen": True,
            "threshold": 0.5,
        }
    else:
        hotwords[wake_phrase] = {
            "module": VOSK_MODULE,
            "listen": True,
            "full_vocab": False,
            "rule": "fuzzy",
            "samples": [spoken_phrase],
            "time_between_checks": 0.2,
        }
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
        "--config",
        type=Path,
        default=Path.home() / ".config/mycroft/mycroft.conf",
    )
    parser.add_argument("--wake-phrase", default=DEFAULT_WAKE_PHRASE)
    parser.add_argument("--spoken-phrase")
    parser.add_argument("--previous-phrase")
    args = parser.parse_args()

    if not args.wake_phrase or not all(
        character.isalnum() or character == "_" for character in args.wake_phrase
    ):
        parser.error("wake phrase must contain only letters, numbers and underscores")

    config = configure(
        load_config(args.config),
        args.wake_phrase,
        args.spoken_phrase,
        args.previous_phrase,
    )
    atomic_write(args.config, config)
    print(f"Configured OVOS wake phrase: {args.wake_phrase.replace('_', ' ')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
