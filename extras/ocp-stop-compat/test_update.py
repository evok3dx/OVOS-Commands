#!/usr/bin/env python3
"""Offline tests for the reviewed Common Play STOP-1 repair."""

import importlib.util
from pathlib import Path
import tempfile
from unittest.mock import patch


root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ocp_stop_compat", root / "install.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

fixture = b'''from ovos_utils.ocp import PlayerState

class OCPMediaPlayer:
    def stop(self):
        """
        Request stopping current playback and searching
        """
        return True
'''

with patch.object(module, "digest", return_value=module.ORIGINAL_SHA256):
    updated = module.patched_source(fixture)
text = updated.decode()
assert module.MARKER in text
assert "return self.state in {PlayerState.PLAYING, PlayerState.PAUSED}" in text
assert module.patched_source(updated) == updated

with tempfile.TemporaryDirectory() as directory:
    target = Path(directory) / "player.py"
    target.write_text("value = 1\n", encoding="utf-8")
    module.atomic_write(target, b"value = 2\n")
    assert target.read_text(encoding="utf-8") == "value = 2\n"
    assert list(Path(directory).iterdir()) == [target]

try:
    module.patched_source(b"unknown source")
except RuntimeError as error:
    assert "differs from the reviewed" in str(error)
else:
    raise AssertionError("Unknown Common Play source was accepted")

print("PASS: Common Play repair is exact, idempotent and rejects unknown source")
