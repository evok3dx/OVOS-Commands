#!/usr/bin/env python3
"""Disable optional Persona routing without removing models or packages."""

import json
import shutil
from datetime import datetime
from pathlib import Path


CONFIG = Path.home() / ".config/mycroft/mycroft.conf"


def main():
    if not CONFIG.is_file():
        raise SystemExit(f"Configuration not found: {CONFIG}")

    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    intents = data.setdefault("intents", {})
    pipeline = intents.get("pipeline", [])

    if isinstance(pipeline, list):
        intents["pipeline"] = [
            item for item in pipeline
            if "persona" not in str(item).lower()
        ]

    persona = intents.setdefault("persona", {})
    persona["handle_fallback"] = False
    persona["ignore_plugin_personas"] = True

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = CONFIG.with_name(f"{CONFIG.name}.before-command-only-{stamp}")
    shutil.copy2(CONFIG, backup)

    temporary = CONFIG.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8"
    )
    temporary.chmod(0o600)
    temporary.replace(CONFIG)

    print(f"Updated: {CONFIG}")
    print(f"Backup:  {backup}")
    print("Conversation add-on disabled. Restart ovos-core.service to apply.")


if __name__ == "__main__":
    main()
