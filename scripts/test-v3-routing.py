#!/usr/bin/env python3
"""Offline checks for V3's native, local-model and GUI command routes."""
import ast
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "jarvis_pipeline_setup", ROOT / "scripts/configure-intent-pipeline.py")
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)

base = ["ovos-adapt-pipeline-plugin-high", "ovos-fallback-pipeline-plugin-medium",
        "ovos-common-query-pipeline-plugin", "ovos-fallback-pipeline-plugin-low"]
stages = pipeline.merge_v3_pipeline(base)
assert stages == [base[0], "jarvis-media-pipeline", "jarvis-qwen-pipeline",
                  base[1], base[2], "jarvis-qwen-chat-pipeline", base[3]]
assert pipeline.merge_v3_pipeline(stages) == stages
private = [base[0], "brain-private-pipeline", *base[1:]]
assert "brain-private-pipeline" in pipeline.merge_v3_pipeline(private)
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
try:
    media.control("delete")
except ValueError:
    pass
else:
    raise AssertionError("Unreviewed media action accepted")

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
    assert len(files) == 45, len(files)
    assert len(media) == 7, len(media)
    assert any("{query}" in phrase for _, phrase in files)
    assert any("{title}" in phrase for phrase in media)
    assert "if action_id == 'files.search':" in source
    registry = (ROOT / "ovos_skill_jarvis_dispatcher/action_registry.py").read_text()
    assert '"system.insert_new_line": _action(' in registry
    assert '"files.search": _action(' in registry
    assert 'files.search' in (ROOT / "ovos_skill_jarvis_dispatcher/routing_prompt.py").read_text()

print("PASS: V3 pipeline order and GUI media/file phrase lists")
