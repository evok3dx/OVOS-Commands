"""Bounded media parsing, YouTube lookup, Brave launch and MPRIS control."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys


VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
GENERIC_PLAY = frozenset(("media", "the media", "music", "the music",
                          "this", "this song", "something"))
ACTIONS = frozenset(("play", "pause", "stop", "next", "previous"))


def normalise_query(value: object) -> str:
    query = re.sub(r"\s+", " ", str(value or "")).strip(" ,.?!")
    query = re.sub(r"\s+on\s+youtube$", "", query, flags=re.I).strip()
    if not query or len(query) > 300 or not re.search(r"[A-Za-z0-9]", query):
        raise ValueError("invalid media query")
    return query


def query_from_utterance(value: object) -> str | None:
    """Recognise deliberate title requests without rejecting words in titles."""
    utterance = re.sub(r"\s+", " ", str(value or "")).strip(" ,.?!")
    if not utterance:
        return None
    if re.fullmatch(
        r"(?:(?:can|could|would|will) you\s+)?(?:please\s+)?"
        r"(?:don't|do not|never|not)\s+(?:play|put on|listen to)(?:\s+.*)?",
        utterance, flags=re.I,
    ):
        return None
    patterns = (
        r"(?:(?:can|could|would|will) you\s+)?(?:please\s+)?"
        r"(?:play|put on|listen to)\s*,?\s+(.+?)(?:\s+please)?",
        r"(?:i(?:'d| would) like(?: you)? to\s+)"
        r"(?:play|put on)\s*,?\s+(.+?)(?:\s+please)?",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, utterance, flags=re.I)
        if match:
            query = normalise_query(match.group(1))
            if re.search(
                r"\band\s+(?:open|close|minimi[sz]e|maximi[sz]e|delete|send|write|type)\b",
                query, re.I,
            ):
                return None
            return None if query.casefold() in GENERIC_PLAY else query
    return None


def first_result(payload: str) -> tuple[str, str]:
    data = json.loads(payload)
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        entries = [data] if isinstance(data, dict) else []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        video_id = str(entry.get("id") or "")
        if not VIDEO_ID.fullmatch(video_id):
            url = str(entry.get("url") or entry.get("webpage_url") or "")
            match = re.search(
                r"(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})", url
            )
            video_id = match.group(1) if match else ""
        if VIDEO_ID.fullmatch(video_id):
            title = str(entry.get("title") or "the first result").strip()
            return "https://www.youtube.com/watch?v=" + video_id, title[:200]
    raise ValueError("YouTube returned no playable result")


def search_command(python: str, query: str) -> list[str]:
    executable = str(Path(python).with_name("yt-dlp"))
    prefix = [executable] if Path(executable).is_file() else [python, "-m", "yt_dlp"]
    return [*prefix, "--flat-playlist", "--playlist-end", "1",
            "--dump-single-json", "--no-warnings", "--", "ytsearch1:" + query]


def selected_brave_command(candidates=None) -> list[str]:
    if candidates is None:
        from ovos_skill_jarvis_dispatcher.launcher import discover
        candidates = discover(("brave",))
    candidate = candidates.get("brave") if isinstance(candidates, dict) else None
    argv = candidate.get("argv") if isinstance(candidate, dict) else None
    if not isinstance(argv, list) or not argv or not all(
            isinstance(item, str) and item for item in argv):
        raise RuntimeError("The configured Brave launcher is unavailable")
    return argv


def open_brave(url: str) -> bool:
    from ovos_skill_jarvis_dispatcher.launcher import start_desktop
    return bool(start_desktop([*selected_brave_command(), url]))


def preferred_player(action: str) -> str | None:
    """Prefer the active Brave/Chromium player without hard-coded instance IDs."""
    if action not in ACTIONS:
        raise ValueError("Unsupported media action")
    result = subprocess.run(
        ["/usr/bin/playerctl", "--list-all"], capture_output=True,
        text=True, check=False, timeout=5,
    )
    if result.returncode:
        return None
    players = []
    for value in result.stdout.splitlines()[:64]:
        name = value.strip()
        if (name and len(name) <= 128 and name.isprintable()
                and re.fullmatch(r"[A-Za-z0-9_.:-]+", name)
                and re.match(r"^(?:brave|chromium)(?:\.|$)", name, re.I)):
            players.append(name)
    if not players:
        return None
    preferred = "Paused" if action == "play" else "Playing"
    states = []
    for name in players:
        status = subprocess.run(
            ["/usr/bin/playerctl", "--player", name, "status"],
            capture_output=True, text=True, check=False, timeout=3,
        )
        states.append((name, status.stdout.strip()))
    for name, status in states:
        if status.casefold() == preferred.casefold():
            return name
    for name, status in states:
        if status.casefold() in {"playing", "paused"}:
            return name
    return players[0]


def control(action: str) -> tuple[bool, str | None]:
    if action not in ACTIONS:
        raise ValueError("Unsupported media action")
    player = preferred_player(action)
    command = ["/usr/bin/playerctl"]
    if player:
        command.extend(("--player", player))
    command.append(action)
    result = subprocess.run(command, check=False, timeout=10,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0, player
