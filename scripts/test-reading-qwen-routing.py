#!/usr/bin/env python3
"""Offline reading router checks: exact target/speed, no model or desktop needed."""

import ast
import json
import sys
import types
from pathlib import Path
from unittest.mock import Mock, patch


root = Path(__file__).resolve().parents[1]
package = types.ModuleType("ovos_skill_jarvis_dispatcher")
package.__path__ = [str(root / "ovos_skill_jarvis_dispatcher")]
sys.modules[package.__name__] = package

from ovos_skill_jarvis_dispatcher import action_registry, custom_commands, profile, routing_model


configured = profile.resolve_profile({"applications": {}})
catalogue = action_registry.router_catalog(configured)
assert {"reading.selection", "reading.selection_fast", "reading.page",
        "reading.page_fast"} <= catalogue.keys()
assert "reading.last_typed" not in catalogue

# The single tray opens the Commands page; that page must list registered
# phrases under the same 1x/2x actions that will actually run.
inventory = custom_commands.collect_builtin_inventory(configured)
assert "read this at 2x" in inventory["reading.selection_fast"]
assert "read selected text at double speed" in inventory["reading.selection_fast"]
assert "read this page at 2x" in inventory["reading.page_fast"]
assert "read this page" in inventory["reading.page"]
assert "read this at 2x" not in inventory["reading.selection"]

for spoken, expected in (
    ("Could you read this for me?", "reading.selection"),
    ("Please read this at 2x", "reading.selection_fast"),
    ("Read selected text at double speed", "reading.selection_fast"),
    ("Can you read this page at 2x?", "reading.page_fast"),
    ("Please read the page", "reading.page"),
):
    payload, allowed = routing_model.payload_for(spoken, catalogue, configured)
    offered = {action for action in allowed if action.startswith("reading.")}
    assert offered == {expected}, (spoken, offered)
    enum = payload["format"]["properties"]["action"]["enum"]
    assert expected in enum and "none" in enum
    assert "Keep both" in payload["messages"][0]["content"]
    with patch.object(routing_model, "local_json", return_value={
        "done": True, "done_reason": "stop",
        "message": {"content": json.dumps({"action": expected})},
    }):
        assert routing_model.classify(spoken, catalogue, configured)["actual"] == expected

    wrong_speed = expected.removesuffix("_fast") if expected.endswith("_fast") else expected + "_fast"
    with patch.object(routing_model, "local_json", return_value={
        "done": True, "done_reason": "stop",
        "message": {"content": json.dumps({"action": wrong_speed})},
    }):
        try:
            routing_model.classify(spoken, catalogue, configured)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Model changed the requested speed: {spoken}")

for spoken in ("Don't read this at 2x", "If you can, read this page at 2x"):
    with patch.object(routing_model, "local_json", return_value={
        "done": True, "done_reason": "stop",
        "message": {"content": '{"action":"none"}'},
    }):
        assert routing_model.classify(spoken, catalogue, configured)["actual"] == "none"

# Exercise the real pipeline method without requiring OVOS to be installed on
# the development host. A model timeout must return control to native routes.
tree = ast.parse((root / "ovos_skill_jarvis_dispatcher/routing_pipeline.py").read_text())
pipeline = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                and node.name == "JarvisQwenPipeline")
match = next(node for node in pipeline.body if isinstance(node, ast.FunctionDef)
             and node.name == "match")
current = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
               and node.name == "current_runtime")
namespace = {
    "current_runtime": lambda *_: (skill, runtime),
    "question_like": lambda _: False,
    "RequestCancelled": routing_model.RequestCancelled,
    "EVENT": "jarvis.qwen.execute",
}
skill = types.SimpleNamespace(log=Mock())
runtime = types.SimpleNamespace(propose=Mock(side_effect=TimeoutError("model busy")),
                                last=None)
current_globals = {"UTTERANCE_EVENTS": {"recognizer_loop:utterance"},
                   "get_dispatcher": lambda: skill}
skill._qwen_router = runtime
exec(compile(ast.Module(body=[current], type_ignores=[]),
             "routing_pipeline.py", "exec"), current_globals)
empty_event = types.SimpleNamespace(msg_type="recognizer_loop:utterance")
assert current_globals["current_runtime"](["  "], "en-US", empty_event) == (None, None)
assert current_globals["current_runtime"](["read this"], "en-US", empty_event) == (skill, runtime)
exec(compile(ast.Module(body=[match], type_ignores=[]),
             "routing_pipeline.py", "exec"), namespace)
message = types.SimpleNamespace(context={})
assert namespace["match"](None, ["read this at 2x"], "en-US", message) is None
assert runtime.last == "unavailable"
assert message.context["jarvis_qwen_unavailable"] is True
runtime.propose = Mock(return_value=None)
message.context.clear()
assert namespace["match"](None, ["read the page"], "en-US", message) is None
assert "jarvis_qwen_unavailable" not in message.context

chat_pipeline = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                     and node.name == "JarvisQwenChatPipeline")
chat_match = next(node for node in chat_pipeline.body if isinstance(node, ast.FunctionDef)
                  and node.name == "match")
namespace["reply_match"] = Mock()
exec(compile(ast.Module(body=[chat_match], type_ignores=[]),
             "routing_pipeline.py", "exec"), namespace)
message.context["jarvis_qwen_unavailable"] = True
assert namespace["match"](None, ["read the page"], "en-US", message) is None
namespace["reply_match"].assert_not_called()

print("PASS: Qwen reading keeps target/speed, ignores silence and yields on failure")
