#!/usr/bin/env python3

import json
import os
import pwd
import re
import stat
import subprocess
from pathlib import Path



SOURCE = Path(
    "/var/spool/jarvis-responses/codex/latest.json"
)

EXPECTED_UID = pwd.getpwnam("agent-codex").pw_uid
MAX_FILE_SIZE = 65536
MAX_SPOKEN_CHARACTERS = 6000
MAX_SPOKEN_WORDS = 900


def read_secure_json():
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    descriptor = os.open(SOURCE, flags)

    try:
        information = os.fstat(descriptor)

        if not stat.S_ISREG(information.st_mode):
            raise RuntimeError("Response source is not a regular file")

        if information.st_uid != EXPECTED_UID:
            raise RuntimeError("Response source has the wrong owner")

        if not 0 < information.st_size <= MAX_FILE_SIZE:
            raise RuntimeError("Response source has an invalid size")

        with os.fdopen(
            descriptor,
            "r",
            encoding="utf-8"
        ) as response_file:
            descriptor = -1
            return json.load(response_file)

    finally:
        if descriptor >= 0:
            os.close(descriptor)


def clean_for_speech(message):
    message = message.strip()

    # Search results keep full sources on screen, but speak only
    # the dedicated summary section.
    lines = message.splitlines()
    summary_lines = []
    capturing_summary = False

    for line in lines:
        plain_line = re.sub(r"[#*_`]+", "", line).strip()
        lowered = plain_line.lower()

        if lowered.startswith("spoken summary:"):
            capturing_summary = True
            remainder = plain_line.split(":", 1)[1].strip()

            if remainder:
                summary_lines.append(remainder)

            continue

        if capturing_summary and lowered.startswith("sources:"):
            break

        if capturing_summary:
            summary_lines.append(line)

    if summary_lines:
        message = "\n".join(summary_lines).strip()

    # Phoonnx cannot parse comma-grouped numbers such as 1,000.
    message = re.sub(r"(?<=\d),(?=\d)", "", message)

    if (
        "```" in message
        or len(message) > MAX_SPOKEN_CHARACTERS
        or len(message.split()) > MAX_SPOKEN_WORDS
    ):
        return (
            "Codex has finished. "
            "The response is ready on screen."
        )

    message = re.sub(
        r"\[([^\]]+)\]\([^)]+\)",
        r"\1",
        message
    )
    message = re.sub(
        r"https?://\S+",
        "a link",
        message
    )
    message = re.sub(
        r"[`#*_>~]+",
        " ",
        message
    )
    message = re.sub(
        r"\s+",
        " ",
        message
    ).strip()

    if not message:
        return "Codex has finished."

    return f"Codex says, {message}"


def main():
    if not SOURCE.exists():
        return

    response = read_secure_json()

    if response.get("source") != "codex":
        raise SystemExit("Unexpected response source")

    turn_id = str(response.get("turn_id", "")).strip()
    message = response.get("message", "")

    if not turn_id or not isinstance(message, str):
        raise SystemExit("Invalid response payload")

    spoken_text = clean_for_speech(message)

    subprocess.Popen(
        [
            "/usr/bin/flatpak",
            "run",
            "net.mkiol.SpeechNote",
            "--action",
            "start-reading-text",
            "--text",
            spoken_text
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )


if __name__ == "__main__":
    main()
