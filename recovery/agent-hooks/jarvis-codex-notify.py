#!/usr/bin/python3

import json
import os
import sys
from pathlib import Path


PRIVATE_STATE = (
    Path.home() /
    ".local/state/jarvis"
)

SPEECH_SPOOL = Path(
    "/var/spool/jarvis-responses/codex/latest.json"
)


def write_json(path, data, mode):
    temporary = path.with_suffix(".tmp")

    temporary.write_text(
        json.dumps(data, ensure_ascii=False),
        encoding="utf-8"
    )

    os.chmod(temporary, mode)
    temporary.replace(path)


def is_internal_title(message):
    try:
        content = json.loads(message)
    except (json.JSONDecodeError, TypeError):
        return False

    return (
        isinstance(content, dict)
        and set(content) == {"title"}
        and isinstance(content.get("title"), str)
    )


def main():
    if len(sys.argv) != 2:
        return 0

    try:
        event = json.loads(sys.argv[1])
    except (json.JSONDecodeError, TypeError):
        return 0

    if event.get("type") != "agent-turn-complete":
        return 0

    message = event.get(
        "last-assistant-message",
        ""
    )

    if not isinstance(message, str):
        return 0

    message = message.strip()

    if not message:
        return 0

    output = {
        "source": "codex",
        "type": event.get("type"),
        "thread_id": event.get("thread-id"),
        "turn_id": event.get("turn-id"),
        "message": message
    }

    if is_internal_title(message):
        write_json(
            PRIVATE_STATE /
            "codex-ignored-title.json",
            output,
            0o600
        )
        return 0

    write_json(
        PRIVATE_STATE /
        "codex-latest.json",
        output,
        0o600
    )

    write_json(
        SPEECH_SPOOL,
        output,
        0o640
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
