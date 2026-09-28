#!/usr/bin/env python3
"""Static safety checks for the modular Jarvis dispatcher."""

import ast
import json
import re
import runpy
import stat
import sys
import tempfile
import types
from pathlib import Path
from xml.etree import ElementTree


sys.dont_write_bytecode = True


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "ovos_skill_jarvis_dispatcher"
MANIFEST = json.loads(
    (ROOT / "deployment-manifest.json").read_text(encoding="utf-8")
)
COMPATIBILITY = json.loads(
    (ROOT / "compatibility.json").read_text(encoding="utf-8")
)
assert MANIFEST["schema_version"] == 2
assert COMPATIBILITY["schema_version"] == 1
EXPECTED_ROOT_MODULES = set(MANIFEST["package_modules"])
EXPECTED_INTEGRATION_MODULES = set(MANIFEST["integration_modules"])
EXPECTED_SYSTEM_HELPERS = set(MANIFEST["runtime_helpers"])
EXPECTED_PROFILES = set(MANIFEST["profiles"])
EXPECTED_SYSTEMD_TEMPLATES = set(MANIFEST["systemd_templates"])

for inventory_name in (
    "package_modules", "integration_modules", "runtime_helpers", "profiles"
):
    inventory = MANIFEST[inventory_name]
    assert inventory, f"Manifest inventory is empty: {inventory_name}"
    assert len(inventory) == len(set(inventory)), (
        f"Manifest inventory contains duplicates: {inventory_name}"
    )
    assert all(Path(item).name == item for item in inventory), (
        f"Manifest inventory contains a path: {inventory_name}"
    )

optional_files = []
for component, files in MANIFEST["optional_components"].items():
    assert files, f"Optional component is empty: {component}"
    assert len(files) == len(set(files)), (
        f"Optional component contains duplicates: {component}"
    )
    for relative in files:
        path = (ROOT / relative).resolve()
        assert ROOT == path.parent or ROOT in path.parents, (
            f"Optional path escapes repository: {relative}"
        )
        assert path.is_file(), f"Optional file is missing: {relative}"
        optional_files.append(path)

for relative in EXPECTED_SYSTEMD_TEMPLATES:
    path = (ROOT / relative).resolve()
    assert ROOT in path.parents, f"Systemd template escapes repository: {relative}"
    assert path.is_file(), f"Systemd template is missing: {relative}"

project_source = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
version_match = re.search(r'^version = "([^"]+)"$', project_source, re.MULTILINE)
assert version_match, "Project version is missing"
PROJECT_VERSION = version_match.group(1)
assert MANIFEST["release_version"] == version_match.group(1)
assert COMPATIBILITY["release_version"] == version_match.group(1)
assert COMPATIBILITY["ovos"]["entry_point_group"] == "opm.skill"
assert re.fullmatch(
    r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
    COMPATIBILITY["updates"]["repository"],
)
assert (
    '"ovos-skill-jarvis-dispatcher.openvoiceos" = '
    '"ovos_skill_jarvis_dispatcher:JarvisDispatcherSkill"'
) in project_source
for project in ("installer", "workshop", "config", "core", "plugin_manager"):
    repository = COMPATIBILITY["upstream"][f"{project}_repository"]
    reference = COMPATIBILITY["upstream"][f"{project}_reference_commit"]
    assert repository.startswith("https://github.com/OpenVoiceOS/")
    assert re.fullmatch(r"[0-9a-f]{40}", reference)
assert re.fullmatch(
    r"[0-9a-f]{64}",
    COMPATIBILITY["upstream"]["installer_archive_sha256"],
)
installer_source = (ROOT / "scripts/install.sh").read_text(encoding="utf-8")
for required_bootstrap_fragment in (
    "read_compatibility_value upstream.installer_repository",
    "read_compatibility_value upstream.installer_reference_commit",
    "read_compatibility_value upstream.installer_archive_sha256",
    'installer_archive_url="${installer_repository%.git}/archive/${installer_commit}.tar.gz"',
    "hashlib.sha256()",
    "if actual != expected:",
    'installer_parent="$(mktemp -d "$state_root/bootstrap.XXXXXX")"',
    'workspace="$(dirname "$archive")/workspace"',
    'actual_sha256="$(sha256sum "$archive"',
    'tar -xzf "$archive" --strip-components=1 -C "$installer_root"',
    'TMPDIR="$installer_tmp" bash setup.sh',
    'cleanup_ovos_download "$installer_parent"',
    "sudo apt-get install --no-install-recommends git",
    "No desktop applications are being installed.",
    "share_telemetry: false",
    "share_usage_telemetry: false",
    "extra_skills: false",
    "Jarvis remains user-space and no desktop applications are installed.",
):
    assert required_bootstrap_fragment in installer_source, (
        f"Installer bootstrap safety check is missing: {required_bootstrap_fragment}"
    )
assert 'for command in git sudo bash' not in installer_source
assert "sudo -n rm -rf" not in installer_source
assert '(cd "$installer_root" && sudo bash setup.sh)' not in installer_source
assert "sudo bash -s" not in installer_source
assert "/var/tmp/jarvis-ovos-root" not in installer_source
assert '${TMPDIR:-/tmp}/jarvis-voice-stack' not in installer_source
assert 'mktemp -d "$state_root/voice-stack.XXXXXX"' in installer_source
doctor_source = (ROOT / "scripts/doctor.py").read_text(encoding="utf-8")
assert "metadata.entry_points(group=group)" in doctor_source
assert 'entries_for("opm.skill")' in doctor_source
assert 'entries_for("opm.wake_word")' in doctor_source
assert 'entries_for("opm.stt")' in doctor_source
assert 'entries_for("opm.tts")' in doctor_source
assert 'entries_for("opm.VAD")' in doctor_source
assert "entry.group for entry in metadata.entry_points()" not in doctor_source
assert "result.stderr.strip()" in doctor_source
doctor_tree = ast.parse(doctor_source)
probe_values = [
    node.value.value
    for node in ast.walk(doctor_tree)
    if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == "probe" for target in node.targets)
    and isinstance(node.value, ast.Constant)
    and isinstance(node.value.value, str)
]
assert len(probe_values) == 1
compile(probe_values[0], "doctor-ovos-probe", "exec")
tray_source = (ROOT / "tray/ovos-tray.py").read_text(encoding="utf-8")
assert 'Open Jarvis…' in tray_source
assert 'Stop speaking' in tray_source
assert 'Restart Jarvis' not in tray_source
assert 'service_action' not in tray_source
assert "from control_runtime import" in tray_source
for gui_module in ('control_center.py', 'control_runtime.py'):
    compile((ROOT / 'scripts' / gui_module).read_text(), gui_module, 'exec')
control_center = (ROOT / 'scripts/control_center.py').read_text(encoding='utf-8')
assert "'Restart commands'" in control_center
assert "'Restart full voice system'" in control_center
assert "'Update Available ('" in control_center
assert "self.service_labels" in control_center
assert "'jarvis-danger'" in control_center
assert "'jarvis-service-row'" in control_center
assert "'jarvis-led-ready'" in control_center
assert "'Everything is working'" in control_center
assert "'jarvis-summary-good'" in control_center
assert "self.page('updates','Updates'" in control_center
assert "background-color: #2F6FED" in control_center
assert "background-color: #20A464" in control_center
assert "def uninstall(" in control_center
assert "update_available()" not in control_center
assert "relaunch_control_center()" in control_center
assert "Gtk.ResponseType.CANCEL" in control_center
control_runtime = (ROOT / 'scripts/control_runtime.py').read_text(encoding='utf-8')
assert "relaunch-control-center.py" in control_runtime
updater_source = (ROOT / 'scripts/update.py').read_text(encoding='utf-8')
assert 'dir=work_dir()' in updater_source
assert 'directory.chmod(0o700)' in updater_source
setup_source = (ROOT / 'scripts/setup.py').read_text(encoding='utf-8')
assert "scroll.set_min_content_height(390)" in setup_source
assert "button.set_mode(False)" in setup_source
assert "Voice only" not in setup_source
assert "core_button" not in setup_source
assert "tab_label('Defaults'" in setup_source
assert "class DefaultAppPicker(Gtk.MenuButton)" in setup_source
assert "Enabled compatible applications" in setup_source
assert '"display_name": "ONLYOFFICE"' in (
    ROOT / "ovos_skill_jarvis_dispatcher/profile.py"
).read_text(encoding="utf-8")

routing_benchmark = (ROOT / "scripts/routing-benchmark.py").read_text()
assert "len(result) < 300" in routing_benchmark
assert "No actions will be executed." in routing_benchmark
assert "does **not** test Whisper" in routing_benchmark
benchmark_scope = runpy.run_path(ROOT / "scripts/routing-benchmark.py",
                                 run_name="jarvis_benchmark_validation")
benchmark_cases = benchmark_scope["cases"]()
assert len(benchmark_cases) == 364
assert len({phrase.casefold() for phrase, _expected in benchmark_cases}) == 364
setup_helper = (ROOT / 'system_helpers/jarvis-setup').read_text(encoding='utf-8')
assert '[[ "$argument" == --gui && -x "$tray" ]]' in setup_helper
assert 'nohup "$tray"' in setup_helper
assert "jarvis-focused-navigation" in EXPECTED_SYSTEM_HELPERS
assert COMPATIBILITY["ovos"]["wakeword"] == {
    "phrase": "hey_jarvis",
    "module": "ovos-ww-plugin-openwakeword",
    "package": "ovos-ww-plugin-openwakeword",
    "validated_version": "0.4.5a2",
    "engine_package": "openwakeword",
    "engine_version": "0.6.0",
    "threshold": 0.4,
}
assert COMPATIBILITY["ovos"]["custom_wakeword"]["module"] == "ovos-ww-plugin-vosk"
assert COMPATIBILITY["ovos"]["stt"]["model"] == "small.en"
assert COMPATIBILITY["ovos"]["tts"]["voice"] == "kokoro/af_bella"
# Keep the original release and the functionally verified reference system upgrade.
# Exact tuples prevent acceptance of unreviewed mixtures or future versions.
assert tuple(COMPATIBILITY["ovos"]["tts"][key] for key in (
    "scriptconv_version", "onnxruntime_version", "numpy_version"
)) in {
    ("0.0.4a23", "1.29.0", "1.26.4"),
    ("0.0.4a31", "1.30.0", "2.4.6"),
}, "TTS dependency versions do not match a reviewed baseline"
assert COMPATIBILITY["ovos"]["tts"]["spacy_version"] == "3.8.15"
assert COMPATIBILITY["ovos"]["validated_package_versions"]["ovos-adapt-parser"] == "1.6.7a2"
assert COMPATIBILITY["ovos"]["validated_package_versions"]["ovos-microphone-plugin-alsa"] == "0.1.3"
assert COMPATIBILITY["ovos"]["validated_package_versions"]["ovos-microphone-plugin-sounddevice"] == "0.0.3a9"
reference_manifest = json.loads(
    (ROOT / COMPATIBILITY["ovos"]["reviewed_stack_manifest"]).read_text(encoding="utf-8")
)
reference_packages = reference_manifest["packages"]
assert len(reference_packages) == 107
assert reference_packages["ovos-core"] == "3.7.0a1"
assert reference_packages["ovos-adapt-parser"] == "1.6.7a2"
assert reference_packages["ovos-microphone-plugin-alsa"] == "0.1.3"
assert reference_packages["ovos-microphone-plugin-sounddevice"] == "0.0.3a9"
assert reference_packages["ovos-phal"] == "0.3.1a1"
assert reference_packages["ovos-plugin-common-play"] == "1.3.10a1"
assert "ovos-skill-jarvis-dispatcher" not in reference_packages
assert 'read_reference_stack_requirements' in installer_source
assert 'Building a clean staged OVOS environment from the reviewed package set.' in installer_source
assert 'cp -a -- "$venv_root" "$stage_venv"' not in installer_source
assert 'scripts/validate-staged-ovos.py' in installer_source
assert 'engine.register_intent_parser(IntentBuilder("JarvisAdaptProbe")' in installer_source

staged_validator = runpy.run_path(ROOT / "scripts/validate-staged-ovos.py")
filter_dependency_report = staged_validator["unexpected_pip_check_lines"]
entry_point_pairs = staged_validator["entry_point_pairs"]
assert filter_dependency_report(
    "openwakeword 0.6.0 has requirement numpy<2, but you have numpy 2.4.6."
) == []
assert filter_dependency_report(
    "old-skill 1.0 requires ovos-workshop<8, but you have 9.8.7a1."
) == ["old-skill 1.0 requires ovos-workshop<8, but you have 9.8.7a1."]
legacy_entry = type("EntryPoint", (), {"name": "legacy"})()
current_entry = type(
    "EntryPoint", (), {"group": "opm.current", "name": "current"}
)()
assert entry_point_pairs({"opm.legacy": [legacy_entry]}) == {
    ("opm.legacy", "legacy")
}
assert entry_point_pairs([current_entry]) == {("opm.current", "current")}

microphone_helpers = runpy.run_path(ROOT / "scripts/configure-microphone.py")
configure_microphone = microphone_helpers["configure"]
implicit_microphone = {"private": "preserved"}
assert configure_microphone(implicit_microphone) is True
assert implicit_microphone["private"] == "preserved"
assert implicit_microphone["listener"]["microphone"] == {
    "module": "ovos-microphone-plugin-sounddevice",
    "ovos-microphone-plugin-sounddevice": {
        "fallback_module": "ovos-microphone-plugin-alsa"
    },
    "ovos-microphone-plugin-alsa": {},
}
explicit_microphone = {
    "listener": {"microphone": {"module": "private-microphone"}}
}
assert configure_microphone(explicit_microphone) is False
assert explicit_microphone["listener"]["microphone"] == {
    "module": "private-microphone"
}

pipeline_helpers = runpy.run_path(ROOT / "scripts/configure-intent-pipeline.py")
migrate_v3_pipeline = pipeline_helpers["migrate_v3_pipeline"]
reviewed_pipeline = COMPATIBILITY["ovos"]["intent_pipeline"]
released_pipeline = [
    "ovos-stop-pipeline-plugin-high",
    "ovos-converse-pipeline-plugin",
    "ovos-ocp-pipeline-plugin-high",
    "ovos-adapt-pipeline-plugin-high",
    "ovos-persona-pipeline-plugin-high",
    "ovos-padatious-pipeline-plugin-high",
    "ovos-fallback-pipeline-plugin-high",
    "ovos-stop-pipeline-plugin-medium",
    "ovos-adapt-pipeline-plugin-medium",
    "ovos-persona-pipeline-plugin-low",
    "ovos-common-query-pipeline-plugin",
    "jarvis-media-pipeline",
    "jarvis-qwen-pipeline",
    "jarvis-unmatched-pipeline",
    "ovos-fallback-pipeline-plugin-medium",
    "jarvis-qwen-chat-pipeline",
    "ovos-fallback-pipeline-plugin-low",
]
assert migrate_v3_pipeline(released_pipeline, reviewed_pipeline) == [
    *reviewed_pipeline[:3],
    "jarvis-media-pipeline",
    *reviewed_pipeline[3:7],
    "jarvis-qwen-pipeline",
    "jarvis-unmatched-pipeline",
    *reviewed_pipeline[7:-1],
    "jarvis-qwen-chat-pipeline",
    reviewed_pipeline[-1],
]
try:
    migrate_v3_pipeline([*released_pipeline, "private-pipeline"], reviewed_pipeline)
except ValueError as error:
    assert "private-pipeline" in str(error)
else:
    raise AssertionError("Custom pipeline stage was silently removed")


assert COMPATIBILITY["ovos"]["intent_pipeline"] == [
    "ovos-stop-pipeline-plugin-high",
    "ovos-converse-pipeline-plugin",
    "ovos-adapt-pipeline-plugin-high",
    "ovos-padatious-pipeline-plugin-high",
    "ovos-fallback-pipeline-plugin-high",
    "ovos-stop-pipeline-plugin-medium",
    "ovos-adapt-pipeline-plugin-medium",
    "ovos-fallback-pipeline-plugin-medium",
    "ovos-common-query-pipeline-plugin",
    "ovos-fallback-pipeline-plugin-low",
]
assert re.fullmatch(
    r"[0-9a-f]{64}", COMPATIBILITY["ovos"]["tts"]["spacy_model_sha256"]
)
assert re.fullmatch(
    r"[0-9a-f]{40}", COMPATIBILITY["ovos"]["tts"]["reference_commit"]
)
assert re.fullmatch(
    r"[0-9a-f]{64}", COMPATIBILITY["ovos"]["tts"]["archive_sha256"]
)
assert (ROOT / "voice/jarvis-ready.wav").read_bytes()[:4] == b"RIFF"
assert "nvidia-" not in installer_source
assert "torch==" not in installer_source
assert "update_available" in tray_source
speechnote_setup = (ROOT / "system_helpers/jarvis-speechnote-setup").read_text(
    encoding="utf-8"
)
reading_helper = (ROOT / "system_helpers/jarvis-read-visible-text").read_text(
    encoding="utf-8"
)
dispatcher_helpers = (ROOT / "ovos_skill_jarvis_dispatcher/helpers.py").read_text(
    encoding="utf-8"
)
assert 'exit 23' in reading_helper
assert 'result.returncode == 23' in dispatcher_helpers
assert 'Reading is already active.' in dispatcher_helpers
for required_speechnote_fragment in (
    "flatpak remote-add --user --if-not-exists flathub",
    'flatpak install --user --noninteractive flathub "$app_id"',
    "never invokes sudo",
    "never changes existing Speech Note settings",
    "keep every existing rule",
    "Rule scope: STT",
    "Rule type: Replace (Regular expression)",
    r"Pattern: \bhey\s*,?\s*jarvis\b\s*\.?\s*",
    "Replace with: one space",
    "If you change Jarvis's wake phrase",
):
    assert required_speechnote_fragment in speechnote_setup, (
        "Speech Note user-space safety check is missing: "
        f"{required_speechnote_fragment}"
    )
assert not any(
    line.strip().startswith("sudo ") for line in speechnote_setup.splitlines()
)
EXPECTED_INTENTS = {
    "CustomCommandIntent",
    "CloseFocusedWindowIntent", "MinimizeFocusedWindowIntent",
    "MaximizeFocusedWindowIntent", "RestoreFocusedWindowIntent",
    "ReadLastTypedTextIntent", "NewNoteIntent",
    "ReadSelectedTextIntent", "ReadVisiblePageIntent",
    "ReadSelectedTextDoubleSpeedIntent", "ReadVisiblePageDoubleSpeedIntent",
    "SelectAllTextIntent", "DeleteSelectedTextIntent",
    "ClearFocusedTextIntent", "UndoTextEditIntent", "RedoTextEditIntent",
    "CopySelectedTextIntent", "CutSelectedTextIntent",
    "PasteTextIntent", "SaveDocumentIntent",
    "SearchFocusedContentIntent", "SearchNotesIntent",
    "PressTabIntent", "PressShiftTabIntent",
    "NewEmailIntent", "SearchMailIntent",
    "JoinZoomMeetingIntent",
    "MuteSystemMicrophoneIntent",
    "MuteSystemAudioIntent",
    "MuteJarvisIntent",
    "PressEnterIntent", "InsertNewLineIntent", "InsertPeriodIntent",
    "PressSpaceIntent", "ShowDesktopIntent",
    "PressEscapeIntent",
    "PlayMediaIntent", "PromptMusicIntent", "PauseMediaIntent", "StopMediaIntent",
    "NextMediaIntent", "PreviousMediaIntent",
    "CapsLockOnIntent", "CapsLockOffIntent",
    "HermesComposerIntent",
    "StartSpeechNoteDictationIntent", "PauseSpeechNoteDictationIntent",
    "ResumeSpeechNoteDictationIntent", "StopSpeechNoteDictationIntent",
    "WriteFocusedTextIntent", "BraveSearchPromptIntent",
    "FirefoxSearchPromptIntent", "YouTubeSearchPromptIntent",
    "YouTubeShortsIntent", "BrowserNavigationIntent",
    "OpenDesktopAppIntent", "FocusDesktopAppIntent",
    "MinimizeDesktopAppIntent", "MaximizeDesktopAppIntent",
    "CloseDesktopAppIntent", "OpenChatGPTWebsiteIntent",
    "OpenClaudeWebsiteIntent",
    "OpenCodexCommandIntent", "FocusCodexCommandIntent",
    "SearchCodexIntent", "ReadCodexResponseIntent",
    "ReadClaudeResponseIntent", "ReadLatestResponseIntent",
    "OpenClaudeAliasIntent", "NaturalDateIntent", "OpenCodexIntent",
    "OpenClaudeIntent", "FocusCodexIntent", "FocusClaudeIntent",
    "NewClaudeChatIntent",
    "NewClaudeAgentIntent", "CreateClaudeSubagentIntent",
    "ShowClaudeAgentsIntent", "ResumeClaudeAgentIntent",
    "MinimizeCodexIntent", "MinimizeClaudeIntent",
    "CloseCodexWindowIntent", "CloseClaudeWindowIntent",
    "MessageCodexIntent", "MessageClaudeIntent", "WriteCodexIntent",
    "WriteClaudeIntent", "TypeCodexIntent", "TypeClaudeIntent",
    "SpeakCodexIntent", "SpeakClaudeIntent", "TalkCodexIntent",
    "TalkClaudeIntent",
    "MessageHermesIntent", "WriteHermesIntent", "TypeHermesIntent",
    "SpeakHermesIntent", "TalkHermesIntent",
}


def install_import_stubs():
    """Provide the minimal OVOS API surface needed for an import check."""

    class IntentBuilder:
        def __init__(self, name):
            self.name = name

        def require(self, _entity):
            return self

    class ConversationalSkill:
        pass

    def intent_handler(_intent):
        return lambda function: function

    modules = {
        "ovos_bus_client": {"Message": type("Message", (), {})},
        "ovos_workshop": {},
        "ovos_workshop.decorators": {"intent_handler": intent_handler},
        "ovos_workshop.intents": {"IntentBuilder": IntentBuilder},
        "ovos_workshop.skills": {},
        "ovos_workshop.skills.converse": {
            "ConversationalSkill": ConversationalSkill,
        },
    }
    for name, attributes in modules.items():
        module = types.ModuleType(name)
        module.__dict__.update(attributes)
        sys.modules[name] = module


def main():
    found = {path.name for path in PACKAGE.glob("*.py")}
    assert found == EXPECTED_ROOT_MODULES, (found, EXPECTED_ROOT_MODULES)

    integrations = PACKAGE / "integrations"
    found_integrations = {path.name for path in integrations.glob("*.py")}
    assert found_integrations == EXPECTED_INTEGRATION_MODULES, (
        found_integrations,
        EXPECTED_INTEGRATION_MODULES,
    )

    found_helpers = {
        path.name
        for path in (ROOT / "system_helpers").iterdir()
        if path.is_file()
    }
    assert found_helpers == EXPECTED_SYSTEM_HELPERS, (
        found_helpers,
        EXPECTED_SYSTEM_HELPERS,
    )

    python_files = list(PACKAGE.glob("*.py")) + list(integrations.glob("*.py"))
    for path in python_files:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")

    for path in optional_files:
        if path.suffix == ".wav":
            assert path.read_bytes()[:4] == b"RIFF"
            continue
        source = path.read_text(encoding="utf-8")
        first_line = source.splitlines()[0]
        if path.suffix == ".py" or "python" in first_line:
            compile(source, str(path), "exec")
        if path.suffix == ".svg":
            ElementTree.parse(path)

    executable_files = [
        *(ROOT / "system_helpers" / name for name in EXPECTED_SYSTEM_HELPERS),
        ROOT / "command_editor/jarvis-command-editor",
        ROOT / "mic/jarvis-mic-indicator",
        ROOT / "mic/jarvis-mic-toggle",
        *(ROOT / "scripts").glob("*.sh"),
        *(ROOT / "scripts").glob("*.py"),
    ]
    assert all(path.stat().st_mode & stat.S_IXUSR for path in executable_files), (
        "Runtime entry points must be executable"
    )

    # GTK belongs to the distribution Python, not the isolated OVOS
    # virtualenv. Keep desktop entry points deterministic even when a user
    # starts installation or setup from an activated virtualenv.
    for path in (
        ROOT / "tray/ovos-tray.py",
        ROOT / "command_editor/jarvis-command-editor",
        ROOT / "mic/jarvis-mic-indicator",
    ):
        assert path.read_text(encoding="utf-8").splitlines()[0] == "#!/usr/bin/python3"
    setup_helper = (ROOT / "system_helpers/jarvis-setup").read_text(encoding="utf-8")
    assert 'exec /usr/bin/python3 "$setup" "$@"' in setup_helper
    installer = (ROOT / "scripts/install.sh").read_text(encoding="utf-8")
    assert 'desktop_python="${JARVIS_DESKTOP_PYTHON:-/usr/bin/python3}"' in installer
    assert '"$desktop_python" -c \'import gi;' in installer

    tree = ast.parse((PACKAGE / "__init__.py").read_text())
    intents = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "IntentBuilder"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }
    assert intents == EXPECTED_INTENTS, (intents, EXPECTED_INTENTS)
    required_entities = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "require"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }

    profile_namespace = {"__name__": "jarvis_profile_check",
                         "__file__": str(PACKAGE / "profile.py"),
                         "__package__": ""}
    exec((PACKAGE / "profile.py").read_text(), profile_namespace)
    reference_profile = profile_namespace["resolve_profile"](
        profile_namespace["REFERENCE_COMPATIBILITY_PROFILE"]
    )

    namespace = {}
    exec((PACKAGE / "vocabulary.py").read_text(), namespace)
    browser_navigation = namespace["BROWSER_NAVIGATION_ACTIONS"]
    assert browser_navigation["roll up"] == "scroll_up"
    assert browser_navigation["roll down"] == "scroll_down"
    assert browser_navigation["top of page"] == "top"
    assert browser_navigation["bottom of page"] == "bottom"

    conversation_namespace = {}
    exec((PACKAGE / "conversation.py").read_text(), conversation_namespace)
    assert "re" in conversation_namespace

    class FakeSkill:
        def __init__(self):
            self.registrations = []

        def register_vocabulary(self, phrase, entity):
            self.registrations.append((phrase, entity))

    fake = FakeSkill()
    fake._jarvis_profile = reference_profile
    namespace["register_skill_vocabulary"](fake, include_custom=False)
    assert len(fake.registrations) == 2024, len(fake.registrations)
    assert len(fake.registrations) == len(set(fake.registrations)), (
        "Duplicate vocabulary registrations are present"
    )
    vocabulary_entities = {entity for _phrase, entity in fake.registrations}
    assert required_entities - {"CustomCommandPhrase"} == vocabulary_entities

    normal = FakeSkill()
    normal._jarvis_profile = profile_namespace["resolve_profile"](
        profile_namespace["SAFE_DEFAULT_PROFILE"]
    )
    namespace["register_skill_vocabulary"](normal, include_custom=False)
    normal_entities = {entity for _phrase, entity in normal.registrations}
    assert not normal_entities.intersection({
        "CodexKeyword", "OpenCodexCommand", "FocusCodexCommand",
        "ReadCodexResponseCommand", "ReadClaudeResponseCommand",
        "NewClaudeAgentCommand", "CreateClaudeSubagentCommand",
        "ShowClaudeAgentsCommand", "ResumeClaudeAgentCommand",
    }), "Private agent vocabulary leaked into the normal configuration"
    phrase_entities = {}
    for phrase, entity in fake.registrations:
        phrase_entities.setdefault(phrase, set()).add(entity)
    collisions = {
        phrase: entities
        for phrase, entities in phrase_entities.items()
        if len(entities) > 1
    }
    assert collisions == {
        "close window": {"CloseFocusedWindowCommand", "CloseKeyword"}
    }
    for phrase in (
        "open standard notes",
        "open standard note",
        "open standard nodes",
        "open standard node",
    ):
        assert (phrase, "OpenDesktopAppCommand") in fake.registrations
    for phrase in (
        "search notes",
        "search nodes",
        "search standard notes",
        "search standard nodes",
    ):
        assert (phrase, "SearchNotesCommand") in fake.registrations
    for phrase in (
        "new note",
        "new notes",
        "new node",
        "new nodes",
        "knee nodes",
    ):
        assert (phrase, "NewNoteCommand") in fake.registrations
    for phrase in ("claude", "cloud", "clawed", "called"):
        assert (
            phrase,
            "ClaudeKeyword",
        ) in fake.registrations
    for phrase in (
        "hermes", "hermas", "omos",
        "hermes desktop", "hermes app",
    ):
        assert (phrase, "HermesKeyword") in fake.registrations
    assert (
        "message",
        "MessageKeyword",
    ) in fake.registrations
    for phrase in (
        "new claude chat",
        "new cloud chat",
        "a new cloud chat",
        "open a new clawed chat",
        "start a new chat with called",
    ):
        assert (phrase, "NewClaudeChatCommand") in fake.registrations
    for phrase, entity in (
        ("new claude agent", "NewClaudeAgentCommand"),
        ("start a new cloud agent", "NewClaudeAgentCommand"),
        ("create a clawed subagent", "CreateClaudeSubagentCommand"),
        ("show called agents", "ShowClaudeAgentsCommand"),
        ("resume cloud agent", "ResumeClaudeAgentCommand"),
    ):
        assert (phrase, entity) in fake.registrations
    for phrase, entity in (
        ("write", "WriteKeyword"),
        ("type", "TypeKeyword"),
        ("speak", "SpeakKeyword"),
        ("talk", "TalkKeyword"),
    ):
        assert (phrase, entity) in fake.registrations
    for phrase in ("mute mic", "mute microphone"):
        assert (
            phrase,
            "MuteSystemMicrophoneCommand",
        ) in fake.registrations
    for phrase in ("mute system", "mute everything"):
        assert (
            phrase,
            "MuteSystemAudioCommand",
        ) in fake.registrations
    for phrase in ("mute jarvis", "stop jarvis listening"):
        assert (
            phrase,
            "MuteJarvisCommand",
        ) in fake.registrations
    for phrase in (
        "press enter", "press return", "press send", "hit enter", "hit return",
    ):
        assert (phrase, "PressEnterCommand") in fake.registrations
    for phrase in ("minimize everything", "minimise everything", "hide everything"):
        assert (phrase, "ShowDesktopCommand") in fake.registrations
    for phrase in ("new line", "newline", "insert new line", "add a new line"):
        assert (phrase, "InsertNewLineCommand") in fake.registrations
    for phrase in ("full stop", "period", "insert a full stop", "add a period"):
        assert (phrase, "InsertPeriodCommand") in fake.registrations
    for phrase in ("press escape", "press esc", "hit escape", "escape key"):
        assert (phrase, "PressEscapeCommand") in fake.registrations
    media_commands = {
        "PlayMediaCommand": (
            "play media", "resume playback", "resume music",
            "start the music", "start the song again",
        ),
        "PromptMusicCommand": ("play music", "lay music", "put some music on"),
        "PauseMediaCommand": (
            "pause media", "pause playback", "pause music", "poze music",
            "stop music", "stop the song", "stop the track",
        ),
        "StopMediaCommand": ("stop media", "stop playback", "stop playing"),
        "NextMediaCommand": ("next track", "next song", "skip track"),
        "PreviousMediaCommand": (
            "previous track", "previous song", "go back one track", "back track",
        ),
    }
    for entity, phrases in media_commands.items():
        for phrase in phrases:
            assert (phrase, entity) in fake.registrations
    assert ("stop music", "StopMediaCommand") not in fake.registrations
    assert ("stop the song", "StopMediaCommand") not in fake.registrations
    assert not any(phrase in {"pose", "poze", "lay"}
                   for phrase, _entity in fake.registrations)
    for phrase in ("caps lock on", "enable caps lock"):
        assert (phrase, "CapsLockOnCommand") in fake.registrations
    for phrase in ("caps lock off", "disable caps lock"):
        assert (phrase, "CapsLockOffCommand") in fake.registrations
    for phrase in (
        "focus hermes composer", "open hermes model picker",
        "new line in hermes", "queue hermes message",
        "send next hermes message", "open hermes commands",
        "reference file in hermes", "cancel hermes run",
    ):
        assert (phrase, "HermesComposerCommand") in fake.registrations
    for phrase in (
        "close app", "closed app", "close the app", "closed the app",
        "close this app", "closed this app",
    ):
        assert (phrase, "CloseFocusedWindowCommand") in fake.registrations
    for phrase in (
        "read window",
        "read this window",
        "read current window",
        "read the complete page",
        "please read the complete page",
        "read the whole page",
        "please read the whole page",
    ):
        assert (
            phrase,
            "ReadVisiblePageCommand",
        ) in fake.registrations
    for phrase in (
        "new note",
        "create a new note",
        "create new note",
        "make a new note",
        "make new note",
    ):
        assert (phrase, "NewNoteCommand") in fake.registrations
    for phrase in (
        "search page", "search this page", "search the page",
        "find on page", "find on this page", "search document",
        "search this document", "find in this document",
        "search this note", "find in this note",
        "search this node", "find in this node",
    ):
        assert (phrase, "SearchFocusedContentCommand") in fake.registrations
    for phrase in (
        "search notes", "search my notes", "find a note",
        "find note", "look up a note", "look up notes",
        "look up my notes", "look for a note", "look for notes",
    ):
        assert (phrase, "SearchNotesCommand") in fake.registrations
    for phrase in (
        "press tab", "tab", "next field", "next box",
        "go to next field", "go to the next field",
        "move to next field", "move to the next field",
    ):
        assert (phrase, "PressTabCommand") in fake.registrations
    for phrase in (
        "press shift tab", "shift tab", "previous field", "previous box",
        "go to previous field", "go to the previous field",
        "move to previous field", "move to the previous field",
    ):
        assert (phrase, "PressShiftTabCommand") in fake.registrations
    for phrase in (
        "new email", "create new email", "create an email",
        "compose email", "compose an email", "write a new email",
        "write an email",
    ):
        assert (phrase, "NewEmailCommand") in fake.registrations
    for phrase in (
        "search mail", "search my mail", "search email", "search my email",
        "find an email", "find email", "look up an email", "look through my mail",
    ):
        assert (phrase, "SearchMailCommand") in fake.registrations
    for phrase in (
        "join meeting", "join the meeting", "join zoom meeting",
        "join the zoom meeting", "join copied meeting",
        "join copied zoom meeting",
    ):
        assert (phrase, "JoinZoomMeetingCommand") in fake.registrations
    for phrase in (
        "search youtube", "search you tube", "search on youtube",
        "search in youtube", "youtube search", "you tube search",
    ):
        assert (phrase, "YouTubeSearchPromptCommand") in fake.registrations
    for phrase in (
        "go to youtube shorts", "open youtube shorts", "youtube shorts",
        "show youtube shorts", "go to youtube reels",
        "open youtube reels", "youtube reels", "show youtube reels",
    ):
        assert (phrase, "YouTubeShortsCommand") in fake.registrations
    assert len(fake._browser_navigation_actions) == 72
    assert set(fake._desktop_app_aliases) == {
        "brave", "firefox", "signal", "zoom", "terminal", "notes",
        "office", "claude", "chatgpt", "hermes", "mail", "proton_mail",
        "calendar",
    }
    action_verbs = {
        "OpenDesktopAppCommand": ("open", "launch", "start"),
        "FocusDesktopAppCommand": (
            "focus", "show", "go to", "bring up", "switch to"
        ),
        "MinimizeDesktopAppCommand": (
            "minimize", "minimise", "hide", "put away"
        ),
        "CloseDesktopAppCommand": ("close", "quit", "exit"),
        "MaximizeDesktopAppCommand": (
            "maximize", "maximise", "make full screen", "make fullscreen"
        ),
    }
    registrations = set(fake.registrations)
    for aliases in fake._desktop_app_aliases.values():
        for alias in aliases:
            for entity, verbs in action_verbs.items():
                for verb in verbs:
                    assert (f"{verb} {alias}", entity) in registrations
            assert (f"show me {alias}", "FocusDesktopAppCommand") in registrations
            assert (f"show me the {alias} window", "FocusDesktopAppCommand") in registrations
    for phrase in (
        "read app", "read this app", "read application",
        "read this application", "read screen", "read this screen",
        "read content", "read this content", "read full page",
        "read the full page", "read the entire page",
    ):
        assert (phrase, "ReadVisiblePageCommand") in registrations

    assert ("go back one track", "PreviousMediaCommand") in registrations
    assert ("send the message", "PressEnterCommand") in registrations
    assert ("submit", "PressEnterCommand") in registrations

    profiles = sorted((ROOT / "profiles").glob("*.json"))
    assert {path.name for path in profiles} == EXPECTED_PROFILES
    for path in profiles:
        raw_profile = json.loads(path.read_text())
        profile_namespace["resolve_profile"](raw_profile)

    try:
        profile_namespace["resolve_profile"]({
            "applications": {"notes": "terminal"},
        })
    except ValueError:
        pass
    else:
        raise AssertionError("Incompatible category mapping was accepted")

    install_import_stubs()
    sys.path.insert(0, str(ROOT))
    package = __import__("ovos_skill_jarvis_dispatcher")
    skill = package.create_skill()
    assert type(skill).__name__ == "JarvisDispatcherSkill"

    from ovos_skill_jarvis_dispatcher.custom_commands import (
        collect_builtin_inventory,
        read_mapping,
        validate_mapping,
        write_mapping,
    )

    assert validate_mapping(
        {"show my notes": "application.open.notes"},
        profile=reference_profile,
        builtin_phrases={"open notes"},
    ) == {"show my notes": "application.open.notes"}
    try:
        validate_mapping(
            {"open notes": "application.open.notes"},
            profile=reference_profile,
            builtin_phrases={"open notes"},
        )
    except ValueError:
        pass
    else:
        raise AssertionError("A built-in phrase collision was accepted")

    inventory = collect_builtin_inventory(reference_profile)
    assert set(inventory["mail.new"]) == {
        "new email", "create new email", "create an email",
        "compose email", "compose an email", "write a new email",
        "write an email",
    }
    assert set(inventory["browser.search_youtube"]) == {
        "search youtube", "search you tube", "search on youtube",
        "search in youtube", "youtube search", "you tube search",
    }
    assert set(inventory["browser.youtube_shorts"]) == {
        "go to youtube shorts", "open youtube shorts", "youtube shorts",
        "show youtube shorts", "go to youtube reels",
        "open youtube reels", "youtube reels", "show youtube reels",
    }
    assert set(inventory["hermes.focus_composer"]) == {
        "focus hermes composer", "go to hermes composer",
        "focus the hermes composer", "focus composer in hermes",
    }
    assert set(inventory["hermes.command_palette"]) == {
        "open hermes commands", "show hermes commands",
        "open hermes slash commands", "show hermes command palette",
    }
    with tempfile.TemporaryDirectory() as directory:
        custom_path = Path(directory) / "custom-commands.json"
        written = write_mapping(
            {"show my notes": "application.open.notes"},
            path=custom_path,
            profile=reference_profile,
            builtin_phrases={"open notes"},
        )
        assert read_mapping(
            path=custom_path,
            profile=reference_profile,
            builtin_phrases={"open notes"},
        ) == written
        assert stat.S_IMODE(custom_path.stat().st_mode) == 0o600

    current_documents = sorted(ROOT.rglob("*.md"))
    link_pattern = re.compile(r"\[[^]]+\]\(([^)]+)\)")
    for document in current_documents:
        assert document.is_file(), f"Current document is missing: {document}"
        for target in link_pattern.findall(document.read_text(encoding="utf-8")):
            relative = target.split("#", 1)[0]
            if (
                relative
                and "://" not in relative
                and not relative.startswith("mailto:")
            ):
                assert (document.parent / relative).resolve().exists(), (
                    f"Broken link in {document.relative_to(ROOT)}: {target}"
                )

    agents_guide = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for required in (
        "## Mandatory reading order",
        "## Command-system update map",
        "action_registry.py",
        "vocabulary.py",
        "custom_commands.py",
        "router_catalog()",
        "Control Centre Commands page",
        "never use a root-owned checkout or temporary directory",
        "docs/releases.md",
        "docs/troubleshooting.md",
        "docs/12-decisions.md",
    ):
        assert required in agents_guide, f"AGENTS.md is missing: {required}"

    instruction_adapters = {
        "CLAUDE.md": "AGENTS.md",
        "GEMINI.md": "AGENTS.md",
        ".github/copilot-instructions.md": "AGENTS.md",
    }
    for relative, canonical in instruction_adapters.items():
        adapter = (ROOT / relative).read_text(encoding="utf-8")
        assert canonical in adapter
        assert len(adapter.splitlines()) <= 6, (
            f"{relative} must remain a pointer, not a duplicate policy"
        )

    release_record = (ROOT / "docs/releases.md").read_text(encoding="utf-8")
    assert f"## {PROJECT_VERSION}" in release_record
    assert "docs/releases.md" in agents_guide
    ai_report_source = (ROOT / "scripts/create_ai_report.py").read_text(
        encoding="utf-8"
    )
    assert '"AGENTS.md"' in ai_report_source
    assert "Start with `source/AGENTS.md`" in ai_report_source

    print(f"PASS: {len(python_files)} Python modules compile")
    print(f"PASS: {len(intents)} intents match the expected inventory")
    print(f"PASS: {len(fake.registrations)} compatibility vocabulary registrations are present")
    print("PASS: vocabulary registrations and entities are consistent")
    print("PASS: personal phrase validation rejects built-in collisions")
    print("PASS: personal phrases save atomically with private permissions")
    print("PASS: built-in phrases are grouped by editor action")
    print("PASS: every app alias has open, focus, minimise, maximise and close coverage")
    print(f"PASS: {len(EXPECTED_PROFILES)} deployment profiles validate")
    print(f"PASS: {len(EXPECTED_SYSTEM_HELPERS)} runtime helpers are packaged")
    print(f"PASS: {len(EXPECTED_SYSTEMD_TEMPLATES)} systemd templates validate")
    print("PASS: optional components and current documentation validate")
    print("PASS: package imports and create_skill() succeeds")


if __name__ == "__main__":
    main()
