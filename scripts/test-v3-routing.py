#!/usr/bin/env python3
"""Offline checks for V3's native, local-model and GUI command routes."""
import ast
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
action_spec = importlib.util.spec_from_file_location(
    "jarvis_action_registry",
    ROOT / "ovos_skill_jarvis_dispatcher/action_registry.py",
)
action_registry = importlib.util.module_from_spec(action_spec)
action_spec.loader.exec_module(action_registry)
strict_spoken_action = action_registry.strict_spoken_action

sys.modules.setdefault("ovos_bus_client", SimpleNamespace(Message=SimpleNamespace))
controls_spec = importlib.util.spec_from_file_location(
    "jarvis_system_controls", ROOT / "ovos_skill_jarvis_dispatcher/system_controls.py",
)
system_controls = importlib.util.module_from_spec(controls_spec)
controls_spec.loader.exec_module(system_controls)

class FakeControls(system_controls.SystemControlsMixin):
    def __init__(self):
        self.typed = []
        self.spoken = []
        self.log = type("Log", (), {"exception": lambda *_args: None})()

    def _focused_window_details(self):
        return "123", "editor"

    def _type_focused_text(self, text):
        self.typed.append(text)

    def speak(self, text):
        self.spoken.append(text)

controls = FakeControls()
controls._insert_period()
assert controls.typed == ["."] and controls.spoken == []

strict_profile = {"private_extensions": {"agents": True}, "applications": {}}
assert strict_spoken_action("Message Hermes.", strict_profile) == "hermes.message"
assert strict_spoken_action("message Claude", strict_profile) == "claude_desktop.message"
assert strict_spoken_action("message Claude agent", strict_profile) == "claude_agent.message"
assert strict_spoken_action("search Firefox", strict_profile) == "browser.search_firefox"
assert strict_spoken_action("message Hermes with private data", strict_profile) is None
disabled_agents = {"private_extensions": {"agents": False}, "applications": {}}
assert strict_spoken_action("message Claude agent", disabled_agents) is None
spec = importlib.util.spec_from_file_location(
    "jarvis_pipeline_setup", ROOT / "scripts/configure-intent-pipeline.py")
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)

base = ["ovos-adapt-pipeline-plugin-high", "ovos-fallback-pipeline-plugin-medium",
        "ovos-common-query-pipeline-plugin", "ovos-fallback-pipeline-plugin-low"]
stages = pipeline.merge_v3_pipeline(base)
assert stages == [base[0], "jarvis-media-pipeline", "jarvis-qwen-pipeline",
                  "jarvis-unmatched-pipeline", base[1], base[2],
                  "jarvis-qwen-chat-pipeline", base[3]]
assert pipeline.merge_v3_pipeline(stages) == stages
private = [base[0], "reference-private-pipeline", *base[1:]]
assert "reference-private-pipeline" in pipeline.merge_v3_pipeline(private)
for broken in ([], ["ovos-fallback-pipeline-plugin-medium"], ["broken", 1]):
    try:
        pipeline.merge_v3_pipeline(broken)
    except ValueError:
        pass
    else:
        raise AssertionError("Malformed pipeline accepted")

media_path = ROOT / "plugins/ovos-skill-jarvis-media/ovos_skill_jarvis_media/media.py"
media_spec = importlib.util.spec_from_file_location("jarvis_media_parser", media_path)
media = importlib.util.module_from_spec(media_spec)
media_spec.loader.exec_module(media)
assert media.query_from_utterance("Play a song called Brave New World") == "a song called Brave New World"
assert media.query_from_utterance("do not play a song") is None
assert media.query_from_utterance("play music") is None
assert media.first_result(json.dumps({"entries": [{"id": "ABCDEFGHIJK", "title": "Example"}]})) == (
    "https://www.youtube.com/watch?v=ABCDEFGHIJK", "Example")
assert media.provider_search_blocked(
    "ERROR: Sign in to confirm you're not a bot"
)
assert media.provider_search_blocked("HTTP Error 429: Too Many Requests")
assert not media.provider_search_blocked("No matching videos were found")
try:
    media.control("delete")
except ValueError:
    pass
else:
    raise AssertionError("Unreviewed media action accepted")

# A valid title receives one concise acknowledgement before the asynchronous
# Brave lookup starts. Empty or generic requests never reach this handler.
skill_source = (ROOT / "plugins/ovos-skill-jarvis-media/ovos_skill_jarvis_media/__init__.py").read_text()
skill_tree = ast.parse(skill_source)
skill_class = next(node for node in skill_tree.body if isinstance(node, ast.ClassDef)
                   and node.name == "JarvisMediaSkill")
handle_play = next(node for node in skill_class.body if isinstance(node, ast.FunctionDef)
                   and node.name == "_handle_play")
spoken = []
started = []

class FakeThread:
    def __init__(self, *, target, args, name, daemon):
        assert name == "jarvis-media-youtube" and daemon is True
        self.target = target
        self.args = args

    def start(self):
        started.append(self.args)

fake_skill = SimpleNamespace(
    _media_lock=threading.RLock(),
    _media_generation=0,
    _cancel_locked=lambda: None,
    _search_and_open=lambda *_args: None,
    speak=lambda text, **kwargs: spoken.append((text, kwargs)),
)
handle_scope = {"normalise_query": media.normalise_query,
                "threading": SimpleNamespace(Thread=FakeThread)}
exec(compile(ast.Module(body=[handle_play], type_ignores=[]),
             "ovos_skill_jarvis_media/__init__.py", "exec"), handle_scope)
handle_scope["_handle_play"](fake_skill, SimpleNamespace(data={"query": "Get Lucky"}))
assert spoken == [("Let me spin that track.", {"wait": True})]
assert started == [("Get Lucky", 1)]
assert "RESULT_TRANSITION_SECONDS = 1.5" in skill_source
assert 'pace_search("media", jitter=0.0)' in skill_source

# Starting the address-bar prompt must not clear/deactivate the conversation
# immediately before it is activated. That ordering made live follow-up speech
# fall through to broad fallback instead of being typed into the browser.
browser_tree = ast.parse(
    (ROOT / "ovos_skill_jarvis_dispatcher/browser.py").read_text()
)
browser_class = next(
    node for node in browser_tree.body
    if isinstance(node, ast.ClassDef) and node.name == "BrowserActionsMixin"
)
address_prompt = next(
    node for node in browser_class.body
    if isinstance(node, ast.FunctionDef) and node.name == "_prompt_browser_address"
)
address_calls = {
    node.func.attr for node in ast.walk(address_prompt)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
}
assert "_clear_message_state" not in address_calls
assert {"_run_browser_action", "activate", "_arm_message_timeout"} <= address_calls

with tempfile.TemporaryDirectory() as temporary:
    home = Path(temporary)
    rollback_spec = importlib.util.spec_from_file_location(
        "jarvis_rollback_sources", ROOT / "scripts/check-plugin-rollback.py")
    rollback_sources = importlib.util.module_from_spec(rollback_spec)
    rollback_spec.loader.exec_module(rollback_sources)
    local_wheel = home / "previous file-search.whl"
    local_url = {"url": local_wheel.as_uri()}
    assert rollback_sources.missing_source(local_url)
    class PreviousLocalPackage:
        def read_text(self, name):
            assert name == "direct_url.json"
            return json.dumps(local_url)
    with patch.object(rollback_sources.metadata, "distribution",
                      return_value=PreviousLocalPackage()):
        try:
            rollback_sources.main()
        except SystemExit as error:
            assert "Cannot safely upgrade" in str(error)
        else:
            raise AssertionError("Missing previous installer source was accepted")
    local_wheel.touch()
    assert not rollback_sources.missing_source(local_url)
    with patch.object(rollback_sources.metadata, "distribution",
                      return_value=PreviousLocalPackage()):
        rollback_sources.main()
    assert rollback_sources.missing_source({"url": "file://remote-host/package.whl"})
    assert not rollback_sources.missing_source({"url": "https://example.org/package.whl"})
    config = home / "mycroft.conf"
    config.write_text(json.dumps({"intents": {"pipeline": private}, "host": "keep"}))
    available = ["--available-plugin", "ovos-adapt-pipeline-plugin",
                 "--available-plugin", "ovos-fallback-pipeline-plugin",
                 "--available-plugin", "ovos-common-query-pipeline-plugin"]
    for name in ("jarvis-media-pipeline", "jarvis-qwen-pipeline",
                 "jarvis-unmatched-pipeline",
                 "jarvis-qwen-chat-pipeline"):
        available += ["--available-plugin", name]
    command = ["python3", str(ROOT / "scripts/configure-intent-pipeline.py"),
               "--config", str(config), "--merge-v3", *available]
    subprocess.run(command, check=True, capture_output=True)
    result = json.loads(config.read_text())
    assert result["host"] == "keep"
    assert result["intents"]["pipeline"] == pipeline.merge_v3_pipeline(private)
    assert result["intents"]["persona"]["handle_fallback"] is False
    original = config.read_bytes()
    subprocess.run(command, check=True, capture_output=True)
    assert config.read_bytes() == original

    # The displayed media and file examples come from the installed packages,
    # rather than a stale, saved phrase count or editable {query} action.
    editor = ROOT / "command_editor/jarvis-command-editor"
    source = editor.read_text()
    nodes = ast.parse(source)
    methods = [n for n in nodes.body if isinstance(n, ast.FunctionDef)
               and n.name in {"file_search_patterns", "media_title_patterns"}]
    namespace = {"Path": Path, "subprocess": subprocess, "json": json,
                 "HOME": home}
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(editor), "exec"), namespace)
    python = home / ".venvs/ovos/bin/python"
    python.parent.mkdir(parents=True)
    python.touch()
    folders = {
        "jarvis_file_search": ROOT / "plugins/jarvis-file-search/jarvis_file_search",
        "ovos_skill_jarvis_media": ROOT / "plugins/ovos-skill-jarvis-media/ovos_skill_jarvis_media",
    }
    def locate(args, **_kwargs):
        folder = folders["jarvis_file_search" if "jarvis_file_search" in args[-1]
                         else "ovos_skill_jarvis_media"]
        return subprocess.CompletedProcess(args, 0, str(folder) + "\n", "")
    with patch.object(subprocess, "run", side_effect=locate):
        files = namespace["file_search_patterns"]()
        media = namespace["media_title_patterns"]()
    assert len(files) == 47, len(files)
    assert len(media) == 7, len(media)
    assert any("{query}" in phrase for _, phrase in files)
    assert any("{title}" in phrase for phrase in media)
    assert "if action_id == 'files.search':" in source
    registry = (ROOT / "ovos_skill_jarvis_dispatcher/action_registry.py").read_text()
    assert '"system.insert_new_line": _action(' in registry
    assert '"files.search": _action(' in registry
assert 'files.search' in (ROOT / "ovos_skill_jarvis_dispatcher/routing_prompt.py").read_text()

# A wake-only transcription is consumed silently. A current-time question
# reaches native date/time first and cannot be answered by the offline chat
# model if the native skill was unavailable.
chat_tree = ast.parse((ROOT / "ovos_skill_jarvis_dispatcher/routing_chat.py").read_text())
functions = [node for node in chat_tree.body if isinstance(node, ast.FunctionDef)
             and node.name in {"question_like", "wake_only", "live_question"}]
chat_helpers = {"re": re}
exec(compile(ast.Module(body=functions, type_ignores=[]), "routing_chat.py", "exec"),
     chat_helpers)
assert chat_helpers["wake_only"]("Hey Jarvis.")
assert not chat_helpers["wake_only"]("Hey Jarvis, open Firefox")
for question in ("What time is it?", "Time is it.", "What is the time?",
                 "What day is it?", "What is today's date?"):
    assert chat_helpers["live_question"](question), question
assert not chat_helpers["live_question"]("What is RAM?")

pipeline_tree = ast.parse((ROOT / "ovos_skill_jarvis_dispatcher/routing_pipeline.py").read_text())
chat_cls = next(n for n in pipeline_tree.body if isinstance(n, ast.ClassDef)
                and n.name == "JarvisQwenChatPipeline")
chat_match = next(n for n in chat_cls.body if isinstance(n, ast.FunctionDef)
                  and n.name == "match")
calls = []
runtime = SimpleNamespace(epoch=7,
                          reply_token=lambda utterance, epoch, command=False:
                          calls.append((utterance, epoch, command)) or "reply-token")
skill = SimpleNamespace(skill_id="jarvis")
scope = {"current_runtime": lambda *args: (skill, runtime),
         "wake_only": chat_helpers["wake_only"],
         "live_question": chat_helpers["live_question"],
         "question_like": chat_helpers["question_like"],
         "reply_match": lambda _, token, utterance: (token, utterance)}
exec(compile(ast.Module(body=[chat_match], type_ignores=[]), "routing_pipeline.py", "exec"), scope)
message = SimpleNamespace(context={})
assert scope["match"](None, ["Hey Jarvis."], "en-US", message) == ("reply-token", "Hey Jarvis.")
assert calls.pop() == ("Hey Jarvis.", 6, True)  # quiet token
assert scope["match"](None, ["What time is it?"], "en-US", message) == ("reply-token", "What time is it?")
assert calls.pop() == ("What time is it?", 7, True)  # Please repeat, no made-up time
assert scope["match"](None, ["What is RAM?"], "en-US", message) == ("reply-token", "What is RAM?")
assert calls.pop() == ("What is RAM?", -1, False)  # still a normal chat answer

# Current recognised non-question input is deterministic failure feedback,
# even if no router epoch survived in the message context.
message = SimpleNamespace(context={})
assert scope["match"](None, ["Purple bananas now"], "en-US", message) == (
    "reply-token", "Purple bananas now")
assert calls.pop() == ("Purple bananas now", 7, True)

# A timed-out local router still yields the short failure response instead of
# dropping recognised speech. Empty transcriptions never enter this pipeline.
message = SimpleNamespace(context={'jarvis_qwen_unavailable': True})
assert scope["match"](None, ["Do the unusual thing"], "en-US", message) == (
    "reply-token", "Do the unusual thing")
assert calls.pop() == ("Do the unusual thing", 7, True)

# A narrow stage ahead of general fallbacks claims only recognised
# non-question commands. DDG/common-query still receive real questions.
unmatched_cls = next(n for n in pipeline_tree.body if isinstance(n, ast.ClassDef)
                     and n.name == "JarvisUnmatchedPipeline")
unmatched_match = next(n for n in unmatched_cls.body if isinstance(n, ast.FunctionDef)
                       and n.name == "match")
calls.clear()
scope["current_runtime"] = lambda *args: (skill, runtime)
exec(compile(ast.Module(body=[unmatched_match], type_ignores=[]),
             "routing_pipeline.py", "exec"), scope)
message = SimpleNamespace(context={})
assert scope["match"](None, ["Purple bananas now"], "en-US", message) == (
    "reply-token", "Purple bananas now")
assert calls.pop() == ("Purple bananas now", 7, True)
assert scope["match"](None, ["What are purple bananas?"], "en-US", message) is None

desktop_source = (ROOT / "ovos_skill_jarvis_dispatcher/desktop.py").read_text()
assert 'self.speak("Opening.")' in desktop_source
assert 'self.speak(f"Opening {display_name}.")' not in desktop_source

control_source = (ROOT / "scripts/control_center.py").read_text()
assert "'Open Speech Note and setup guide…'" in control_source
assert 'speech_note_status' in control_source and 'speech_note_action' in control_source

print("PASS: V3 pipeline order and GUI media/file phrase lists")
