#!/usr/bin/env python3
"""The prompted search submits once, and never presses Enter after focus moves."""
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import Mock, patch

root = Path(__file__).resolve().parents[1]
package = types.ModuleType("ovos_skill_jarvis_dispatcher")
package.__path__ = [str(root / "ovos_skill_jarvis_dispatcher")]
sys.modules[package.__name__] = package
source = root / "ovos_skill_jarvis_dispatcher/browser.py"
spec = importlib.util.spec_from_file_location(
    "ovos_skill_jarvis_dispatcher.browser", source,
)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
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
with patch.object(module, "pace_search", return_value=0), \
        patch.object(module.time, "sleep") as sleep, \
        patch.object(module.subprocess, "run") as run:
    browser._submit_prompted_browser_search("harvard jarvis", "firefox", "123")
actions = [call.args[0] for call in run.call_args_list]
assert len(actions) == 3, actions
assert actions[0][-1] == "ctrl+a" and actions[-1][-1] == "Return", actions
assert "ctrl+t" not in str(actions) and "harvard%20jarvis" not in str(actions)
assert actions[1][-2:] == ["--", "harvard jarvis"], actions
assert actions[1][3:5] == ["--delay", "55"], actions
sleep.assert_called_once_with(0.45)

browser = Browser()
def lose_focus(command, **_kwargs):
    if "type" in command:
        browser.window = "456"

with patch.object(module, "pace_search", return_value=0), \
        patch.object(module.time, "sleep"), \
        patch.object(module.subprocess, "run", side_effect=lose_focus) as run:
    browser._submit_prompted_browser_search("search terms", "firefox", "123")
assert run.call_count == 2
assert browser.spoken == ["The focused window changed, so I cancelled."]
print("PASS: prompted Firefox search submits once and stops after focus changes")
