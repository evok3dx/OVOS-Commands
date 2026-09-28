#!/usr/bin/env python3
"""Verify semantic Qwen fallback coverage without executing desktop actions."""

import json
import runpy
import sys
import types
from pathlib import Path
from unittest.mock import patch


root = Path(__file__).resolve().parents[1]
package = types.ModuleType("ovos_skill_jarvis_dispatcher")
package.__path__ = [str(root / "ovos_skill_jarvis_dispatcher")]
sys.modules[package.__name__] = package

from ovos_skill_jarvis_dispatcher import action_registry, profile, routing_model


configured = profile.resolve_profile({
    "applications": {
        "brave": "brave",
        "firefox": "firefox",
        "claude": "claude_desktop",
        "hermes": "hermes_desktop",
    },
    "spoken_names": {"hermes_desktop": "my assistant"},
    "private_extensions": {"agents": True},
})
catalogue = action_registry.router_catalog(configured)

required = {
    "text.write", "dictation.start", "dictation.pause", "dictation.resume",
    "dictation.stop", "reading.last_typed", "reading.selection",
    "reading.selection_fast", "reading.page", "reading.page_fast",
    "browser.search_firefox", "browser.search_brave", "media.search",
    "media.prompt",
    "hermes.message", "claude_desktop.message", "codex.message",
    "claude_agent.message",
}
assert required <= catalogue.keys(), required - catalogue.keys()

benchmark = runpy.run_path(str(root / "scripts/routing-benchmark.py"),
                           run_name="jarvis_policy_test")
for phrase, expected in benchmark["cases"]():
    if expected == "none":
        continue
    allowed = routing_model.candidates_for(phrase, catalogue, configured)
    assert expected in allowed, (phrase, expected, sorted(allowed))

cases = (
    ("Could you start writing for me?", "text.write"),
    ("Begin continuous dictation", "dictation.start"),
    ("Would you read this sentence aloud?", "reading.selection"),
    ("Please read this page twice as fast", "reading.page_fast"),
    ("I want to look something up using Firefox", "browser.search_firefox"),
    ("Can I search through Brave?", "browser.search_brave"),
    ("Use the browser to look this up", "browser.search_brave"),
    ("Can I dictate something to Hermes?", "hermes.message"),
    ("I need to tell my assistant something", "hermes.message"),
    ("I need to tell Claude something", "claude_desktop.message"),
    ("Start a message for the Codex agent", "codex.message"),
    ("Let me ask the Claude agent something", "claude_agent.message"),
    ("Put on Get Lucky", "media.search"),
    ("Could you play some music?", "media.prompt"),
)
for spoken, expected in cases:
    payload, allowed = routing_model.payload_for(spoken, catalogue, configured)
    assert expected in allowed, (spoken, expected, sorted(allowed))
    enum = payload["format"]["properties"]["action"]["enum"]
    assert expected in enum
    with patch.object(routing_model, "local_json", return_value={
        "done": True,
        "done_reason": "stop",
        "message": {"content": json.dumps({"action": expected})},
    }):
        assert routing_model.classify(
            spoken, catalogue, configured,
        )["actual"] == expected

for spoken in ("Can I search through Brave?", "Can I dictate something to Hermes?"):
    payload, _allowed = routing_model.payload_for(spoken, catalogue, configured)
    system_prompt = payload["messages"][0]["content"]
    assert "polite request phrased as a question" in system_prompt
    assert "information-seeking question" in system_prompt

assert routing_model.media_search_request("Could you play a song called Get Lucky?") == "Get Lucky"
assert routing_model.media_search_request("Lay Get Lucky") == "Get Lucky"
assert routing_model.media_search_request("I would like to hear Teardrop please") == "Teardrop"
assert routing_model.media_search_request("play music") is None
assert routing_model.media_search_request("Could you start writing for me?") is None
assert routing_model.media_search_request("All Eyes on Me by Tupac") is None
assert routing_model.media_search_request(
    "All Eyes on Me by Tupac", model_approved=True
) == "All Eyes on Me by Tupac"
assert routing_model.media_search_request(
    "Lay All Eyes on Me by Tupac", model_approved=True
) == "All Eyes on Me by Tupac"
assert routing_model.media_search_request(
    "Do not play All Eyes on Me", model_approved=True
) is None
assert routing_model.media_search_request(
    "All Eyes on Me then close Firefox", model_approved=True
) is None

# Dispatch forwards only the bounded title as data to the separate Media skill.
class FakeMessage:
    def __init__(self, msg_type, data=None):
        self.msg_type = msg_type
        self.data = data or {}


sys.modules["ovos_bus_client"] = types.SimpleNamespace(Message=FakeMessage)
emitted = []
fake_skill = types.SimpleNamespace(
    _jarvis_profile=configured,
    bus=types.SimpleNamespace(emit=emitted.append),
)
spoken = FakeMessage("ovos.utterance.handle", {
    "utterance": "Could you play a song called Get Lucky?",
})
assert action_registry.dispatch_action(
    fake_skill, "media.search", spoken, source="router",
)
assert emitted[0].msg_type == "jarvis.media.play_query"
assert emitted[0].data == {"query": "Get Lucky"}
title_only = FakeMessage("ovos.utterance.handle", {
    "utterance": "Lay All Eyes on Me by Tupac",
})
assert action_registry.dispatch_action(
    fake_skill, "media.search", title_only, source="router",
)
assert emitted[1].data == {"query": "All Eyes on Me by Tupac"}
assert action_registry.dispatch_action(
    fake_skill, "media.search", title_only, source="personal",
)
assert emitted[2].data == {"query": "All Eyes on Me by Tupac"}

# The model can only start message capture. It never receives a message body,
# and ambiguous multi-target requests fail closed.
assert routing_model.message_candidates("tell Claude and Hermes", catalogue) == set()
assert routing_model.candidates_for(
    "tell Claude and Hermes", catalogue, configured,
) == {}

# Newly detected applications inherit bounded open/focus/minimise/maximise
# coverage from the profile. No hard-coded app name or phrase is required.
dynamic_id = "desktop_0123456789abcdef01234567"
dynamic_profile = {
    "applications": {
        dynamic_id: {
            "display_name": "Obsidian",
            "aliases": ["obsidian", "my knowledge app"],
            "integration": dynamic_id,
            "wm_class": "obsidian",
        },
    },
    "private_extensions": {"agents": False},
    "spoken_names": {dynamic_id: "research console"},
}
dynamic_catalogue = action_registry.router_catalog(dynamic_profile)
allowed = routing_model.candidates_for(
    "Could you bring up my research console?", dynamic_catalogue, dynamic_profile,
)
assert f"application.open.{dynamic_id}" in allowed
assert f"application.focus.{dynamic_id}" in allowed
assert f"application.close.{dynamic_id}" not in dynamic_catalogue

# Private agent actions disappear completely when that extension is disabled.
public_profile = profile.resolve_profile({
    "applications": {"claude": "claude_desktop"},
    "private_extensions": {"agents": False},
})
public_catalogue = action_registry.router_catalog(public_profile)
assert "codex.message" not in public_catalogue
assert "claude_agent.message" not in public_catalogue
assert "claude_desktop.message" in public_catalogue

no_desktop_profile = profile.resolve_profile({
    "applications": {},
    "private_extensions": {"agents": False},
})
no_desktop_catalogue = action_registry.router_catalog(no_desktop_profile)
assert "claude_desktop.message" not in no_desktop_catalogue
assert "hermes.message" not in no_desktop_catalogue

print("PASS: Qwen fallback covers safe workflows and dynamic applications")
