#!/usr/bin/env python3
"""Verify Media uses enabled Brave first and Firefox only as fallback."""

from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "plugins/ovos-skill-jarvis-media/ovos_skill_jarvis_media/media.py"
spec = importlib.util.spec_from_file_location("jarvis_media_fallback_test", SOURCE)
media = importlib.util.module_from_spec(spec)
spec.loader.exec_module(media)

URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
CANDIDATES = {
    "brave": {"argv": ["gio", "launch", "brave.desktop"]},
    "firefox": {"argv": ["gio", "launch", "firefox.desktop"]},
}
PROFILE = {"applications": {
    "brave": {"integration": "brave"},
    "firefox": {"integration": "firefox"},
}}

attempts = []
result = media.open_media_url(
    URL, candidates=CANDIDATES, profile=PROFILE,
    starter=lambda command: attempts.append(command) or command[2] == "firefox.desktop",
)
assert result == "firefox"
assert attempts == [
    ["gio", "launch", "brave.desktop", URL],
    ["gio", "launch", "firefox.desktop", URL],
]

attempts.clear()
firefox_only = {"applications": {"firefox": {"integration": "firefox"}}}
result = media.open_media_url(
    URL, candidates=CANDIDATES, profile=firefox_only,
    starter=lambda command: attempts.append(command) or True,
)
assert result == "firefox"
assert attempts == [["gio", "launch", "firefox.desktop", URL]]

print("PASS: Media uses enabled Brave first and Firefox as a bounded fallback")
