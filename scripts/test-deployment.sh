#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_root="$(mktemp -d "${TMPDIR:-/tmp}/jarvis-deployment-test.XXXXXX")"

cleanup() {
  case "$test_root" in
    "${TMPDIR:-/tmp}"/jarvis-deployment-test.*)
      rm -rf -- "$test_root"
      ;;
  esac
}
trap cleanup EXIT

manifest_list() {
  python3 - "$repo_root/deployment-manifest.json" "$1" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(*data[sys.argv[2]], sep="\n")
PY
}

mapfile -t helpers < <(manifest_list runtime_helpers)

python3 "$repo_root/scripts/test-v3-routing.py"
python3 "$repo_root/scripts/test-isolated-media-routing.py"
python3 "$repo_root/scripts/test-intent-cleanup.py"
python3 "$repo_root/scripts/test-installer-progress.py"
python3 - "$repo_root/scripts/verify-wake-model.py" <<'PY'
import os
import subprocess
import sys
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    package = base / "openwakeword"
    package.mkdir()
    model = base / "hey_jarvis_v0.1.onnx"
    model.write_bytes(b"reviewed test model")
    (package / "__init__.py").write_text('''
from pathlib import Path

def get_pretrained_model_paths(inference_framework="tflite"):
    if inference_framework == "onnx":
        return [str(Path(__file__).parent.parent / "hey_jarvis_v0.1.onnx")]
    return [str(Path(__file__).parent.parent / "hey_jarvis_v0.1.tflite")]

class Model:
    def __init__(self, wakeword_models, inference_framework):
        assert inference_framework == "onnx"
        assert wakeword_models == [str(Path(__file__).parent.parent / "hey_jarvis_v0.1.onnx")]
        self.models = {"hey_jarvis": object()}
''', encoding="utf-8")
    environment = dict(os.environ, PYTHONPATH=directory)
    result = subprocess.run([sys.executable, sys.argv[1]],
                            env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(model)
    model.unlink()
    missing = subprocess.run([sys.executable, sys.argv[1]],
                             env=environment, capture_output=True, text=True)
    assert missing.returncode != 0
    assert "Hey Jarvis ONNX model" in missing.stderr
print("PASS: official ONNX model selected and missing model rejected")
PY
python3 - "$repo_root/scripts/configure-wakeword.py" <<'PY'
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("wake_setup", sys.argv[1])
wake = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wake)
with tempfile.TemporaryDirectory() as directory:
    model = Path(directory) / "hey_jarvis_v0.1.onnx"
    model.write_bytes(b"isolated test fixture")
    original = wake.configure({"hotwords": {"wake_up": {"listen": False}}},
                              "hey_jarvis", "hey jarvis", onnx_model=model)
    assert original["hotwords"]["wake_up"] == {"listen": False}
    assert original["hotwords"]["hey_jarvis"]["models"] == [str(model)]
    assert original["hotwords"]["hey_jarvis"]["threshold"] == 0.4
    assert original["listener"]["vad_pre_wake_enabled"] is False
    assert original["confirm_listening"] is True
    old = {"listener": {"wake_word": "hey_jarvis"},
           "hotwords": {"hey_jarvis": {"module": wake.OPENWAKEWORD_MODULE,
                                        "listen": True, "threshold": 0.5}}}
    upgraded = wake.ensure_default_onnx(old, model)
    assert upgraded["hotwords"]["hey_jarvis"] == {
        "module": wake.OPENWAKEWORD_MODULE, "listen": True, "threshold": 0.4,
        "models": [str(model)], "inference_framework": "onnx"}
    assert upgraded["listener"]["vad_pre_wake_enabled"] is False
    assert upgraded["confirm_listening"] is True
    assert wake.ensure_default_onnx(upgraded, model) == upgraded
    existing_path = Path(directory) / "saved.conf"
    existing_path.write_text(json.dumps(upgraded, separators=(",", ":")))
    preserved_bytes = existing_path.read_bytes()
    import subprocess
    subprocess.run([sys.executable, sys.argv[1], "--config", str(existing_path),
                    "--ensure-default-onnx", "--onnx-model", str(model)],
                   check=True, capture_output=True)
    assert existing_path.read_bytes() == preserved_bytes
    custom = {"listener": {"wake_word": "hello_jarvis"}, "hotwords": {
        "hello_jarvis": {"module": wake.VOSK_MODULE, "listen": True}}}
    assert wake.ensure_default_onnx(custom, model) == custom
    try:
        wake.ensure_default_onnx({"listener": {"wake_word": "hey_jarvis"},
                                  "hotwords": {"hey_jarvis": {"module": wake.OPENWAKEWORD_MODULE,
                                       "models": ["private-custom.tflite"]}}}, model)
    except ValueError:
        pass
    else:
        raise AssertionError("Custom wake model was silently replaced")
print("PASS: fresh ONNX wake and safe default-only upgrade")
PY
python3 - "$repo_root/scripts/relocate-ovos-launchers.py" <<'PY'
import importlib.util
import sys
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("relocate_ovos", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as directory:
    home = Path(directory)
    stage = home / ".local/state/jarvis/stage.test/ovos-venv"
    final = home / ".venvs/ovos"
    (stage / "bin").mkdir(parents=True)
    final.parent.mkdir(parents=True)
    (stage / "bin/python").write_text("#!/bin/sh\n")
    bad = stage / "bin/jarvis-root-temp"
    bad.write_text("#!/var/tmp/jarvis-ovos-root.missing/source/python\n")
    try:
        module.relocate(stage, final)
    except ValueError as error:
        assert "privileged installer scratch" in str(error)
    else:
        raise AssertionError("Privileged temporary launcher was accepted")
print("PASS: copied root scratch launchers cannot become runtime entry points")
PY
python3 "$repo_root/scripts/test-reading-qwen-routing.py"
python3 "$repo_root/scripts/test-reading-request-errors.py"
python3 "$repo_root/scripts/test-qwen-safe-workflows.py"
python3 "$repo_root/scripts/test-qwen-setup.py"
python3 "$repo_root/scripts/test-preferred-apps.py"
python3 "$repo_root/scripts/test-update-security.py"
python3 "$repo_root/scripts/test-v4-security.py"
python3 "$repo_root/scripts/test-release-privacy.py"
python3 "$repo_root/scripts/test-dependency-lock.py"
python3 "$repo_root/scripts/test-v4-handover.py"
python3 "$repo_root/scripts/test-startup-settings.py"
python3 "$repo_root/scripts/test-core-isolation-candidate.py"
python3 "$repo_root/scripts/test-boot-readiness.py"
python3 "$repo_root/scripts/test-lifecycle-hotfix.py"
python3 "$repo_root/scripts/test-runtime-provenance.py"
python3 "$repo_root/scripts/test-runtime-bundle.py"
python3 "$repo_root/scripts/test-wake-onnx-boundary.py"
python3 "$repo_root/scripts/test-hermes-message-safety.py"
python3 "$repo_root/scripts/test-control-update-cancel.py"
python3 "$repo_root/scripts/test-search-pacing.py"
python3 "$repo_root/scripts/test-media-browser-fallback.py"
python3 "$repo_root/scripts/test-browser-search-focus.py"
python3 "$repo_root/scripts/test-audio-config.py"
python3 "$repo_root/scripts/test-speech-note-dictation.py"
bash "$repo_root/scripts/test-speech-note-speed.sh"
python3 "$repo_root/scripts/test-settings-export.py"
python3 "$repo_root/extras/whisper-hints/test_update.py"
python3 "$repo_root/extras/listener-safety/test_update.py"
python3 "$repo_root/extras/ocp-stop-compat/test_update.py"
PYTHONPATH="$repo_root/plugins/jarvis-file-search" \
  python3 -m unittest discover -s "$repo_root/plugins/jarvis-file-search/tests" -q

# A check-only run on a fresh home must not create a deployment.
fresh_home="$test_root/fresh"
mkdir -p "$fresh_home"
JARVIS_HOME="$fresh_home" JARVIS_TEST_MODE=1 \
  bash "$repo_root/scripts/install.sh" --check
test ! -e "$fresh_home/.local/src/ovos-skill-jarvis-dispatcher"

# The doctor must retain a virtualenv launcher path even when it is a symlink
# to a uv-managed base interpreter; resolving it would lose venv site-packages.
python3 - "$repo_root/scripts/doctor.py" "$test_root" <<'PY'
import importlib.util
import os
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("jarvis_doctor", sys.argv[1])
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
home = Path(sys.argv[2]) / "doctor-home"
base = home / ".local/share/uv/python/base-python"
base.parent.mkdir(parents=True)
base.write_text("#!/bin/sh\n", encoding="utf-8")
base.chmod(0o755)
launcher = home / ".venvs/ovos/bin/python"
launcher.parent.mkdir(parents=True)
launcher.symlink_to(base)
found = module.locate_ovos_python(home, None)
assert found == launcher, (found, launcher)
assert found != base.resolve()

upgrade = module.POLICY["ovos"]["preserved_alpha_stack"]
assert module.reviewed_voice_versions(upgrade["core"]) == upgrade["voice"]
assert module.reviewed_voice_versions({**upgrade["core"], "ovos-workshop": "7.0.6"}) == {}

try:
    module.run_json([
        sys.executable,
        "-c",
        "import sys; sys.stderr.write('doctor-traceback-marker\\n'); sys.exit(7)",
    ])
except RuntimeError as error:
    message = str(error)
    assert "status 7" in message, message
    assert "doctor-traceback-marker" in message, message
else:
    raise AssertionError("run_json hid a failed probe")
PY

# Standard Notes is detected from normal desktop launchers as well as the
# reviewed command, Flatpak and AppImage locations.
python3 - "$repo_root/ovos_skill_jarvis_dispatcher/capabilities.py" "$test_root" <<'PY'
import importlib.util
import os
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("jarvis_capabilities", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
home = Path(sys.argv[2]) / "standard-notes-home"
applications = home / ".local/share/applications"
applications.mkdir(parents=True)
(applications / "standard-notes-appimage.desktop").write_text(
    "[Desktop Entry]\nName=Standard Notes\nExec=/opt/standard-notes\n",
    encoding="utf-8",
)
assert module._integration_present("standard_notes", home)

appimage_home = Path(sys.argv[2]) / "standard-notes-appimage-home"
appimage = appimage_home / "Applications/StandardNotes.AppImage"
appimage.parent.mkdir(parents=True)
appimage.write_bytes(b"AppImage fixture")
appimage.chmod(0o755)
assert module._integration_present("standard_notes", appimage_home)

# Recommended keeps the reviewed everyday mappings and also includes a visible
# desktop Calendar. Proton Mail remains separately visible and becomes the
# preferred generic Mail target.
calendar = applications / "org.gnome.Calendar.desktop"
calendar.write_text(
    "[Desktop Entry]\nType=Application\nName=Calendar\nExec=gnome-calendar\n",
    encoding="utf-8",
)
assert module._integration_present("system_calendar", home)
detected = {
    "notes": "standard_notes",
    "proton_mail": "proton_mail",
    "calendar": "proton_calendar",
    "system_calendar": "system_calendar",
}
recommended = module.recommended_applications(detected, home)
assert set(detected.values()) <= recommended
configured = module.build_configuration("recommended", detected, home=home)
assert configured["applications"]["notes"] == "standard_notes"
assert configured["applications"]["proton_mail"] == "proton_mail"
assert configured["applications"]["calendar"] == "proton_calendar"
assert configured["applications"]["system_calendar"] == "system_calendar"
assert configured["preferred_apps"] == {
    "notes": "notes", "mail": "proton_mail", "calendar": "calendar",
}
PY

# Standard Notes launch resolution uses the same portable locations accepted
# by capability detection, including the laptop's unhyphenated AppImage name.
notes_home="$test_root/notes-launch-home"
notes_bin="$test_root/notes-launch-bin"
notes_state="$test_root/notes-window.state"
notes_log="$test_root/notes-launch.log"
mkdir -p "$notes_home/Applications" "$notes_bin"
printf '%s\n' '#!/bin/sh' 'exit 0' > "$notes_home/Applications/StandardNotes.AppImage"
chmod 0755 "$notes_home/Applications/StandardNotes.AppImage"
python3 - "$notes_bin/wmctrl" "$notes_bin/xdotool" "$notes_bin/systemd-run" <<'PY'
import stat
import sys
from pathlib import Path

wmctrl, xdotool, systemd_run = map(Path, sys.argv[1:])
wmctrl.write_text(r'''#!/usr/bin/env bash
if [[ "$1" == "-lx" ]]; then
  if [[ -e "$JARVIS_NOTES_STATE" ]]; then
    echo '0x00001000  0 standard-notes.StandardNotes host Standard Notes'
  fi
  exit 0
fi
exit 0
''', encoding="utf-8")
xdotool.write_text(r'''#!/usr/bin/env bash
if [[ "$1" == "getactivewindow" ]]; then
  echo 4096
fi
exit 0
''', encoding="utf-8")
systemd_run.write_text(r'''#!/usr/bin/env bash
printf '%s\n' "$*" >> "$JARVIS_NOTES_LOG"
touch "$JARVIS_NOTES_STATE"
exit 0
''', encoding="utf-8")
for path in (wmctrl, xdotool, systemd_run):
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
PY
HOME="$notes_home" PATH="$notes_bin:$PATH" \
  JARVIS_SYSTEMD_RUN="$notes_bin/systemd-run" \
  JARVIS_NOTES_STATE="$notes_state" JARVIS_NOTES_LOG="$notes_log" \
  "$repo_root/system_helpers/jarvis-app-window" open standard_notes
grep -F -- "$notes_home/Applications/StandardNotes.AppImage" "$notes_log"

# The Bella pronunciation repair is guarded: it patches only the reviewed
# scriptconv layout, compiles the result and retains an exact backup.
python3 - "$repo_root/scripts/patch-pronunciation.py" "$test_root" <<'PY'
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("jarvis_pronunciation", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
root = Path(sys.argv[2])
source = root / "mul.py"
backup = root / "mul.py.backup"
source.write_text("""class Example:
    def method(self, lang):
                if self.g2p_en is None:
                    from misaki import en
                    self.g2p_en = en.G2P()
""", encoding="utf-8")
assert module.patch(source, backup) == "applied"
assert "from misaki.espeak import EspeakFallback" in source.read_text()
assert "self.g2p_en = en.G2P()" in backup.read_text()
assert module.patch(source) == "already-applied"

# The working reference system has the same fallback with harmless formatting differences.
# It must be recognised without rewriting the installed dependency.
reference_source = root / "mul-reference.py"
reference_layout = """class Example:
    def method(self, lang):
                if self.g2p_en is None:
                    from misaki import en
                    from misaki.espeak import EspeakFallback

                    british = lang == "en-GB"
                    self.g2p_en = en.G2P(
                        british=british,
                        fallback=EspeakFallback(british=british)
                    )
"""
reference_source.write_text(reference_layout, encoding="utf-8")
assert module.layout(reference_layout) == "already-applied"
assert module.patch(reference_source) == "already-applied"
assert reference_source.read_text(encoding="utf-8") == reference_layout

unknown = root / "mul-unknown.py"
unknown.write_text("self.g2p_en = something_unreviewed()\n", encoding="utf-8")
try:
    module.patch(unknown)
except RuntimeError as error:
    assert "not the reviewed layout" in str(error)
else:
    raise AssertionError("unknown pronunciation layout was accepted")
PY

# The installer pins the exact reviewed pipeline exported from the reference and
# preserves that order while verifying every stage is actually installed.
pipeline_config="$test_root/pipeline-user.json"
printf '%s\n' \
  '{"intents":{"pipeline":["ovos-adapt-pipeline-plugin-high"]},"unrelated":true}' \
  > "$pipeline_config"
chmod 0600 "$pipeline_config"
python3 "$repo_root/scripts/configure-intent-pipeline.py" \
  --config "$pipeline_config" \
  --available-plugin ovos-stop-pipeline-plugin \
  --available-plugin ovos-converse-pipeline-plugin \
  --available-plugin ovos-ocp-pipeline-plugin \
  --available-plugin ovos-adapt-pipeline-plugin \
  --available-plugin ovos-persona-pipeline-plugin \
  --available-plugin ovos-padatious-pipeline-plugin \
  --available-plugin ovos-fallback-pipeline-plugin \
  --available-plugin ovos-common-query-pipeline-plugin
python3 - "$pipeline_config" <<'PY'
import json
import stat
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
assert data == {
    "unrelated": True,
    "intents": {
        "pipeline": [
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
    },
}
assert stat.S_IMODE(path.stat().st_mode) == 0o600
PY

# Fresh installation creates a complete, self-contained source deployment.
JARVIS_HOME="$fresh_home" JARVIS_TEST_MODE=1 \
  bash "$repo_root/scripts/install.sh" --no-restart

fresh_target="$fresh_home/.local/src/ovos-skill-jarvis-dispatcher"
test -f "$fresh_target/pyproject.toml"
test -f "$fresh_target/compatibility.json"
test ! -e "$fresh_home/.config/jarvis/profile.json"
python3 - "$fresh_home/.config/jarvis/capabilities.json" <<'PY'
import json
import stat
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
assert data["mode"] == "recommended"
assert data["wake_phrase"] == "hey_jarvis"
assert data["wake_phrase_spoken"] == "hey jarvis"
assert data["listen_shortcut"] == "<Super>l"
assert data["microphone_shortcut"] == "<Shift><Super>l"
assert data["applications"] == {
    "brave": "brave", "firefox": "firefox", "terminal": "terminal"
}
assert data["private_extensions"] == {"agents": False}
assert stat.S_IMODE(path.stat().st_mode) == 0o600
PY
test -x "$fresh_home/.local/bin/jarvis-restart"
test -f "$fresh_home/.config/autostart/ovos-tray.desktop"
test -f "$fresh_home/.config/autostart/jarvis-voice.desktop"
grep -Fxq "Exec=$fresh_home/.local/bin/jarvis-setup --start-voice-at-login" \
  "$fresh_home/.config/autostart/jarvis-voice.desktop"
grep -Fxq 'X-GNOME-Autostart-Delay=5' \
  "$fresh_home/.config/autostart/ovos-tray.desktop"
grep -Fxq "TryExec=$fresh_home/.local/bin/ovos-tray" \
  "$fresh_home/.config/autostart/ovos-tray.desktop"
test -f "$fresh_home/.local/share/applications/jarvis-ovos.desktop"
grep -Fxq 'Name=Jarvis OVOS' \
  "$fresh_home/.local/share/applications/jarvis-ovos.desktop"
grep -Fxq "Exec=$fresh_home/.local/bin/jarvis-setup --gui" \
  "$fresh_home/.local/share/applications/jarvis-ovos.desktop"
grep -Fq '[[ "$argument" == --gui && -x "$tray" ]]' \
  "$fresh_home/.local/bin/jarvis-setup"
grep -Fq 'nohup "$tray"' "$fresh_home/.local/bin/jarvis-setup"
test ! -e "$fresh_home/.config/autostart/jarvis-mic-indicator.desktop"
test -f "$fresh_home/.local/share/ovos/sounds/jarvis-ready.wav"

# Full voice restarts avoid the message bus and start audio, listener and core
# in a deterministic order.  This prevents duplicate skill-discovery passes.
restart_log="$test_root/restart-order.log"
fake_systemctl="$test_root/fake-systemctl"
python3 - "$fake_systemctl" <<'PY'
import stat
import sys
from pathlib import Path

path = Path(sys.argv[1])
path.write_text("""#!/usr/bin/env bash
printf '%s\\n' \"$*\" >> \"$JARVIS_RESTART_LOG\"
exit 0
""", encoding="utf-8")
path.chmod(path.stat().st_mode | stat.S_IXUSR)
PY
JARVIS_SYSTEMCTL="$fake_systemctl" JARVIS_RESTART_LOG="$restart_log" \
  "$fresh_home/.local/bin/jarvis-restart" --full >/dev/null
python3 - "$restart_log" <<'PY'
import sys
from pathlib import Path

lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
actions = [line for line in lines if " is-active " not in f" {line} "]
assert actions == [
    "--user stop ovos-core.service ovos-listener.service ovos-audio.service",
    "--user start ovos-audio.service",
    "--user start ovos-listener.service",
    "--user start ovos-core.service",
], actions
assert all("ovos-messagebus" not in line for line in lines)
PY

# Focused navigation is a packaged, bounded helper. It targets only the
# verified active X11 window and refuses Cinnamon desktop/panel surfaces.
navigation_bin="$test_root/navigation-bin"
navigation_log="$test_root/navigation.log"
mkdir -p "$navigation_bin"
python3 - "$navigation_bin/xdotool" "$navigation_bin/xprop" <<'PY'
import stat
import sys
from pathlib import Path

xdotool = Path(sys.argv[1])
xdotool.write_text("""#!/usr/bin/env bash
if [[ \"$1\" == getactivewindow ]]; then
  echo 4242
elif [[ \"$1\" == key ]]; then
  printf '%s\\n' \"$*\" >> \"$JARVIS_NAVIGATION_LOG\"
else
  exit 2
fi
""", encoding="utf-8")
xdotool.chmod(xdotool.stat().st_mode | stat.S_IXUSR)

xprop = Path(sys.argv[2])
xprop.write_text("""#!/usr/bin/env bash
if [[ \"${@: -1}\" == WM_CLASS ]]; then
  printf 'WM_CLASS(STRING) = \"%s\", \"%s\"\\n' \\
    \"${JARVIS_TEST_WINDOW_CLASS:-Navigator}\" \\
    \"${JARVIS_TEST_WINDOW_CLASS:-Firefox}\"
else
  echo '_NET_WM_WINDOW_TYPE(ATOM) = _NET_WM_WINDOW_TYPE_NORMAL'
fi
""", encoding="utf-8")
xprop.chmod(xprop.stat().st_mode | stat.S_IXUSR)
PY
for action in scroll_down page_down top bottom; do
  PATH="$navigation_bin:$PATH" JARVIS_NAVIGATION_LOG="$navigation_log" \
    "$fresh_home/.local/bin/jarvis-focused-navigation" "$action"
done
python3 - "$navigation_log" <<'PY'
import sys
from pathlib import Path

assert Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() == [
    "key --clearmodifiers --repeat 4 --delay 50 Down",
    "key --clearmodifiers Page_Down",
    "key --clearmodifiers ctrl+Home",
    "key --clearmodifiers ctrl+End",
]
PY
if PATH="$navigation_bin:$PATH" JARVIS_NAVIGATION_LOG="$navigation_log" \
   JARVIS_TEST_WINDOW_CLASS="Cinnamon" \
   "$fresh_home/.local/bin/jarvis-focused-navigation" page_down 2>/dev/null; then
  echo "Focused navigation accepted the Cinnamon desktop" >&2
  exit 1
fi

python3 - "$fresh_home/.config/mycroft/mycroft.conf" <<'PY'
import json
import stat
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
assert data["listener"]["wake_word"] == "hey_jarvis"
assert data["listener"]["vad_pre_wake_enabled"] is False
assert data["hotwords"]["hey_jarvis"] == {
    "module": "ovos-ww-plugin-openwakeword",
    "listen": True,
    "threshold": 0.4,
    "inference_framework": "onnx",
    "models": [str(path.parents[2] / ".local/share/ovos/models/hey_jarvis_v0.1.onnx")],
}
assert data["listener"]["instant_listen"] is False
assert data["listener"]["fake_barge_in"] is True
assert "barge_in_delay" not in data["listener"]
assert data["listener"]["barge_in_volume"] == 20
assert data["confirm_listening"] is True
assert data["listener"]["VAD"] == {"module": "ovos-vad-plugin-silero"}
assert data["listener"]["microphone"] == {
    "module": "ovos-microphone-plugin-sounddevice",
    "ovos-microphone-plugin-sounddevice": {
        "fallback_module": "ovos-microphone-plugin-alsa"
    },
    "ovos-microphone-plugin-alsa": {},
}
assert data["stt"] == {
    "module": "ovos-stt-plugin-fasterwhisper",
    "ovos-stt-plugin-fasterwhisper": {
        "model": "small.en", "use_cuda": False, "compute_type": "int8",
        "beam_size": 1, "cpu_threads": 8, "vad_filter": True,
    },
}
assert data["tts"]["module"] == "ovos-tts-plugin-phoonnx"
assert data["tts"]["ovos-tts-plugin-phoonnx"]["voice"] == "kokoro/af_bella"
assert data["sounds"]["start_listening"].endswith(
    "/.local/share/ovos/sounds/jarvis-ready.wav"
)
assert data["play_wav_cmdline"] == "play %1 pad 0.15 0.25"
assert stat.S_IMODE(path.stat().st_mode) == 0o600
PY

# Wake phrase changes remain user-space, remove only the previously managed
# Vosk entry for an arbitrary custom phrase, and update both OVOS and Jarvis
# configuration atomically.
JARVIS_HOME="$fresh_home" JARVIS_TEST_MODE=1 \
  "$fresh_home/.local/bin/jarvis-wake-phrase" --phrase "hello jarvis"
python3 - "$fresh_home/.config/mycroft/mycroft.conf" \
  "$fresh_home/.config/jarvis/capabilities.json" <<'PY'
import json
import sys
from pathlib import Path

ovos = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
capabilities = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
assert ovos["listener"]["wake_word"] == "hello_jarvis"
assert ovos["hotwords"]["hello_jarvis"]["samples"] == ["hello jarvis"]
assert ovos["hotwords"]["hello_jarvis"]["module"] == "ovos-ww-plugin-vosk"
assert "hey_jarvis" not in ovos["hotwords"]
assert capabilities["wake_phrase"] == "hello_jarvis"
assert capabilities["wake_phrase_spoken"] == "hello jarvis"
PY

# Cinnamon shortcut management preserves conflicting built-ins, keeps the
# lock shortcut, updates the Jarvis custom binding and restores snapshots.
shortcut_bin="$test_root/shortcut-bin"
shortcut_store="$test_root/gsettings.json"
shortcut_snapshot="$test_root/gsettings-snapshot.json"
mkdir -p "$shortcut_bin"
python3 - "$shortcut_bin/gsettings" <<'PY'
import stat
import sys
from pathlib import Path

path = Path(sys.argv[1])
path.write_text(r'''#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

store = Path(os.environ["FAKE_GSETTINGS_STORE"])
if store.exists():
    data = json.loads(store.read_text())
else:
    data = {
        "org.cinnamon.desktop.keybindings": {
            "custom-list": "['custom0', 'custom1', 'jarvis-listen', 'jarvis-microphone-toggle']",
            "looking-glass-keybinding": "['<Super>l']",
        },
        "org.cinnamon.desktop.keybindings.media-keys": {
            "screensaver": "['<Control><Alt>l', 'XF86ScreenSaver']",
        },
        "org.cinnamon.desktop.keybindings.custom-keybinding:/org/cinnamon/desktop/keybindings/custom-keybindings/custom0/": {
            "name": "'Read Selected Text'", "command": "'/usr/bin/true'",
            "binding": "['<Control><Alt>r']",
        },
        "org.cinnamon.desktop.keybindings.custom-keybinding:/org/cinnamon/desktop/keybindings/custom-keybindings/custom1/": {
            "name": "'Voice Dictation'", "command": "'/usr/bin/true'",
            "binding": "['<Control><Alt>e']",
        },
        "org.cinnamon.desktop.keybindings.custom-keybinding:/org/cinnamon/desktop/keybindings/custom-keybindings/jarvis-listen/": {
            "name": "'Jarvis Listen'", "command": "'/old/ovos-listen'",
            "binding": "['<Super>l']",
        },
        "org.cinnamon.desktop.keybindings.custom-keybinding:/org/cinnamon/desktop/keybindings/custom-keybindings/jarvis-microphone-toggle/": {
            "name": "'Jarvis Microphone Toggle'", "command": "'/old/jarvis-mic-toggle'",
            "binding": "['<Shift><Super>l']",
        },
    }

command = sys.argv[1]
if command == "list-schemas":
    print("org.cinnamon.desktop.keybindings")
    print("org.cinnamon.desktop.keybindings.media-keys")
elif command == "list-relocatable-schemas":
    print("org.cinnamon.desktop.keybindings.custom-keybinding")
elif command == "list-keys":
    print(*data[sys.argv[2]].keys(), sep="\n")
elif command == "get":
    data.setdefault(sys.argv[2], {"name": "''", "command": "''", "binding": "[]"})
    print(data[sys.argv[2]][sys.argv[3]])
elif command == "set":
    data.setdefault(sys.argv[2], {})[sys.argv[3]] = sys.argv[4]
    store.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    if os.environ.get("FAKE_GSETTINGS_LOG"):
        with Path(os.environ["FAKE_GSETTINGS_LOG"]).open("a") as output:
            output.write(json.dumps(sys.argv[2:]) + "\n")
else:
    raise SystemExit(2)
''', encoding="utf-8")
path.chmod(path.stat().st_mode | stat.S_IXUSR)
PY
FAKE_GSETTINGS_STORE="$shortcut_store" PATH="$shortcut_bin:$PATH" \
  JARVIS_HOME="$fresh_home" python3 "$fresh_target/scripts/listen-shortcut.py" \
  --snapshot "$shortcut_snapshot"
FAKE_GSETTINGS_STORE="$shortcut_store" PATH="$shortcut_bin:$PATH" \
  FAKE_GSETTINGS_LOG="$test_root/gsettings.log" JARVIS_HOME="$fresh_home" \
  python3 "$fresh_target/scripts/listen-shortcut.py" \
  --shortcut '<Super>l'
python3 - "$shortcut_store" "$fresh_home/.config/jarvis/capabilities.json" \
  "$test_root/gsettings.log" <<'PY'
import ast
import json
import sys
from pathlib import Path

settings = json.loads(Path(sys.argv[1]).read_text())
caps = json.loads(Path(sys.argv[2]).read_text())
parent = settings["org.cinnamon.desktop.keybindings"]
custom = settings[
    "org.cinnamon.desktop.keybindings.custom-keybinding:/org/cinnamon/desktop/keybindings/custom-keybindings/custom2/"
]
microphone = settings[
    "org.cinnamon.desktop.keybindings.custom-keybinding:/org/cinnamon/desktop/keybindings/custom-keybindings/custom3/"
]
assert ast.literal_eval(parent["custom-list"]) == [
    "custom0", "custom1", "custom2", "custom3"
]
assert ast.literal_eval(parent["looking-glass-keybinding"]) == []
assert ast.literal_eval(custom["binding"]) == ["<Super>l"]
assert ast.literal_eval(custom["command"]).endswith("/.venvs/ovos/bin/ovos-listen")
assert ast.literal_eval(microphone["binding"]) == ["<Shift><Super>l"]
assert ast.literal_eval(microphone["command"]).endswith("/.local/bin/jarvis-mic-toggle")
assert caps["listen_shortcut"] == "<Super>l"
assert caps["microphone_shortcut"] == "<Shift><Super>l"
state = json.loads(
    (Path(sys.argv[2]).parent / "listen-shortcut.json").read_text()
)
assert state["listen_entry"] == "custom2"
assert state["microphone_entry"] == "custom3"

# Cinnamon activates a customN entry when it appears in custom-list. Both
# targets therefore have to be fully populated before that parent write.
operations = [
    json.loads(line) for line in Path(sys.argv[3]).read_text().splitlines()
]
parent_index = next(
    index for index, operation in enumerate(operations)
    if operation[0] == "org.cinnamon.desktop.keybindings"
    and operation[1] == "custom-list"
)
for entry in ("custom2", "custom3"):
    target_fragment = f"/custom-keybindings/{entry}/"
    field_indices = [
        index for index, operation in enumerate(operations)
        if target_fragment in operation[0]
        and operation[1] in {"name", "command", "binding"}
    ]
    assert len(field_indices) == 3, (entry, operations)
    assert max(field_indices) < parent_index, (entry, operations)
PY
FAKE_GSETTINGS_STORE="$shortcut_store" PATH="$shortcut_bin:$PATH" \
  JARVIS_HOME="$fresh_home" python3 "$fresh_target/scripts/listen-shortcut.py" \
  --shortcut '<Super>j'
python3 - "$shortcut_store" <<'PY'
import ast
import json
import sys
from pathlib import Path
settings = json.loads(Path(sys.argv[1]).read_text())
assert ast.literal_eval(
    settings["org.cinnamon.desktop.keybindings"]["looking-glass-keybinding"]
) == ["<Super>l"]
PY
FAKE_GSETTINGS_STORE="$shortcut_store" PATH="$shortcut_bin:$PATH" \
  python3 "$fresh_target/scripts/listen-shortcut.py" \
  --restore-snapshot "$shortcut_snapshot"
python3 - "$shortcut_store" <<'PY'
import ast
import json
import sys
from pathlib import Path
settings = json.loads(Path(sys.argv[1]).read_text())
parent = settings["org.cinnamon.desktop.keybindings"]
assert ast.literal_eval(parent["custom-list"]) == [
    "custom0", "custom1", "jarvis-listen", "jarvis-microphone-toggle"
]
assert ast.literal_eval(parent["looking-glass-keybinding"]) == ["<Super>l"]
PY

# An activated virtualenv must not capture GTK desktop helpers. This fake
# python3 records accidental PATH-based use; jarvis-setup must bypass it.
fake_venv="$test_root/activated-venv/bin"
fake_python_log="$test_root/activated-venv-python.log"
mkdir -p "$fake_venv"
FAKE_PYTHON_LOG="$fake_python_log" python3 - "$fake_venv/python3" <<'PY'
import stat
import sys
from pathlib import Path

path = Path(sys.argv[1])
path.write_text("""#!/usr/bin/env bash
printf '%s\\n' invoked >> "$FAKE_PYTHON_LOG"
exec /usr/bin/python3 "$@"
""", encoding="utf-8")
path.chmod(path.stat().st_mode | stat.S_IXUSR)
PY
PATH="$fake_venv:$PATH" FAKE_PYTHON_LOG="$fake_python_log" \
  JARVIS_HOME="$fresh_home" \
  "$fresh_home/.local/bin/jarvis-setup" --mode custom \
  --output "$test_root/venv-safe-core.json" --no-restart
test ! -e "$fake_python_log"

# Setup supports an empty custom selection and a reviewed app selection.
JARVIS_HOME="$fresh_home" JARVIS_TEST_MODE=1 \
  python3 "$fresh_target/scripts/setup.py" --mode custom \
  --output "$test_root/core.json" --no-restart
JARVIS_HOME="$fresh_home" JARVIS_TEST_MODE=1 \
  python3 "$fresh_target/scripts/setup.py" --mode custom --apps firefox \
  --output "$test_root/custom.json" --no-restart
JARVIS_HOME="$fresh_home" JARVIS_TEST_MODE=1 \
  JARVIS_TEST_PRIVATE_AGENTS=1 \
  JARVIS_TEST_DETECTED_APPS=brave,firefox,terminal,onlyoffice,signal,zoom,calculator,standard_notes,hermes_desktop,proton_mail,proton_calendar \
  python3 "$fresh_target/scripts/setup.py" --mode recommended \
  --output "$test_root/recommended.json" --no-restart
JARVIS_HOME="$fresh_home" JARVIS_TEST_MODE=1 \
  JARVIS_TEST_DETECTED_APPS=brave,onlyoffice \
  python3 "$fresh_target/scripts/setup.py" --mode all \
  --output "$test_root/all.json" --no-restart
python3 - "$test_root/core.json" "$test_root/custom.json" \
  "$test_root/recommended.json" "$test_root/all.json" <<'PY'
import json
import sys
from pathlib import Path

core = json.loads(Path(sys.argv[1]).read_text())
custom = json.loads(Path(sys.argv[2]).read_text())
recommended = json.loads(Path(sys.argv[3]).read_text())
all_apps = json.loads(Path(sys.argv[4]).read_text())
assert core["applications"] == {}
assert custom["applications"] == {"firefox": "firefox"}
assert recommended["mode"] == "recommended"
assert set(recommended["applications"].values()) == {
    "brave", "firefox", "terminal", "signal", "zoom", "calculator",
    "standard_notes", "hermes_desktop", "proton_mail", "proton_calendar",
    "onlyoffice",
}
assert recommended["private_extensions"] == {"agents": True}
assert all_apps["mode"] == "all-detected"
assert set(all_apps["applications"].values()) == {"brave", "onlyoffice"}
PY

# The optional Speech Note add-on uses only a per-user Flatpak installation.
fake_bin="$test_root/fake-bin"
fake_state="$test_root/fake-flatpak-state"
fake_log="$test_root/fake-flatpak.log"
mkdir -p "$fake_bin"
FAKE_STATE="$fake_state" FAKE_LOG="$fake_log" python3 - "$fake_bin/flatpak" <<'PY'
import os
import stat
import sys
from pathlib import Path

path = Path(sys.argv[1])
path.write_text("""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' \"$*\" >> \"$FAKE_LOG\"
if [[ \"${1:-}\" == info && \"${2:-}\" == --show-version ]]; then
  [[ -f \"$FAKE_STATE\" ]] || exit 1
  echo 4.8.4
elif [[ \"${1:-}\" == info ]]; then
  [[ -f \"$FAKE_STATE\" ]]
elif [[ \"${1:-}\" == remotes ]]; then
  :
elif [[ \"${1:-}\" == remote-add ]]; then
  :
elif [[ \"${1:-}\" == install ]]; then
  : > \"$FAKE_STATE\"
else
  exit 2
fi
""", encoding="utf-8")
path.chmod(path.stat().st_mode | stat.S_IXUSR)
PY
FAKE_STATE="$fake_state" FAKE_LOG="$fake_log" PATH="$fake_bin:$PATH" \
  "$fresh_home/.local/bin/jarvis-speechnote-setup" --install --yes
grep -q '^remote-add --user --if-not-exists flathub ' "$fake_log"
grep -q '^install --user --noninteractive flathub net.mkiol.SpeechNote$' "$fake_log"

# Normal setup cannot enable private agents, while an existing named reference system
# profile retains its already-customised extension during migration only.
JARVIS_HOME="$fresh_home" JARVIS_TEST_MODE=1 \
  python3 "$fresh_target/scripts/setup.py" \
  --migrate-profile "$repo_root/profiles/reference.json" \
  --output "$test_root/migrated-reference.json" --no-restart
python3 - "$test_root/migrated-reference.json" <<'PY'
import json
import sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
assert data["private_extensions"] == {"agents": True}
PY

# A disabled/private-window periodic check is read-only and exits quietly.
printf '%s\n' '{"repository": null}' > "$fresh_home/.config/jarvis/update.json"
JARVIS_HOME="$fresh_home" python3 "$fresh_target/scripts/update.py" check --quiet
for helper in "${helpers[@]}"; do
  cmp "$repo_root/system_helpers/$helper" "$fresh_home/.local/bin/$helper"
done
for unit in \
  hermes-launcher-repair.service \
  hermes-launcher-repair.path \
  jarvis-health-check.service \
  jarvis-health-check.timer \
  jarvis-update-check.service \
  jarvis-update-check.timer; do
  test -f "$fresh_home/.config/systemd/user/$unit"
done
grep -q '^OnCalendar=monthly$' \
  "$fresh_home/.config/systemd/user/jarvis-update-check.timer"
! grep -q '^OnUnitActiveSec=' \
  "$fresh_home/.config/systemd/user/jarvis-update-check.timer"
for state in ready starting stopped failed; do
  test -f "$fresh_home/.local/share/icons/ovos-tray/ovos-$state-update.svg"
done
HOME="$fresh_home" python3 - "$fresh_target/scripts/control_runtime.py" <<'PY'
import importlib.util
import json
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("control_runtime", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
state = Path.home() / ".local/state/jarvis"
updates = state / "updates/latest.json"
updates.parent.mkdir(parents=True, exist_ok=True)
(state / "current.json").write_text(json.dumps({"version": "2.3.1"}))
updates.write_text(json.dumps({"latest": "3.0.0", "release_date": "2026-09-27", "update_available": True}))
assert module.update_available() == "3.0.0"
assert module.update_status() == {
    "installed": "2.3.1", "latest": "3.0.0",
    "release_date": "2026-09-27", "available": True,
    "checked": False, "failed": False,
}
updates.write_text(json.dumps({"latest": "2.3.1", "update_available": True}))
assert module.update_available() is None
updates.write_text(json.dumps({"latest": "3.0.0", "update_available": True}))
(state / "current.json").write_text(json.dumps({"version": "3.0.0rc1"}))
assert module.update_available() == "3.0.0"
from unittest.mock import patch
with patch.object(module, 'run') as run:
    run.return_value.returncode = 0
    run.return_value.stdout = 'Update installed.\n'
    run.return_value.stderr = ''
    assert module.maintenance('install') == 'Update installed.'
    assert run.call_args.args[0] == [str(Path.home() / '.local/bin/jarvis-update'),
                                      'install', '--yes']
helper = Path(sys.argv[1]).with_name('relaunch-control-center.py')
launcher = Path.home() / '.local/bin/jarvis-setup'
helper.touch(exist_ok=True)
launcher.parent.mkdir(parents=True, exist_ok=True)
launcher.touch(exist_ok=True)
with patch.object(module.subprocess, 'Popen') as popen:
    popen.return_value.pid = 987
    assert module.relaunch_control_center(wait_pid=123) == 987
    command = popen.call_args.args[0]
    assert command[1:] == [str(helper), '--wait-pid', '123',
                           '--launcher', str(launcher)]
    assert popen.call_args.kwargs['start_new_session'] is True
with patch.object(module, 'run') as run:
    run.return_value.returncode = 0
    run.return_value.stdout = 'Speech Note installed\n'
    run.return_value.stderr = ''
    assert module.speech_note_status() == {
        'installed': True, 'detail': 'Speech Note installed'}
    assert run.call_args.args[0] == [
        Path.home() / '.local/bin/jarvis-speechnote-setup', '--status']
with patch.object(module, 'run') as run:
    run.side_effect = [
        __import__('subprocess').CompletedProcess([], 0, 'Speech Note installed.\n', ''),
        __import__('subprocess').CompletedProcess([], 0, 'Speech Note opened.\n', ''),
    ]
    assert module.speech_note_action('install') == (
        'Speech Note installed.\nSpeech Note opened.')
    assert run.call_args_list[0].args[0] == [
        Path.home() / '.local/bin/jarvis-speechnote-setup', '--install', '--yes']
    assert run.call_args_list[1].args[0] == [
        Path.home() / '.local/bin/jarvis-speechnote-setup', '--open']
inactive={unit:{'ActiveState':'inactive'} for unit in module.UNITS}
assert module.audio_settings() == {'enabled':True,'volume':20}
with patch.object(module,'snapshot',return_value=inactive):
    assert module.voice_setting('audio',[False,35]) == 'Background audio while listening saved.'
assert module.audio_settings() == {'enabled':False,'volume':35}
saved=json.loads((Path.home()/'.config/mycroft/mycroft.conf').read_text())
assert saved['stt']['ovos-stt-plugin-fasterwhisper']['vad_filter'] is True
with patch.object(module,'snapshot',return_value=inactive):
    module.voice_setting('audio',[True,20])
assert module.audio_settings() == {'enabled':True,'volume':20}
updater_path = Path(sys.argv[1]).with_name('update.py')
updater_spec = importlib.util.spec_from_file_location('jarvis_updater', updater_path)
updater = importlib.util.module_from_spec(updater_spec)
updater_spec.loader.exec_module(updater)
assert updater.version_key('3.0.0rc1') < updater.version_key('3.0.0')
assert updater.version_key('v3.0.0') > updater.version_key('2.3.1')
private_log = "Session({'location': {'lat': 25.7701, 'lon': -80.1928, 'tz': 'America/New_York'}})"
safe_log = module.sanitise_log_text(private_log)
assert '25.7701' not in safe_log and '-80.1928' not in safe_log
assert '<redacted-location>' in safe_log
PY

# The AI bundle is bounded, self-describing and redacts supplied secret shapes.
report="$test_root/ai-report.tar.gz"
JARVIS_HOME="$fresh_home" JARVIS_REPOSITORY="$fresh_target" JARVIS_TEST_MODE=1 \
  "$fresh_home/.local/bin/jarvis-report" \
  --issue "Contact person@example.com with api_key=DO-NOT-SHARE location={'lat': 25.7701, 'lon': -80.1928}" \
  --output "$report"
test "$(stat -c '%a' "$report")" = 600
report_dir="$test_root/report"
mkdir -p "$report_dir"
tar -xzf "$report" -C "$report_dir"
bundle="$(find "$report_dir" -mindepth 1 -maxdepth 1 -type d -name 'jarvis-ai-report-*' -print -quit)"
test -n "$bundle"
grep -q '<redacted-email>' "$bundle/ISSUE.md"
grep -q 'api_key=<redacted>' "$bundle/ISSUE.md"
! grep -R -q 'DO-NOT-SHARE\|person@example.com' "$bundle"
! grep -R -q '25.7701\|-80.1928' "$bundle"
grep -R -q '<redacted-location>' "$bundle"
! grep -R -q '/workspace/' "$bundle"
(cd "$bundle" && sha256sum --check MANIFEST.sha256 >/dev/null)
python3 - "$report" <<'PY'
import stat
import sys
import tarfile

with tarfile.open(sys.argv[1], "r:gz") as archive:
    for member in archive.getmembers():
        expected = 0o700 if member.isdir() else 0o600
        assert stat.S_IMODE(member.mode) == expected, (member.name, oct(member.mode))
PY

# Optional log collection remains explicit and produces a reviewable marker.
log_report="$test_root/ai-report-with-logs.tar.gz"
JARVIS_HOME="$fresh_home" JARVIS_TEST_MODE=1 \
  python3 "$fresh_target/scripts/create_ai_report.py" \
  --issue 'Intermittent service warning' --include-logs --output "$log_report"
tar -tzf "$log_report" > "$test_root/log-report-files.txt"
grep -q 'OPTIONAL_SANITISED_LOGS.txt' "$test_root/log-report-files.txt"

# Rolling back a fresh install removes deployed files and retains the replaced
# release in the recoverable retired directory.
JARVIS_HOME="$fresh_home" JARVIS_TEST_MODE=1 \
  bash "$fresh_target/scripts/rollback.sh" --no-restart
test ! -e "$fresh_target"
test ! -e "$fresh_home/.config/jarvis/profile.json"
test ! -e "$fresh_home/.config/jarvis/capabilities.json"
test ! -e "$fresh_home/.config/mycroft/mycroft.conf"
test ! -e "$fresh_home/.local/bin/jarvis-mic-indicator"
test ! -e "$fresh_home/.local/bin/jarvis-mic-toggle"
test ! -e "$fresh_home/.config/autostart/jarvis-mic-indicator.desktop"
for helper in "${helpers[@]}"; do
  test ! -e "$fresh_home/.local/bin/$helper"
done

# A mid-transaction failure restores the previous deployment automatically.
failure_home="$test_root/failure"
failure_target="$failure_home/.local/src/ovos-skill-jarvis-dispatcher"
mkdir -p "$failure_target" "$failure_home/.local/bin" "$failure_home/.config/jarvis"
printf '%s\n' previous > "$failure_target/previous-release.txt"
cp "$repo_root/profiles/default.json" "$failure_home/.config/jarvis/profile.json"
for helper in "${helpers[@]}"; do
  printf '#!/usr/bin/env bash\necho previous %s\n' "$helper" \
    > "$failure_home/.local/bin/$helper"
  chmod 0755 "$failure_home/.local/bin/$helper"
done
if JARVIS_HOME="$failure_home" JARVIS_TEST_MODE=1 JARVIS_TEST_FAIL_AFTER_DEPLOY=1 \
  bash "$repo_root/scripts/install.sh" --profile reference --no-restart; then
  echo "Injected deployment failure unexpectedly succeeded." >&2
  exit 1
fi
test -f "$failure_target/previous-release.txt"
cmp "$repo_root/profiles/default.json" "$failure_home/.config/jarvis/profile.json"
for helper in "${helpers[@]}"; do
  grep -q "previous $helper" "$failure_home/.local/bin/$helper"
done

# A normal upgrade changes managed program files while preserving machine-owned
# configuration, personal phrases, sounds, shortcuts and private helpers.
preserve_home="$test_root/preserve"
preserve_target="$preserve_home/.local/src/ovos-skill-jarvis-dispatcher"
mkdir -p \
  "$preserve_target" \
  "$preserve_home/.local/bin" \
  "$preserve_home/.config/jarvis" \
  "$preserve_home/.config/mycroft" \
  "$preserve_home/.local/share/ovos/sounds" \
  "$test_root/preserve-expected"
printf '%s\n' legacy > "$preserve_target/legacy-only.txt"
cp "$repo_root/profiles/default.json" "$preserve_home/.config/jarvis/profile.json"
JARVIS_HOME="$preserve_home" JARVIS_TEST_MODE=1 \
  python3 "$repo_root/scripts/setup.py" --mode custom --apps brave \
  --output "$preserve_home/.config/jarvis/capabilities.json" --no-restart
python3 - "$preserve_home/.config/jarvis/capabilities.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
# An update must preserve the exact saved map even if all-detected was the
# original setup mode and a later release can recognise additional apps.
data["mode"] = "all-detected"
path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
path.chmod(0o600)
PY
printf '%s\n' '{"private":"audio configuration"}' \
  > "$preserve_home/.config/mycroft/mycroft.conf"
printf '%s\n' '{"listen_shortcut":"<Super>j","microphone_shortcut":"disabled"}' \
  > "$preserve_home/.config/jarvis/listen-shortcut.json"
printf '%s\n' '{"version":1,"phrases":{"please put a line here":"system.insert_new_line"}}' \
  > "$preserve_home/.config/jarvis/custom-commands.json"
chmod 0600 "$preserve_home/.config/jarvis/custom-commands.json"
printf '%s\n' 'private listening sound' \
  > "$preserve_home/.local/share/ovos/sounds/jarvis-ready.wav"
printf '%s\n' '#!/usr/bin/env bash' 'echo private agent helper' \
  > "$preserve_home/.local/bin/jarvis-agent-window"
chmod 0755 "$preserve_home/.local/bin/jarvis-agent-window"
cp -a "$preserve_home/.config/mycroft/mycroft.conf" \
  "$preserve_home/.config/jarvis/listen-shortcut.json" \
  "$preserve_home/.config/jarvis/custom-commands.json" \
  "$preserve_home/.local/share/ovos/sounds/jarvis-ready.wav" \
  "$preserve_home/.local/bin/jarvis-agent-window" \
  "$test_root/preserve-expected/"

JARVIS_HOME="$preserve_home" JARVIS_TEST_MODE=1 \
  bash "$repo_root/scripts/install.sh" --no-restart

test ! -e "$preserve_target/legacy-only.txt"
for file in \
  listen-shortcut.json custom-commands.json \
  jarvis-ready.wav jarvis-agent-window; do
  case "$file" in
    mycroft.conf) actual="$preserve_home/.config/mycroft/$file" ;;
    listen-shortcut.json|custom-commands.json)
      actual="$preserve_home/.config/jarvis/$file" ;;
    jarvis-ready.wav) actual="$preserve_home/.local/share/ovos/sounds/$file" ;;
    jarvis-agent-window) actual="$preserve_home/.local/bin/$file" ;;
  esac
  cmp "$test_root/preserve-expected/$file" "$actual"
done
python3 - "$preserve_home/.config/mycroft/mycroft.conf" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert data["private"] == "audio configuration"
assert data["listener"]["microphone"] == {
    "module": "ovos-microphone-plugin-sounddevice",
    "ovos-microphone-plugin-sounddevice": {
        "fallback_module": "ovos-microphone-plugin-alsa"
    },
    "ovos-microphone-plugin-alsa": {},
}
PY
test "$(stat -c '%a' "$preserve_home/.config/jarvis/custom-commands.json")" = 600
test -f "$preserve_home/.config/jarvis/capabilities.json"
python3 - "$preserve_home/.config/jarvis/capabilities.json" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert data["listen_shortcut"] == "<Super>j"
assert data["microphone_shortcut"] == "disabled"
assert data["mode"] == "all-detected"
assert data["applications"] == {"brave": "brave"}
PY

# An explicit upgrade choice overrides only the app map and retains personal
# commands and unrelated machine settings. This path also bypasses TTY prompts.
JARVIS_HOME="$preserve_home" JARVIS_TEST_MODE=1 \
  JARVIS_TEST_DETECTED_APPS=brave,standard_notes,proton_mail,proton_calendar,system_calendar \
  bash "$repo_root/scripts/install.sh" --mode recommended --no-restart
python3 - "$preserve_home/.config/jarvis/capabilities.json" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
assert data["mode"] == "recommended"
assert data["applications"] == {
    "brave": "brave",
    "calendar": "proton_calendar",
    "notes": "standard_notes",
    "proton_mail": "proton_mail",
    "system_calendar": "system_calendar",
}
assert data["preferred_apps"] == {
    "browser": "brave", "notes": "notes", "mail": "proton_mail",
    "calendar": "calendar",
}
PY
cmp "$test_root/preserve-expected/custom-commands.json" \
  "$preserve_home/.config/jarvis/custom-commands.json"

# Upgrade rollback restores an existing tree byte-for-byte where it matters.
upgrade_home="$test_root/upgrade"
upgrade_target="$upgrade_home/.local/src/ovos-skill-jarvis-dispatcher"
mkdir -p "$upgrade_target" "$upgrade_home/.local/bin" "$upgrade_home/.config/jarvis"
mkdir -p "$upgrade_home/.config/autostart" "$upgrade_home/.local/share/applications"
printf '%s\n' '[Desktop Entry]' 'Name=Previous Jarvis launcher' \
  > "$upgrade_home/.local/share/applications/jarvis-ovos.desktop"
cp "$upgrade_home/.local/share/applications/jarvis-ovos.desktop" \
  "$test_root/old-jarvis-ovos.desktop"
cat > "$upgrade_home/.config/autostart/jarvis-mic-indicator.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Jarvis Microphone Indicator
Exec=$upgrade_home/.local/bin/jarvis-mic-indicator
Hidden=true
X-GNOME-Autostart-enabled=false
EOF
cp "$upgrade_home/.config/autostart/jarvis-mic-indicator.desktop" "$test_root/old-mic-autostart.desktop"
tar --create --file=- --directory "$repo_root" \
  --exclude='./.git' --exclude='./dist' --exclude='*/__pycache__' . \
  | tar --extract --file=- --directory "$upgrade_target"
cp "$repo_root/ovos_skill_jarvis_dispatcher/wakeword.py" \
  "$upgrade_target/ovos_skill_jarvis_dispatcher/agents.py"
printf '%s\n' legacy > "$upgrade_target/legacy-only.txt"
cp "$repo_root/profiles/default.json" "$upgrade_home/.config/jarvis/profile.json"
printf '%s\n' '{"schema_version":1,"enabled":false,"future_setting":"preserved"}' \
  > "$upgrade_home/.config/jarvis/startup.json"
cp "$upgrade_home/.config/jarvis/startup.json" "$test_root/old-startup.json"
for helper in "${helpers[@]}"; do
  printf '#!/usr/bin/env bash\necho legacy %s\n' "$helper" \
    > "$upgrade_home/.local/bin/$helper"
  chmod 0755 "$upgrade_home/.local/bin/$helper"
done

JARVIS_HOME="$upgrade_home" JARVIS_TEST_MODE=1 \
  bash "$repo_root/scripts/install.sh" --profile reference --no-restart
cmp "$repo_root/ovos_skill_jarvis_dispatcher/agents.py" \
  "$upgrade_target/ovos_skill_jarvis_dispatcher/agents.py"
test ! -e "$upgrade_target/legacy-only.txt"
test ! -e "$upgrade_home/.config/autostart/jarvis-mic-indicator.desktop"
grep -Fxq 'Hidden=true' "$upgrade_home/.config/autostart/ovos-tray.desktop"
grep -Fxq 'X-GNOME-Autostart-enabled=false' "$upgrade_home/.config/autostart/ovos-tray.desktop"
grep -Fxq 'Hidden=true' "$upgrade_home/.config/autostart/jarvis-voice.desktop"
cmp "$test_root/old-startup.json" "$upgrade_home/.config/jarvis/startup.json"

JARVIS_HOME="$upgrade_home" JARVIS_TEST_MODE=1 \
  bash "$upgrade_target/scripts/rollback.sh" --no-restart
cmp "$repo_root/ovos_skill_jarvis_dispatcher/wakeword.py" \
  "$upgrade_target/ovos_skill_jarvis_dispatcher/agents.py"
test -f "$upgrade_target/legacy-only.txt"
cmp "$test_root/old-mic-autostart.desktop" "$upgrade_home/.config/autostart/jarvis-mic-indicator.desktop"
cmp "$test_root/old-jarvis-ovos.desktop" \
  "$upgrade_home/.local/share/applications/jarvis-ovos.desktop"
cmp "$repo_root/profiles/default.json" "$upgrade_home/.config/jarvis/profile.json"
cmp "$test_root/old-startup.json" "$upgrade_home/.config/jarvis/startup.json"
for helper in "${helpers[@]}"; do
  grep -q "legacy $helper" "$upgrade_home/.local/bin/$helper"
done

# The V3.1 migration must retain a complete previous OVOS virtualenv. These
# small stand-ins exercise the real move and rollback logic without modifying
# a running host or downloading the large voice models.
for scenario in success interrupted; do
  stack_home="$test_root/stack-$scenario"
  stack_target="$stack_home/.local/src/ovos-skill-jarvis-dispatcher"
  stack_venv="$stack_home/.venvs/ovos"
  mkdir -p "$stack_target" "$stack_venv/bin" "$stack_home/.config/jarvis"
  printf 'old deployment\n' > "$stack_target/old.txt"
  cp "$repo_root/profiles/default.json" "$stack_home/.config/jarvis/profile.json"
  printf '#!/bin/sh\nexit 0\n' > "$stack_venv/bin/python"
  chmod 0755 "$stack_venv/bin/python"
  printf 'original venv\n' > "$stack_venv/host-marker"
  if [[ "$scenario" == interrupted ]]; then
    if JARVIS_HOME="$stack_home" JARVIS_TEST_MODE=1 JARVIS_TEST_STACK_MODE=1 \
      JARVIS_TEST_FAIL_AFTER_STACK_SWAP=1 \
      bash "$repo_root/scripts/install.sh" --profile reference; then
      echo "Injected stack migration failure unexpectedly succeeded." >&2
      exit 1
    fi
    test -f "$stack_venv/host-marker"
    test ! -e "$stack_venv/jarvis-stack-test-marker"
    test -f "$stack_target/old.txt"
  else
    JARVIS_HOME="$stack_home" JARVIS_TEST_MODE=1 JARVIS_TEST_STACK_MODE=1 \
      bash "$repo_root/scripts/install.sh" --profile reference
    test -f "$stack_venv/jarvis-stack-test-marker"
    test ! -e "$stack_venv/host-marker"
    test -f "$stack_target/pyproject.toml"
    for launcher in ovos-core ovos-audio ovos-dinkum-listener ovos-listen ovos-say-to ovos-speak; do
      test "$(head -n 1 "$stack_venv/bin/$launcher")" = \
        "#!$stack_venv/bin/python"
    done
    JARVIS_HOME="$stack_home" JARVIS_TEST_MODE=1 \
      bash "$stack_target/scripts/rollback.sh" --no-restart
    test -f "$stack_venv/host-marker"
    test ! -e "$stack_venv/jarvis-stack-test-marker"
    test -f "$stack_target/old.txt"
  fi
  cmp "$repo_root/profiles/default.json" "$stack_home/.config/jarvis/profile.json"
done

# Uninstall removes only explicit Jarvis targets. Complete settings, model and
# OVOS removal require their separate flags; shared Speech Note data survives.
uninstall_home="$test_root/uninstall"
uninstall_bin="$test_root/uninstall-bin"
mkdir -p "$uninstall_home/.local/src" "$uninstall_home/.local/bin" \
  "$uninstall_home/.config/jarvis" "$uninstall_home/.local/state/jarvis" \
  "$uninstall_home/.venvs/ovos/bin" "$uninstall_home/.var/app/net.mkiol.SpeechNote" \
  "$uninstall_bin"
cp -a "$repo_root" "$uninstall_home/.local/src/ovos-skill-jarvis-dispatcher"
for helper in "${helpers[@]}"; do
  install -m 0755 "$repo_root/system_helpers/$helper" "$uninstall_home/.local/bin/$helper"
done
printf '%s\n' '{}' > "$uninstall_home/.config/jarvis/capabilities.json"
printf '%s\n' state > "$uninstall_home/.local/state/jarvis/marker"
printf '%s\n' ovos > "$uninstall_home/.venvs/ovos/bin/marker"
printf '%s\n' speech-note > "$uninstall_home/.var/app/net.mkiol.SpeechNote/marker"
cat > "$uninstall_bin/ollama" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "$JARVIS_UNINSTALL_MODEL_LOG"
EOF
chmod 0755 "$uninstall_bin/ollama"
JARVIS_HOME="$uninstall_home" JARVIS_TEST_MODE=1 \
  JARVIS_UNINSTALL_MODEL_LOG="$test_root/uninstall-model.log" \
  PATH="$uninstall_bin:$PATH" bash "$repo_root/scripts/uninstall.sh" \
  --yes --remove-model --remove-settings --remove-ovos
test ! -e "$uninstall_home/.local/src/ovos-skill-jarvis-dispatcher"
test ! -e "$uninstall_home/.config/jarvis"
test ! -e "$uninstall_home/.local/state/jarvis"
test ! -e "$uninstall_home/.venvs/ovos"
test -f "$uninstall_home/.var/app/net.mkiol.SpeechNote/marker"
grep -Fxq 'rm qwen3:4b-instruct-2507-q4_K_M' "$test_root/uninstall-model.log"

echo "PASS: fresh install, reports, failure recovery, upgrade, staged stack and rollback"
