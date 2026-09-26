#!/usr/bin/env python3
"""Exercise one-turn desktop and private agent messages without an OVOS bus."""
import importlib.util
import subprocess
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


integration = load("hermes_message", ROOT / "ovos_skill_jarvis_dispatcher/integrations/hermes_desktop.py")
claude = load("claude_message", ROOT / "ovos_skill_jarvis_dispatcher/integrations/claude_desktop.py")
agents = load("agent_message", ROOT / "ovos_skill_jarvis_dispatcher/agents.py")
conversation = load("jarvis_conversation", ROOT / "ovos_skill_jarvis_dispatcher/conversation.py")


class FakeSkill(integration.HermesDesktopIntegrationMixin,
                claude.ClaudeDesktopIntegrationMixin,
                agents.AgentActionsMixin,
                conversation.ConversationMixin):
    def __init__(self):
        self._message_lock = threading.RLock()
        self._message_timer = None
        self._message_generation = 0
        self._message_stage = None
        self._pending_agent = None
        self._pending_message = None
        self._pending_window_id = None
        self._message_retries = 0
        self._confirmation_retries = 0
        self.keys = []
        self.typed = []
        self.spoken = []
        self.window = ("123", 'WM_CLASS(STRING) = "hermes", "Hermes"')
        self.windows = []
        self.log = Mock()

    def _focus_hermes_desktop(self):
        return True

    def _open_claude_desktop_new_chat(self):
        return "123"

    def _focused_window_details(self):
        return self.windows.pop(0) if self.windows else self.window

    def _send_focused_keys(self, keys):
        self.keys.append(keys)

    def _type_focused_text(self, text):
        self.typed.append(text)

    def activate(self, **_kwargs):
        pass

    def deactivate(self):
        pass

    def speak(self, text, **_kwargs):
        self.spoken.append(text)

    def _arm_message_timeout(self, _seconds):
        pass

    def _active_window_id(self):
        return self.window[0]

    @staticmethod
    def _confirmation_token(text):
        return str(text).lower().strip(" .")


def reply(skill, utterance):
    return skill._converse_impl(SimpleNamespace(data={"utterances": [utterance]}))


with patch.object(integration.time, "sleep"):
    skill = FakeSkill()
    skill._message_hermes_desktop()
    assert skill.keys == ["ctrl+n", "ctrl+l"], skill.keys
    assert skill._message_stage == "hermes_message"
    assert skill.spoken[-1] == "Ready."

    # A stray media command is left to native routes, not sent as a message.
    assert reply(skill, "Pause music") is False
    assert skill._message_stage is None
    assert skill.typed == [] and "Return" not in skill.keys

    skill._message_hermes_desktop()
    assert reply(skill, "")
    assert skill._message_stage == "hermes_message"
    assert skill.typed == []
    assert reply(skill, "cancel")
    assert skill._message_stage is None and skill.typed == []

    skill._message_hermes_desktop()
    assert reply(skill, "Hello Hermes")
    assert skill.typed == ["Hello Hermes"] and skill.keys[-1] == "Return"
    assert skill._message_stage is None
    assert skill.spoken[-1] == "Message sent."

    skill = FakeSkill()
    skill._message_hermes_desktop()
    skill.window = ("999", 'WM_CLASS(STRING) = "terminal", "Terminal"')
    assert reply(skill, "Hello Hermes")
    assert skill.typed == [] and "Return" not in skill.keys

    skill = FakeSkill()
    skill._message_hermes_desktop()
    skill.windows = [skill.window, skill.window,
                     ("999", 'WM_CLASS(STRING) = "terminal", "Terminal"')]
    assert reply(skill, "Hello Hermes")
    assert skill.typed == ["Hello Hermes"] and "Return" not in skill.keys

    # The private agent flow sends once via its helper, with no second prompt.
    skill = FakeSkill()
    skill.sent_agent = []
    skill._send_agent_message = lambda *args: skill.sent_agent.append(args)
    skill._message_agent("codex")
    assert skill.spoken[-1] == "Ready."
    assert reply(skill, "Research this")
    assert skill.sent_agent == [("codex", "Research this")]
    assert skill._message_stage is None

    skill._message_agent("claude")
    assert reply(skill, "Pause music") is False
    assert skill.sent_agent == [("codex", "Research this")]
    skill._message_agent("claude")
    skill._message_timeout(skill._message_generation)
    assert skill._message_stage is None and skill.sent_agent == [("codex", "Research this")]
    assert skill.spoken[-1] == "Ready."
    skill._message_agent("claude")
    assert reply(skill, "Review this")
    assert skill.sent_agent[-1] == ("claude", "Review this")

    # Real helper path gets exactly the dictated text and acknowledges only
    # when the allowlisted submission succeeds.
    skill = FakeSkill()
    with patch.object(agents.subprocess, "run") as run:
        skill._send_agent_message("claude", "Review this")
    assert run.call_args_list[0].kwargs["input"] == "Review this\n"
    assert skill.spoken[-1] == "Message sent."
    skill = FakeSkill()
    with patch.object(agents.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "helper")):
        skill._send_agent_message("claude", "Review this")
    assert skill.spoken[-1] == "I could not message Claude agent."

    skill = FakeSkill()
    skill.sent_agent = []
    skill._send_agent_message = lambda *args: skill.sent_agent.append(args)

    # Explicitly confirmed web research remains a distinct operation.
    skill._message_stage = "confirmation"
    skill._pending_agent = "codex"
    skill._pending_message = "test prompt"
    assert reply(skill, "send it")
    assert skill.sent_agent[-1] == ("codex", "test prompt")

    skill = FakeSkill()
    skill.windows = [skill.window, ("999", 'WM_CLASS(STRING) = "terminal", "Terminal"')]
    skill._message_hermes_desktop()
    assert skill._message_stage is None
    assert skill.keys == ["ctrl+n"]

    # Claude Desktop checks the same window again after typing, before Return.
    skill = FakeSkill()
    skill.window = ("123", 'WM_CLASS(STRING) = "com.anthropic.claude", "Claude"')
    skill._message_claude_desktop()
    assert skill.spoken[-1] == "Ready."
    with patch.object(claude.subprocess, "run") as run:
        assert reply(skill, "Hello Claude")
    assert [call.args[0][-1] for call in run.call_args_list] == ["BackSpace", "Hello Claude", "Return"]
    assert skill.spoken[-1] == "Message sent."

    skill = FakeSkill()
    skill.window = ("123", 'WM_CLASS(STRING) = "com.anthropic.claude", "Claude"')
    skill._message_claude_desktop()
    skill.windows = [skill.window, ("999", 'WM_CLASS(STRING) = "terminal", "Terminal"')]
    with patch.object(claude.subprocess, "run") as run:
        assert reply(skill, "Hello Claude")
    assert run.call_count == 2 and skill.spoken[-1] != "Message sent."

    # Explicit "agent" targets the private helper, never the desktop chat.
    skill = FakeSkill()
    skill._jarvis_profile = {"private_extensions": {"agents": True}}
    skill._route_claude_message(SimpleNamespace(data={"utterance": "Message Claude agent"}))
    assert skill._message_stage == "message" and skill._pending_agent == "claude"
    assert skill.spoken[-1] == "Ready."

    skill = FakeSkill()
    skill._jarvis_profile = {"private_extensions": {"agents": False}}
    skill._route_claude_message(SimpleNamespace(data={"utterance": "Message Claude agent"}))
    assert skill._message_stage is None
    assert skill.spoken == ["Claude agent is not enabled on this computer."]

    skill = FakeSkill()
    skill._route_claude_message(SimpleNamespace(data={"utterance": "Message Claude"}))
    assert skill._message_stage == "claude_message"

print("PASS: one-turn Hermes, Claude and private agent messages; focus and native escapes")
