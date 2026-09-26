#!/usr/bin/env python3
"""The prompted search submits once, and never presses Enter after focus moves."""
import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch

source = Path(__file__).resolve().parents[1] / "ovos_skill_jarvis_dispatcher/browser.py"
spec = importlib.util.spec_from_file_location("browser_focus_test", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Browser(module.BrowserActionsMixin):
    def __init__(self):
        self.window = "123"
        self.spoken = []
        self.log = Mock()

    def _active_window_id(self):
        return self.window

    def _active_browser(self):
        return "firefox"

    def speak(self, text):
        self.spoken.append(text)


browser = Browser()
with patch.object(module.subprocess, "run") as run:
    browser._submit_prompted_browser_search("harvard jarvis", "firefox", "123")
actions = [call.args[0] for call in run.call_args_list]
assert len(actions) == 3, actions
assert actions[0][-1] == "ctrl+a" and actions[-1][-1] == "Return", actions
assert "ctrl+t" not in str(actions) and "harvard%20jarvis" not in str(actions)
assert "harvard+jarvis" in str(actions), actions

browser = Browser()
def lose_focus(command, **_kwargs):
    if "type" in command:
        browser.window = "456"

with patch.object(module.subprocess, "run", side_effect=lose_focus) as run:
    browser._submit_prompted_browser_search("search terms", "firefox", "123")
assert run.call_count == 2
assert browser.spoken == ["The focused window changed, so I cancelled."]
print("PASS: prompted Firefox search submits once and stops after focus changes")
