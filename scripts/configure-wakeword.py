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
    onnx_model: Path | None = None,
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
        # Preserve the reviewed ONNX engine and bind its verified model in the
        # final venv; a dependency repair must not silently change engines.
        if onnx_model is None or not onnx_model.is_file() or "hey_jarvis" not in onnx_model.name or onnx_model.suffix != ".onnx":
            raise ValueError("A verified Hey Jarvis ONNX model is required")
        hotwords[wake_phrase] = {
            "module": OPENWAKEWORD_MODULE,
            "listen": True,
            "threshold": 0.4,
            "models": [str(onnx_model)],
            "inference_framework": "onnx",
        }
        listener["vad_pre_wake_enabled"] = False
        config["confirm_listening"] = True
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


def ensure_default_onnx(config: dict[str, object], onnx_model: Path) -> dict[str, object]:
    """Repair the released Jarvis default; retain custom wake engines/models."""
    if not onnx_model.is_file() or "hey_jarvis" not in onnx_model.name or onnx_model.suffix != ".onnx":
        raise ValueError("A verified Hey Jarvis ONNX model is required")
    listener = config.get("listener", {})
    hotwords = config.get("hotwords", {})
    if not isinstance(listener, dict) or not isinstance(hotwords, dict):
        raise ValueError("OVOS listener and hotwords settings must be objects")
    if listener.get("wake_word") != DEFAULT_WAKE_PHRASE:
        return config  # Custom Vosk/model setup belongs to this machine.
    current = hotwords.get(DEFAULT_WAKE_PHRASE)
    if not isinstance(current, dict) or current.get("module") != OPENWAKEWORD_MODULE:
        raise ValueError("The existing Hey Jarvis wake engine needs manual review")
    models = current.get("models")
    if models:
        if (not isinstance(models, list) or len(models) != 1
                or not isinstance(models[0], str)
                or not models[0].endswith(".onnx")
                or "hey_jarvis" not in Path(models[0]).name
                or current.get("inference_framework") != "onnx"
                or not Path(models[0]).is_file()):
            raise ValueError("The existing custom Hey Jarvis model needs manual review")
    if current.get("inference_framework") not in (None, "onnx"):
        raise ValueError("The existing Hey Jarvis framework needs manual review")
    threshold = current.get("threshold", 0.5)
    if threshold not in (0.4, 0.5):
        raise ValueError("The existing custom Hey Jarvis threshold needs manual review")
    current["listen"] = True
    current["threshold"] = 0.4
    current["models"] = [str(onnx_model)]
    current["inference_framework"] = "onnx"
    listener["vad_pre_wake_enabled"] = False
    config["confirm_listening"] = True
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
    parser.add_argument("--onnx-model", type=Path)
    parser.add_argument("--ensure-default-onnx", action="store_true",
                        help="repair the original default only, preserving existing wake settings")
    args = parser.parse_args()

    if not args.wake_phrase or not all(
        character.isalnum() or character == "_" for character in args.wake_phrase
    ):
        parser.error("wake phrase must contain only letters, numbers and underscores")

    source = load_config(args.config)
    before = json.dumps(source, sort_keys=True)
    if args.ensure_default_onnx:
        if args.onnx_model is None:
            parser.error("--ensure-default-onnx requires --onnx-model")
        config = ensure_default_onnx(source, args.onnx_model)
    else:
        config = configure(
            source, args.wake_phrase, args.spoken_phrase,
            args.previous_phrase, args.onnx_model,
        )
    if args.ensure_default_onnx and json.dumps(config, sort_keys=True) == before:
        print("Existing OVOS wake configuration was preserved.")
        return 0
    atomic_write(args.config, config)
    print(f"Configured OVOS wake phrase: {args.wake_phrase.replace('_', ' ')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
