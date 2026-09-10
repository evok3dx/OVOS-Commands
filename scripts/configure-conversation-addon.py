#!/usr/bin/env python3
"""Enable an optional loopback-only OVOS Persona conversation layer."""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path


CONFIG = Path.home() / ".config/mycroft/mycroft.conf"
PERSONA_DIR = Path.home() / ".config/ovos_persona"
PERSONA_FILE = PERSONA_DIR / "local-voice-assistant.json"

HIGH = "ovos-persona-pipeline-plugin-high"
LOW = "ovos-persona-pipeline-plugin-low"


def add_once(values, item, before=None):
    values = [value for value in values if value != item]
    if before in values:
        values.insert(values.index(before), item)
    else:
        values.append(item)
    return values


def main():
    if not CONFIG.is_file():
        raise SystemExit(f"Configuration not found: {CONFIG}")

    model = os.environ.get("JARVIS_MODEL", "voice-assistant").strip()
    if not model:
        raise SystemExit("JARVIS_MODEL cannot be empty")

    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    intents = data.setdefault("intents", {})
    pipeline = intents.setdefault("pipeline", [])
    if not isinstance(pipeline, list):
        raise SystemExit("intents.pipeline must be a list")

    pipeline = add_once(
        pipeline,
        HIGH,
        "ovos-padatious-pipeline-plugin-high"
    )
    pipeline = add_once(
        pipeline,
        LOW,
        "ovos-common-query-pipeline-plugin"
    )
    intents["pipeline"] = pipeline
    intents["persona"] = {
        "handle_fallback": True,
        "default_persona": "Local Voice Assistant",
        "ignore_plugin_personas": True
    }

    persona = {
        "name": "Local Voice Assistant",
        "ovos-solver-openai-plugin": {
            "api_url": "http://127.0.0.1:11434/v1",
            "key": "ollama-local",
            "max_tokens": 100,
            "model": model,
            "system_prompt": (
                "Respond in the same language as the user. Answer directly "
                "in one or two short natural sentences unless more detail "
                "is explicitly requested. Use plain spoken language without "
                "markdown, lists, emojis or introductory filler. Never claim "
                "that a computer action succeeded unless a dedicated command "
                "skill completed it."
            ),
            "temperature": 0.2,
            "top_p": 0.8
        },
        "solvers": ["ovos-solver-openai-plugin"]
    }

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = CONFIG.with_name(f"{CONFIG.name}.before-conversation-{stamp}")
    shutil.copy2(CONFIG, backup)

    temporary = CONFIG.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8"
    )
    temporary.chmod(0o600)
    temporary.replace(CONFIG)

    PERSONA_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    persona_tmp = PERSONA_FILE.with_suffix(".tmp")
    persona_tmp.write_text(
        json.dumps(persona, indent=2) + "\n",
        encoding="utf-8"
    )
    persona_tmp.chmod(0o600)
    persona_tmp.replace(PERSONA_FILE)

    print(f"Updated: {CONFIG}")
    print(f"Persona: {PERSONA_FILE}")
    print(f"Backup:  {backup}")
    print("Conversation add-on enabled. Restart ovos-core.service to apply.")


if __name__ == "__main__":
    main()
