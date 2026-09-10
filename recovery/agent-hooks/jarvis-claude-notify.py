#!/usr/bin/python3

import hashlib
import json
import os
import sys
from pathlib import Path


PRIVATE_STATE = (
    Path.home() /
    ".local/state/jarvis/claude-latest.json"
)

SPEECH_SPOOL = Path(
    "/var/spool/jarvis-responses/claude/latest.json"
)


def write_json(path, data, mode):
    temporary = path.with_suffix(".tmp")

    temporary.write_text(
        json.dumps(data, ensure_ascii=False),
        encoding="utf-8"
    )

    os.chmod(temporary, mode)
    temporary.replace(path)


def main():
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError):
        return 0

    if event.get("hook_event_name") != "Stop":
        return 0

    if event.get("background_tasks"):
        return 0

    if event.get("session_crons"):
        return 0

    message = event.get(
        "last_assistant_message",
        ""
    )

    if not isinstance(message, str):
        return 0

    message = message.strip()

    if not message:
        return 0

    session_id = str(
        event.get("session_id", "")
    )

    identifier = hashlib.sha256(
        (session_id + "\0" + message).encode("utf-8")
    ).hexdigest()

    output = {
        "source": "claude",
        "session_id": session_id,
        "turn_id": identifier,
        "message": message
    }

    write_json(
        PRIVATE_STATE,
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
