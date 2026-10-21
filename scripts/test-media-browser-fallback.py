#!/usr/bin/env python3
"""Verify Media uses enabled Brave first and Firefox only as fallback."""

from pathlib import Path
import importlib.util
from unittest.mock import patch


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

for standalone in (False, True):
    with patch.object(media.Path, 'is_file', return_value=standalone):
        query = '--force-ipv6; $(not-a-command)'
        command = media.search_command('/reviewed/bin/python', query)
        assert command[:1 if standalone else 3] == (
            ['/reviewed/bin/yt-dlp'] if standalone else ['/reviewed/bin/python', '-m', 'yt_dlp'])
        assert command.count('--force-ipv4') == 1 and '--force-ipv6' not in command
        assert command[-2:] == ['--', 'ytsearch1:' + query]
        assert command[command.index('--playlist-end') + 1] == '1'
print('PASS: both yt-dlp launch paths use IPv4 and retain an opaque, bounded query argument')
