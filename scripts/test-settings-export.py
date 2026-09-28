#!/usr/bin/env python3
"""Verify the bounded settings export includes every current Jarvis setting."""

import importlib.util
import json
from pathlib import Path
import stat
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "jarvis_settings_export", ROOT / "scripts/settings_export.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    home = root / "home"
    output = root / "exports"
    output.mkdir()
    fixtures = {
        ".config/jarvis/capabilities.json": '{"mode":"recommended"}\n',
        ".config/jarvis/custom-commands.json": '{"version":1,"phrases":{}}\n',
        ".config/jarvis/listen-shortcut.json": '{"listen_shortcut":"<Super>l"}\n',
        ".config/jarvis/router.json": '{"enabled":true}\n',
        ".config/jarvis/update.json": '{"repository":null}\n',
        ".config/jarvis/reading-normal-speed": "13\n",
        ".config/mycroft/mycroft.conf": '{"listener":{"fake_barge_in_volume":20}}\n',
        ".local/share/ovos/sounds/jarvis-ready.wav": "not real audio",
    }
    for relative, content in fixtures.items():
        path = home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    # Unknown files and transient runtime state must not leak into the archive.
    secret = home / ".config/jarvis/unreviewed-secret.json"
    secret.write_text('{"secret":"do not export"}\n')
    transient = home / ".local/state/jarvis/reading-fast-active"
    transient.parent.mkdir(parents=True, exist_ok=True)
    transient.write_text("temporary\n")

    result = module.export_settings(output, home)
    archive = Path(result["path"])
    assert stat.S_IMODE(archive.stat().st_mode) & 0o077 == 0
    with tarfile.open(archive, "r:gz") as bundle:
        names = set(bundle.getnames())
        expected = {"settings/" + relative for relative in fixtures}
        assert expected <= names, expected - names
        assert "settings/.config/jarvis/unreviewed-secret.json" not in names
        assert "settings/.local/state/jarvis/reading-fast-active" not in names
        manifest = json.load(bundle.extractfile("manifest.json"))
        listed = {entry["path"] for entry in manifest["files"]}
        assert set(fixtures) <= listed

print("PASS: settings export covers current persistent Jarvis settings only")
