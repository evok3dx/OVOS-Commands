#!/usr/bin/env python3
"""Opt-in, local-only setup for the reviewed Jarvis Qwen fallback."""

import argparse
import json
import os
from pathlib import Path
import tempfile
from urllib.error import URLError
from urllib.request import urlopen

MODEL = "qwen3:4b-instruct-2507-q4_K_M"
STAGES = ("jarvis-qwen-pipeline", "jarvis-qwen-chat-pipeline")


def inspect(home: Path):
    config_path = home / ".config/mycroft/mycroft.conf"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        config = {}
    intents = config.get("intents", {})
    if not isinstance(intents, dict):
        intents = {}
    pipeline = intents.get("pipeline", [])
    persona = intents.get("persona", {})
    stages_ready = (isinstance(pipeline, list) and all(stage in pipeline for stage in STAGES)
                    and isinstance(persona, dict) and persona.get("handle_fallback") is False)
    try:
        with urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as response:
            models = json.load(response).get("models", [])
        model_ready = any(isinstance(model, dict) and model.get("name") == MODEL
                          for model in models)
        ollama_ready = True
    except (OSError, URLError, ValueError, KeyError, TypeError):
        ollama_ready = model_ready = False
    settings_path = home / ".config/jarvis/router.json"
    try:
        saved = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    return stages_ready, ollama_ready, model_ready, saved, settings_path


def enable(path: Path, saved: dict):
    if not isinstance(saved, dict) or len(json.dumps(saved)) > 4096:
        raise ValueError("Existing router settings need manual review")
    if saved.get("model") not in (None, MODEL):
        raise ValueError("A different local model is configured; keep those settings and review manually")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or (path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid())):
        raise ValueError("Router settings must be a regular file owned by this user")
    updated = dict(saved, version=1, mode="on", model=MODEL, timeout_seconds=8)
    fd, temporary = tempfile.mkstemp(prefix=".router-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(updated, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description="Check or enable local Jarvis Qwen routing")
    parser.add_argument("--enable", action="store_true", help="enable only if the existing model and OVOS routing are ready")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("run as the desktop user, without sudo")
    stages, ollama, model, saved, path = inspect(Path.home())
    print(f"OVOS Qwen stages: {'ready' if stages else 'not configured'}")
    print(f"Local Ollama: {'available' if ollama else 'unavailable'}")
    print(f"Reviewed {MODEL}: {'installed' if model else 'missing'}")
    print(f"Jarvis fallback: {'enabled' if isinstance(saved, dict) and saved.get('mode') == 'on' else 'off'}")
    if not model:
        print(f"Optional model download: ollama pull {MODEL}")
    if args.enable:
        if not (stages and model):
            parser.error("model and both reviewed pipeline stages must already be available; no settings changed")
        enable(path, saved)
        print("Saved private router settings. Restart Jarvis and test voice routing before relying on it.")


if __name__ == "__main__":
    main()
