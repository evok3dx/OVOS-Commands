#!/usr/bin/env python3
"""Select the reviewed PipeWire-friendly OVOS microphone without losing config."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path


SOUNDDEVICE = "ovos-microphone-plugin-sounddevice"
ALSA = "ovos-microphone-plugin-alsa"


def load_config(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("OVOS configuration root must be a JSON object")
    return value


def configure(config: dict[str, object], *, force: bool = False) -> bool:
    """Use SoundDevice with ALSA fallback; preserve an explicit user policy."""
    listener = config.setdefault("listener", {})
    if not isinstance(listener, dict):
        raise ValueError("OVOS listener settings must be a JSON object")
    current = listener.get("microphone")
    if current is not None and not isinstance(current, dict):
        raise ValueError("OVOS microphone settings must be a JSON object")
    if not force and current and isinstance(current.get("module"), str):
        return False
    listener["microphone"] = {
        "module": SOUNDDEVICE,
        SOUNDDEVICE: {"fallback_module": ALSA},
        ALSA: {},
    }
    return True


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
        "--force", action="store_true",
        help="replace an explicit microphone policy after user approval",
    )
    args = parser.parse_args()
    config = load_config(args.config)
    if configure(config, force=args.force):
        atomic_write(args.config, config)
        print("Configured SoundDevice microphone with ALSA fallback.")
    else:
        print("Preserved the existing explicit microphone configuration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
