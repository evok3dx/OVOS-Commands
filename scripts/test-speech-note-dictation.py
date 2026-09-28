#!/usr/bin/env python3
"""Verify direct Speech Note actions and bounded cold-start fallback."""

import ast
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse(
    (ROOT / "ovos_skill_jarvis_dispatcher/dictation.py").read_text()
)
klass = next(
    node for node in tree.body
    if isinstance(node, ast.ClassDef) and node.name == "DictationActionsMixin"
)
method = next(
    node for node in klass.body
    if isinstance(node, ast.FunctionDef) and node.name == "_speech_note_action"
)
scope = {"subprocess": subprocess}
exec(compile(ast.Module(body=[method], type_ignores=[]), "dictation.py", "exec"), scope)
action = scope["_speech_note_action"]
skill = SimpleNamespace(log=Mock())

with patch.object(subprocess, "run") as run:
    assert action(skill, "start-listening-active-window") is True
assert run.call_count == 1
assert run.call_args.args[0][0] == "/usr/bin/gdbus"
assert run.call_args.args[0][-2:] == ["start-listening-active-window", "{}"]

failure = subprocess.CalledProcessError(1, "gdbus")
with patch.object(subprocess, "run", side_effect=[failure, Mock(returncode=0)]) as run:
    assert action(skill, "start-listening-active-window") is True
assert run.call_count == 2
assert run.call_args_list[1].args[0][:4] == [
    "/usr/bin/flatpak", "run", "net.mkiol.SpeechNote", "--action"
]

with patch.object(subprocess, "run", side_effect=OSError("unavailable")):
    assert action(skill, "start-listening-active-window") is False

print("PASS: Speech Note dictation uses D-Bus first and bounded Flatpak fallback")
