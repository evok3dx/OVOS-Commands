#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
manifest="$repo_root/deployment-manifest.json"
jarvis_home="${JARVIS_HOME:-$HOME}"
target_root="$jarvis_home/.local/src/ovos-skill-jarvis-dispatcher"
target_bin="$jarvis_home/.local/bin"
target_profile_dir="$jarvis_home/.config/jarvis"
target_profile="$target_profile_dir/profile.json"
target_capabilities="$target_profile_dir/capabilities.json"
systemd_dir="$jarvis_home/.config/systemd/user"
launcher="$jarvis_home/.local/share/applications/hermes.desktop"
tray_icon_dir="$jarvis_home/.local/share/icons/ovos-tray"
tray_autostart="$jarvis_home/.config/autostart/ovos-tray.desktop"
mic_icon_dir="$jarvis_home/.local/share/jarvis"
mic_autostart="$jarvis_home/.config/autostart/jarvis-mic-indicator.desktop"
ovos_config="$jarvis_home/.config/mycroft/mycroft.conf"
sound_dir="$jarvis_home/.local/share/ovos/sounds"
listening_sound="$sound_dir/jarvis-ready.wav"
shortcut_state="$jarvis_home/.config/jarvis/listen-shortcut.json"
state_root="$jarvis_home/.local/state/jarvis"
ovos_python="${OVOS_PYTHON:-$jarvis_home/.venvs/ovos/bin/python}"
desktop_python="${JARVIS_DESKTOP_PYTHON:-/usr/bin/python3}"
existing_deployment=false
if [[ -d "$target_root" || -f "$target_profile" || -f "$target_capabilities" ]]; then
  existing_deployment=true
fi
existing_deployment_flag=0
if "$existing_deployment"; then
  existing_deployment_flag=1
fi
restart=true
check_only=false
health_check=true
profile_name="${JARVIS_PROFILE:-}"
setup_mode=""
setup_apps=""
speechnote_choice="ask"
bootstrap=false

usage() {
  cat >&2 <<'EOF'
Usage: scripts/install.sh [OPTIONS]

Options:
  --mode MODE          Initial selection: all, core or custom
  --apps LIST          Comma-separated detected app IDs for custom mode
  --profile NAME       Migrate a legacy bundled profile
  --ovos-python PATH   OVOS virtualenv Python (default: ~/.venvs/ovos/bin/python)
  --bootstrap          Prepare missing OVOS and minimal desktop prerequisites
  --speechnote         Install the optional Speech Note Flatpak for this user
  --no-speechnote      Do not offer the optional Speech Note add-on
  --check              Run preflight checks without changing files
  --no-restart         Do not restart OVOS after installation
  --no-health-check    Do not enable periodic read-only health/update timers
  -h, --help           Show this help
EOF
}

while (($#)); do
  case "$1" in
    --profile)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      profile_name="$2"
      shift 2
      ;;
    --mode)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      setup_mode="$2"
      shift 2
      ;;
    --apps)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      setup_apps="$2"
      shift 2
      ;;
    --ovos-python)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      ovos_python="$2"
      shift 2
      ;;
    --bootstrap)
      bootstrap=true
      shift
      ;;
    --speechnote)
      speechnote_choice="install"
      shift
      ;;
    --no-speechnote)
      speechnote_choice="skip"
      shift
      ;;
    --check)
      check_only=true
      shift
      ;;
    --no-restart)
      restart=false
      shift
      ;;
    --no-health-check)
      health_check=false
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

source_profile=""
if [[ -n "$profile_name" ]]; then
  source_profile="$repo_root/profiles/$profile_name.json"
fi

read_manifest_list() {
  python3 - "$manifest" "$1" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(*data[sys.argv[2]], sep="\n")
PY
}
mapfile -t runtime_helpers < <(read_manifest_list runtime_helpers)

read_compatibility_value() {
  python3 - "$repo_root/compatibility.json" "$1" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
value = data
for key in sys.argv[2].split("."):
    value = value[key]
print(value)
PY
}

confirm_default_yes() {
  local prompt="$1"
  local answer
  if [[ ! -t 0 || ! -t 1 ]]; then
    return 1
  fi
  read -r -p "$prompt [Y/n] " answer
  case "${answer,,}" in
    ""|y|yes) return 0 ;;
    n|no) return 1 ;;
    *)
      echo "Please answer yes or no." >&2
      confirm_default_yes "$prompt"
      ;;
  esac
}

confirm_default_no() {
  local prompt="$1"
  local answer
  if [[ ! -t 0 || ! -t 1 ]]; then
    return 1
  fi
  read -r -p "$prompt [y/N] " answer
  case "${answer,,}" in
    y|yes) return 0 ;;
    ""|n|no) return 1 ;;
    *)
      echo "Please answer yes or no." >&2
      confirm_default_no "$prompt"
      ;;
  esac
}

cleanup_ovos_download() {
  local path="$1"
  local temporary_base="${TMPDIR:-/tmp}"
  case "$path" in
    "$temporary_base"/jarvis-ovos-installer.*) ;;
    *)
      echo "Refusing to clean unexpected OVOS download path: $path" >&2
      return 0
      ;;
  esac
  # Only the unprivileged download and scenario backup live here. The
  # privileged upstream installer uses and removes its own isolated workspace.
  rm -rf -- "$path"
}

run_official_ovos_archive() {
  local archive="$1"
  local expected_sha256="$2"
  sudo bash -s -- "$archive" "$expected_sha256" <<'ROOT_SCRIPT'
set -euo pipefail

archive="$1"
expected_sha256="$2"
workspace="$(mktemp -d /var/tmp/jarvis-ovos-root.XXXXXX)"

cleanup() {
  case "$workspace" in
    /var/tmp/jarvis-ovos-root.*) rm -rf -- "$workspace" ;;
  esac
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

actual_sha256="$(sha256sum "$archive" | awk '{print $1}')"
if [[ "$actual_sha256" != "$expected_sha256" ]]; then
  echo "The OVOS installer archive changed before privileged execution." >&2
  exit 1
fi

installer_root="$workspace/source"
installer_tmp="$workspace/tmp"
mkdir -p "$installer_root" "$installer_tmp"
tar -xzf "$archive" --strip-components=1 -C "$installer_root"
[[ -f "$installer_root/setup.sh" ]] || {
  echo "The verified OVOS installer archive does not contain setup.sh." >&2
  exit 1
}

cd "$installer_root"
TMPDIR="$installer_tmp" bash setup.sh
ROOT_SCRIPT
}

install_official_ovos() {
  local installer_repository installer_commit installer_archive_sha256
  local installer_archive_url installer_parent installer_archive
  local scenario_dir scenario_path scenario_backup installer_status
  for command in python3 tar sudo bash; do
    command -v "$command" >/dev/null 2>&1 || {
      echo "Cannot prepare OVOS because '$command' is unavailable." >&2
      return 1
    }
  done

  installer_repository="$(read_compatibility_value upstream.installer_repository)"
  installer_commit="$(read_compatibility_value upstream.installer_reference_commit)"
  installer_archive_sha256="$(read_compatibility_value upstream.installer_archive_sha256)"
  installer_archive_url="${installer_repository%.git}/archive/${installer_commit}.tar.gz"
  installer_parent="$(mktemp -d "${TMPDIR:-/tmp}/jarvis-ovos-installer.XXXXXX")"
  installer_archive="$installer_parent/ovos-installer.tar.gz"
  scenario_dir="$jarvis_home/.config/ovos-installer"
  scenario_path="$scenario_dir/scenario.yaml"
  scenario_backup="$installer_parent/scenario.yaml.previous"

  printf 'Downloading the reviewed Open Voice OS installer...\n'
  if ! python3 - "$installer_archive_url" "$installer_archive" \
      "$installer_archive_sha256" <<'PY'
import hashlib
import sys
import urllib.request
from pathlib import Path

url, destination, expected = sys.argv[1:]
request = urllib.request.Request(url, headers={"User-Agent": "OVOS-Commands/2.3.1"})
digest = hashlib.sha256()
try:
    with urllib.request.urlopen(request, timeout=60) as response, Path(destination).open("wb") as output:
        while chunk := response.read(1024 * 1024):
            digest.update(chunk)
            output.write(chunk)
except Exception as error:
    Path(destination).unlink(missing_ok=True)
    raise SystemExit(f"Could not download the OVOS installer: {error}")

actual = digest.hexdigest()
if actual != expected:
    Path(destination).unlink(missing_ok=True)
    raise SystemExit(
        "The downloaded OVOS installer failed its pinned SHA-256 check.\n"
        f"Expected: {expected}\nActual:   {actual}"
    )
PY
  then
    cleanup_ovos_download "$installer_parent"
    return 1
  fi

  # The official installer uses Git for its version label and OVOS intent
  # cache. Minimal Linux Mint installations do not always include it.
  if ! command -v git >/dev/null 2>&1; then
    if ! command -v apt-get >/dev/null 2>&1; then
      echo "The official OVOS installer requires Git." >&2
      echo "Automatic Git setup currently supports Linux Mint, Ubuntu and Debian." >&2
      cleanup_ovos_download "$installer_parent"
      return 1
    fi
    printf '%s\n' \
      "Installing Git, a command-line prerequisite required by Open Voice OS." \
      "No desktop applications are being installed."
    if ! sudo apt-get update || \
        ! sudo apt-get install --no-install-recommends git; then
      echo "Git could not be installed, so OVOS setup cannot continue." >&2
      cleanup_ovos_download "$installer_parent"
      return 1
    fi
    command -v git >/dev/null 2>&1 || {
      echo "Git installation completed but the git command is still unavailable." >&2
      cleanup_ovos_download "$installer_parent"
      return 1
    }
  fi

  mkdir -p "$scenario_dir"
  if [[ -f "$scenario_path" ]]; then
    cp -a "$scenario_path" "$scenario_backup"
  fi
  install -m 0600 /dev/stdin "$scenario_path" <<'EOF'
---
uninstall: false
method: virtualenv
channel: testing
profile: ovos
features:
  skills: true
  extra_skills: false
  llm: false
raspberry_pi_tuning: false
share_telemetry: false
share_usage_telemetry: false
EOF

  printf '%s\n' \
    "Starting the reviewed official Open Voice OS installer." \
    "It may request your administrator password for system preparation." \
    "Privileged temporary work is isolated and removed before control returns to Jarvis."
  installer_status=0
  run_official_ovos_archive "$installer_archive" \
    "$installer_archive_sha256" || installer_status=$?

  if [[ -f "$scenario_backup" ]]; then
    install -m 0600 "$scenario_backup" "$scenario_path"
  else
    rm -f -- "$scenario_path"
  fi
  cleanup_ovos_download "$installer_parent"

  if ((installer_status != 0)); then
    echo "The official OVOS installer did not complete successfully." >&2
    return "$installer_status"
  fi
  [[ -x "$ovos_python" ]] || {
    echo "OVOS completed but its virtualenv Python was not found: $ovos_python" >&2
    return 1
  }
}

collect_missing_prerequisites() {
  missing_commands=()
  prerequisite_packages=()
  local command package
  while IFS=':' read -r command package; do
    if ! command -v "$command" >/dev/null 2>&1; then
      missing_commands+=("$command")
      prerequisite_packages+=("$package")
    fi
  done <<'EOF'
xdotool:xdotool
xprop:x11-utils
wmctrl:wmctrl
xclip:xclip
play:sox
playerctl:playerctl
zenity:zenity
xdg-open:xdg-utils
EOF
  if ! command -v wpctl >/dev/null 2>&1 && ! command -v pactl >/dev/null 2>&1; then
    missing_commands+=("wpctl or pactl")
    prerequisite_packages+=("pulseaudio-utils")
  fi
  if ! "$desktop_python" -c 'import gi; gi.require_version("Gtk", "3.0")' 2>/dev/null; then
    missing_commands+=("GTK 3 Python bindings")
    prerequisite_packages+=("python3-gi" "gir1.2-gtk-3.0")
  fi
}

install_desktop_prerequisites() {
  command -v apt-get >/dev/null 2>&1 || {
    echo "Automatic prerequisite setup currently supports Linux Mint, Ubuntu and Debian." >&2
    return 1
  }
  command -v sudo >/dev/null 2>&1 || {
    echo "sudo is required to prepare the missing desktop-control prerequisites." >&2
    return 1
  }
  sudo apt-get update
  sudo apt-get install --no-install-recommends "${prerequisite_packages[@]}"
}

installed_package_version() {
  "$ovos_python" - "$1" <<'PY'
import importlib.metadata as metadata
import sys

try:
    print(metadata.version(sys.argv[1]))
except metadata.PackageNotFoundError:
    pass
PY
}

installed_phoonnx_is_reviewed() {
  local expected_version="$1"
  local expected_commit="$2"
  local cached_archive="$3"
  "$ovos_python" - "$expected_version" "$expected_commit" "$cached_archive" <<'PY'
import importlib.metadata as metadata
import json
import sys
from pathlib import Path

expected_version, expected_commit, cached_archive = sys.argv[1:]
try:
    distribution = metadata.distribution("phoonnx")
except metadata.PackageNotFoundError:
    raise SystemExit(1)
if distribution.version != expected_version:
    raise SystemExit(1)
raw = distribution.read_text("direct_url.json")
if not raw:
    raise SystemExit(1)
direct = json.loads(raw)
if direct.get("vcs_info", {}).get("commit_id") == expected_commit:
    raise SystemExit(0)
url = direct.get("url", "")
if url == Path(cached_archive).resolve().as_uri():
    raise SystemExit(0)
raise SystemExit(1)
PY
}

pip_install() {
  if "$ovos_python" -m pip --version >/dev/null 2>&1; then
    "$ovos_python" -m pip install --disable-pip-version-check "$@"
  elif command -v uv >/dev/null 2>&1; then
    uv pip install --python "$ovos_python" "$@"
  else
    echo "Neither pip in the OVOS virtualenv nor uv is available." >&2
    return 1
  fi
}

download_verified() {
  local url="$1"
  local destination="$2"
  local expected="$3"
  python3 - "$url" "$destination" "$expected" <<'PY'
import hashlib
import sys
import urllib.request
from pathlib import Path

url, destination, expected = sys.argv[1:]
request = urllib.request.Request(url, headers={"User-Agent": "OVOS-Commands/2.3.1"})
digest = hashlib.sha256()
with urllib.request.urlopen(request, timeout=120) as response, Path(destination).open("wb") as output:
    while chunk := response.read(1024 * 1024):
        digest.update(chunk)
        output.write(chunk)
actual = digest.hexdigest()
if actual != expected:
    Path(destination).unlink(missing_ok=True)
    raise SystemExit(f"Download checksum mismatch: expected {expected}, got {actual}")
PY
}

managed_package_names() {
  printf '%s\n' \
    ovos-skill-jarvis-media \
    jarvis-file-search-skill \
    yt-dlp \
    ovos-plugin-manager \
    "$(read_compatibility_value ovos.wakeword.package)" \
    "$(read_compatibility_value ovos.wakeword.engine_package)" \
    "$(read_compatibility_value ovos.custom_wakeword.package)" \
    "$(read_compatibility_value ovos.vad.package)" \
    "$(read_compatibility_value ovos.stt.package)" \
    "$(read_compatibility_value ovos.stt.engine_package)" \
    "$(read_compatibility_value ovos.stt.runtime_package)" \
    "$(read_compatibility_value ovos.tts.package)" \
    misaki scriptconv espeakng-loader phonemizer-fork num2words spacy \
    en-core-web-sm onnxruntime numpy
}

cleanup_voice_stack_work() {
  local work="${1:-}"
  case "$work" in
    "${TMPDIR:-/tmp}"/jarvis-voice-stack.*) rm -rf -- "$work" ;;
    "") ;;
    *) echo "Refusing to remove unexpected voice-stack path: $work" >&2 ;;
  esac
}

ensure_voice_stack() {
  local work="" archive repository commit expected_sha phoonnx_version
  local source_dir cached_archive
  local -a requirements
  repository="$(read_compatibility_value ovos.tts.repository)"
  commit="$(read_compatibility_value ovos.tts.reference_commit)"
  expected_sha="$(read_compatibility_value ovos.tts.archive_sha256)"
  phoonnx_version="$(read_compatibility_value ovos.tts.validated_version)"
  source_dir="$jarvis_home/.local/share/jarvis/sources"
  cached_archive="$source_dir/phoonnx-$commit.tar.gz"
  requirements=(
    "ovos-plugin-manager==$(read_compatibility_value ovos.validated_package_versions.ovos-plugin-manager)"
    "$(read_compatibility_value ovos.wakeword.package)==$(read_compatibility_value ovos.wakeword.validated_version)"
    "$(read_compatibility_value ovos.wakeword.engine_package)==$(read_compatibility_value ovos.wakeword.engine_version)"
    "$(read_compatibility_value ovos.custom_wakeword.package)==$(read_compatibility_value ovos.custom_wakeword.validated_version)"
    "$(read_compatibility_value ovos.vad.package)==$(read_compatibility_value ovos.vad.validated_version)"
    "$(read_compatibility_value ovos.stt.package)==$(read_compatibility_value ovos.stt.validated_version)"
    "$(read_compatibility_value ovos.stt.engine_package)==$(read_compatibility_value ovos.stt.engine_version)"
    "$(read_compatibility_value ovos.stt.runtime_package)==$(read_compatibility_value ovos.stt.runtime_version)"
    "misaki==$(read_compatibility_value ovos.tts.misaki_version)"
    "scriptconv==$(read_compatibility_value ovos.tts.scriptconv_version)"
    "espeakng-loader==$(read_compatibility_value ovos.tts.espeakng_loader_version)"
    "phonemizer-fork==$(read_compatibility_value ovos.tts.phonemizer_fork_version)"
    "num2words==$(read_compatibility_value ovos.tts.num2words_version)"
    "spacy==$(read_compatibility_value ovos.tts.spacy_version)"
    "en-core-web-sm @ $(read_compatibility_value ovos.tts.spacy_model_url)#sha256=$(read_compatibility_value ovos.tts.spacy_model_sha256)"
    "onnxruntime==$(read_compatibility_value ovos.tts.onnxruntime_version)"
    "numpy==$(read_compatibility_value ovos.tts.numpy_version)"
  )

  mkdir -p "$source_dir"
  if [[ ! -f "$cached_archive" ]] || \
     [[ "$(sha256sum "$cached_archive" | awk '{print $1}')" != "$expected_sha" ]]; then
    work="$(mktemp -d "${TMPDIR:-/tmp}/jarvis-voice-stack.XXXXXX")"
    archive="$work/phoonnx.tar.gz"
    printf '%s\n' "Downloading the reviewed Bella voice engine source..."
    if ! download_verified \
      "${repository%.git}/archive/${commit}.tar.gz" "$archive" "$expected_sha"; then
      cleanup_voice_stack_work "$work"
      return 1
    fi
    install -m 0644 "$archive" "$cached_archive"
    cleanup_voice_stack_work "$work"
    work=""
  fi

  if ! installed_phoonnx_is_reviewed \
    "$phoonnx_version" "$commit" "$cached_archive"; then
    printf '%s\n' "Installing the reviewed PhōnNX source revision."
    pip_install --force-reinstall --no-deps \
      "phoonnx @ file://$cached_archive"
  fi
  # Include the exact local source in the main transaction as well, so pip
  # verifies and installs its ordinary runtime dependencies without enabling
  # heavyweight optional language/GPU extras.
  requirements+=("phoonnx @ file://$cached_archive")

  printf '%s\n' \
    "Installing the reviewed local OVOS voice stack." \
    "Wake word, speech recognition and Bella run without administrator access."
  if ! pip_install "${requirements[@]}"; then
    cleanup_voice_stack_work "$work"
    return 1
  fi
  cleanup_voice_stack_work "$work"

  printf '%s\n' "Preparing the local Hey Jarvis, small.en and Bella models..."
  "$ovos_python" - <<'PY'
from openwakeword.utils import download_models
from openwakeword import get_pretrained_model_paths
from faster_whisper import WhisperModel

download_models()
paths = [str(path) for path in (get_pretrained_model_paths() or [])]
if not any("hey_jarvis" in path for path in paths):
    raise SystemExit("OpenWakeWord did not provide the reviewed hey_jarvis model")
WhisperModel("small.en", device="cpu", compute_type="int8", cpu_threads=8)
PY
  "$ovos_python" - "$(read_compatibility_value ovos.tts.voice)" <<'PY'
import sys
from phoonnx.model_manager import TTSModelManager

voice = sys.argv[1]
manager = TTSModelManager()
manager.load()
manager.merge_default_voices()
if not manager.download_voice_by_id(voice):
    raise SystemExit(f"PhōnNX voice is not in the reviewed catalogue: {voice}")
PY
}

[[ -x "$desktop_python" ]] || {
  echo "System desktop Python not found: $desktop_python" >&2
  exit 1
}

python3 "$repo_root/scripts/validate_refactor.py"

if [[ -n "$profile_name" ]]; then
  if [[ ! "$profile_name" =~ ^[a-zA-Z0-9._-]+$ ]] || [[ ! -f "$source_profile" ]]; then
    echo "Profile not found: $source_profile" >&2
    exit 1
  fi
  SOURCE_PROFILE="$source_profile" SOURCE_PACKAGE="$repo_root/ovos_skill_jarvis_dispatcher" python3 <<'PY'
import importlib.util
import json
import os
from pathlib import Path

module_path = Path(os.environ["SOURCE_PACKAGE"]) / "profile.py"
spec = importlib.util.spec_from_file_location("jarvis_profile", module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.resolve_profile(json.loads(Path(os.environ["SOURCE_PROFILE"]).read_text(encoding="utf-8")))
PY
fi

if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]]; then
  if [[ ! -x "$ovos_python" ]]; then
    if "$check_only"; then
      echo "OVOS virtualenv Python not found: $ovos_python" >&2
      echo "Run without --check to be offered the reviewed OVOS setup." >&2
      exit 1
    fi
    printf '%s\n' \
      "Open Voice OS is not installed at $ovos_python." \
      "Jarvis can prepare the reviewed official OVOS virtualenv baseline." \
      "This uses administrator access once for OVOS system preparation." \
      "Jarvis remains user-space and no desktop applications are installed."
    if "$bootstrap" || confirm_default_yes "Set up Open Voice OS now?"; then
      install_official_ovos
    else
      echo "OVOS setup was declined; no Jarvis files were installed." >&2
      exit 1
    fi
  fi

  collect_missing_prerequisites
  if ((${#missing_commands[@]})); then
    if "$check_only"; then
      echo "Missing desktop-control prerequisites: ${missing_commands[*]}" >&2
      echo "Run without --check to be offered minimal prerequisite setup." >&2
      exit 1
    fi
    printf '%s\n' \
      "Jarvis needs these small desktop-control prerequisites: ${missing_commands[*]}." \
      "They are command-line controls and GTK bindings, not desktop applications."
    if "$bootstrap" || confirm_default_yes "Install the missing prerequisites now?"; then
      install_desktop_prerequisites
      collect_missing_prerequisites
      ((${#missing_commands[@]} == 0)) || {
        echo "Prerequisites are still missing: ${missing_commands[*]}" >&2
        exit 1
      }
    else
      echo "Prerequisite setup was declined; no Jarvis files were installed." >&2
      exit 1
    fi
  fi
  command -v systemctl >/dev/null 2>&1 || {
    echo "systemctl is required for the supported Linux desktop deployment." >&2
    exit 1
  }
fi

if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]]; then
  "$ovos_python" "$repo_root/scripts/check-plugin-rollback.py"
fi

if "$check_only"; then
  if [[ "${JARVIS_TEST_MODE:-0}" == 1 ]]; then
    echo "PASS: repository and profile validate in test mode"
  else
    python3 "$repo_root/scripts/doctor.py" --ovos-python "$ovos_python"
    "$desktop_python" "$repo_root/scripts/qwen-setup.py"
  fi
  printf '%s\n' "Preflight passed." "No files changed."
  exit 0
fi

# The reviewed local model is required for V3. The prompt and download happen
# before any Jarvis files or configuration change. Existing models are reused.
if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]]; then
  "$desktop_python" "$repo_root/scripts/qwen-setup.py" --prepare
fi

if "$existing_deployment"; then
  printf '%s\n' \
    "Existing OVOS voice packages and models will be left untouched." \
    "Existing Jarvis configuration and keyboard shortcuts will be preserved."
fi

stamp="$(date +%Y%m%d-%H%M%S-%N)"
backup_root="$state_root/backups/$stamp"
mkdir -p "$state_root"
stage_root="$(mktemp -d "$state_root/stage.$stamp.XXXXXX")"
stage_release="$stage_root/release"
configuration_source="$stage_root/capabilities.json"
transaction_active=false

cleanup() {
  case "$stage_root" in
    "$state_root"/stage.*)
      rm -rf -- "$stage_root"
      ;;
  esac
}

restore_failed_transaction() {
  local status="$1"
  if "$transaction_active"; then
    echo "Installation failed; restoring the previous Jarvis deployment." >&2
    rollback_script="$target_root/scripts/rollback.sh"
    if [[ ! -f "$rollback_script" ]]; then
      rollback_script="$stage_release/scripts/rollback.sh"
    fi
    if [[ -f "$rollback_script" ]]; then
      JARVIS_HOME="$jarvis_home" OVOS_PYTHON="$ovos_python" \
        JARVIS_TEST_MODE="${JARVIS_TEST_MODE:-0}" \
        bash "$rollback_script" "$backup_root" || true
    elif [[ -d "$backup_root/target-root" && ! -d "$target_root" ]]; then
      cp -a "$backup_root/target-root" "$target_root" || true
    fi
  fi
  cleanup
  exit "$status"
}
trap 'restore_failed_transaction $?' EXIT

mkdir -p \
  "$backup_root" \
  "$(dirname "$target_root")" \
  "$target_bin" \
  "$target_profile_dir" \
  "$systemd_dir" \
  "$tray_icon_dir" \
  "$mic_icon_dir" \
  "$sound_dir" \
  "$(dirname "$tray_autostart")" \
  "$stage_release"

if [[ -f "$target_capabilities" ]]; then
  cp -a "$target_capabilities" "$configuration_source"
elif [[ -n "$source_profile" ]]; then
  JARVIS_HOME="$jarvis_home" "$desktop_python" "$repo_root/scripts/setup.py" \
    --migrate-profile "$source_profile" --output "$configuration_source" --no-restart
elif [[ -f "$target_profile" ]]; then
  JARVIS_HOME="$jarvis_home" "$desktop_python" "$repo_root/scripts/setup.py" \
    --migrate-profile "$target_profile" --output "$configuration_source" --no-restart
else
  setup_arguments=(--output "$configuration_source" --no-restart)
  if [[ -n "$setup_mode" ]]; then
    setup_arguments+=(--mode "$setup_mode")
  fi
  if [[ -n "$setup_apps" ]]; then
    setup_arguments+=(--apps "$setup_apps")
  fi
  JARVIS_HOME="$jarvis_home" "$desktop_python" "$repo_root/scripts/setup.py" "${setup_arguments[@]}"
fi

JARVIS_HOME="$jarvis_home" \
JARVIS_EXISTING_DEPLOYMENT="$existing_deployment_flag" \
  "$desktop_python" - \
  "$configuration_source" "$repo_root" "$shortcut_state" <<'PY'
import json
import importlib.util
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
capabilities_path = (
    Path(sys.argv[2]) / "ovos_skill_jarvis_dispatcher/capabilities.py"
)
spec = importlib.util.spec_from_file_location(
    "jarvis_capability_detection", capabilities_path
)
capabilities = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capabilities)

data = json.loads(path.read_text(encoding="utf-8"))
if os.environ.get("JARVIS_EXISTING_DEPLOYMENT") == "1":
    shortcut_path = Path(sys.argv[3])
    if shortcut_path.is_file():
        try:
            shortcuts = json.loads(shortcut_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            shortcuts = {}
        listen = shortcuts.get("listen_shortcut", shortcuts.get("shortcut"))
        microphone = shortcuts.get("microphone_shortcut")
        if isinstance(listen, str):
            data["listen_shortcut"] = listen
        if isinstance(microphone, str):
            data["microphone_shortcut"] = microphone
else:
    data.setdefault("listen_shortcut", "<Super>l")
    data.setdefault("microphone_shortcut", "<Shift><Super>l")
if data.get("mode") == "all-detected":
    # "All detected" is a continuing policy, not a one-time snapshot. This
    # picks up a supported application installed after Jarvis without changing
    # core-only or deliberately customised selections.
    home = Path(os.environ.get("JARVIS_HOME", Path.home())).expanduser()
    data["applications"] = capabilities.detect_applications(home)
temporary = path.with_suffix(path.suffix + ".new")
temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
temporary.chmod(0o600)
temporary.replace(path)
PY

# Copy only reviewed release roots. This avoids deploying unrelated files from
# a checkout (for example local notes, credentials or previous build output).
release_roots=(
  .github command_editor docs extras mic ovos_skill_jarvis_dispatcher plugins profiles
  scripts system_helpers systemd tray voice
)
release_files=(
  .gitignore COMMAND-EDITOR.md README.md compatibility.json
  deployment-manifest.json pyproject.toml
)
tar --create --file=- \
  --directory "$repo_root" \
  --exclude='./.git' \
  --exclude='./dist' \
  --exclude='./__pycache__' \
  --exclude='*/__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.log' \
  --exclude='*.mp3' \
  --exclude='*.flac' \
  -- "${release_roots[@]}" "${release_files[@]}" \
  | tar --extract --file=- --directory "$stage_release"

python3 -m py_compile \
  "$stage_release"/ovos_skill_jarvis_dispatcher/*.py \
  "$stage_release"/ovos_skill_jarvis_dispatcher/integrations/*.py \
  "$stage_release"/scripts/*.py

backup_file() {
  local source="$1"
  local relative="$2"
  local destination="$backup_root/$relative"
  mkdir -p "$(dirname "$destination")"
  if [[ -e "$source" ]]; then
    cp -a "$source" "$destination"
  else
    : > "$destination.missing"
  fi
}

backup_file "$target_profile" profile.json
backup_file "$target_capabilities" capabilities.json
backup_file "$target_profile_dir/router.json" router.json
for helper in "${runtime_helpers[@]}"; do
  backup_file "$target_bin/$helper" "helpers/$helper"
done
for unit in \
  hermes-launcher-repair.service \
  hermes-launcher-repair.path \
  jarvis-health-check.service \
  jarvis-health-check.timer \
  jarvis-update-check.service \
  jarvis-update-check.timer; do
  backup_file "$systemd_dir/$unit" "systemd/$unit"
done
backup_file "$launcher" hermes.desktop
backup_file "$target_bin/ovos-tray" tray/ovos-tray
backup_file "$tray_autostart" tray/ovos-tray.desktop
for icon in \
  ovos-ready.svg ovos-ready-update.svg \
  ovos-starting.svg ovos-starting-update.svg \
  ovos-stopped.svg ovos-stopped-update.svg \
  ovos-failed.svg ovos-failed-update.svg; do
  backup_file "$tray_icon_dir/$icon" "tray/$icon"
done
backup_file "$target_bin/jarvis-mic-indicator" mic/jarvis-mic-indicator
backup_file "$target_bin/jarvis-mic-toggle" mic/jarvis-mic-toggle
backup_file "$mic_autostart" mic/jarvis-mic-indicator.desktop
backup_file "$mic_icon_dir/mic-active.svg" mic/mic-active.svg
backup_file "$mic_icon_dir/mic-muted.svg" mic/mic-muted.svg
backup_file "$ovos_config" mycroft.conf
backup_file "$listening_sound" sounds/jarvis-ready.wav
backup_file "$shortcut_state" listen-shortcut.json

if [[ "${JARVIS_TEST_MODE:-0}" == 1 ]]; then
  printf '%s\n' '{}' > "$backup_root/managed-packages.json"
  printf '%s\n' unavailable > "$backup_root/cinnamon-shortcuts.state"
  : > "$backup_root/pronunciation-source.missing"
else
  mapfile -t managed_packages < <(managed_package_names | awk '!seen[$0]++')
  "$ovos_python" - "$backup_root/managed-packages.json" "${managed_packages[@]}" <<'PY'
import importlib.metadata as metadata
import json
import sys
from pathlib import Path

state = {}
for package in sys.argv[2:]:
    try:
        distribution = metadata.distribution(package)
        direct = distribution.read_text("direct_url.json")
        state[package] = {
            "version": distribution.version,
            "direct_url": json.loads(direct) if direct else None,
        }
    except metadata.PackageNotFoundError:
        state[package] = {"version": None, "direct_url": None}
path = Path(sys.argv[1])
path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
path.chmod(0o600)
PY
  pronunciation_source="$(
    "$ovos_python" "$repo_root/scripts/patch-pronunciation.py" --print-source 2>/dev/null || true
  )"
  if [[ -n "$pronunciation_source" && -f "$pronunciation_source" ]]; then
    printf '%s\n' "$pronunciation_source" > "$backup_root/pronunciation-source"
    backup_file "$pronunciation_source" pronunciation/mul.py
  else
    : > "$backup_root/pronunciation-source.missing"
  fi
  if command -v gsettings >/dev/null 2>&1 && \
     JARVIS_HOME="$jarvis_home" "$desktop_python" \
       "$repo_root/scripts/listen-shortcut.py" \
       --snapshot "$backup_root/cinnamon-shortcuts.json"; then
    printf '%s\n' available > "$backup_root/cinnamon-shortcuts.state"
  else
    printf '%s\n' unavailable > "$backup_root/cinnamon-shortcuts.state"
    echo "Cinnamon shortcut schemas unavailable; configure the listen key later from the tray." >&2
  fi
fi

transaction_active=true
if [[ -d "$target_root" ]]; then
  mv -- "$target_root" "$backup_root/target-root"
else
  : > "$backup_root/target-root.missing"
fi

for unit in hermes-launcher-repair.path jarvis-health-check.timer jarvis-update-check.timer; do
  if [[ "${JARVIS_TEST_MODE:-0}" == 1 ]]; then
    echo test > "$backup_root/$unit.state"
  elif systemctl --user is-enabled --quiet "$unit"; then
    echo enabled > "$backup_root/$unit.state"
  else
    echo disabled > "$backup_root/$unit.state"
  fi
done

mv -- "$stage_release" "$target_root"

if [[ "${JARVIS_TEST_MODE:-0}" == 1 && "${JARVIS_TEST_FAIL_AFTER_DEPLOY:-0}" == 1 ]]; then
  echo "Injecting a test-only deployment failure." >&2
  false
fi

if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]]; then
  if "$ovos_python" -m pip --version >/dev/null 2>&1; then
    "$ovos_python" -m pip install --disable-pip-version-check \
      --no-deps --editable "$target_root"
  elif command -v uv >/dev/null 2>&1; then
    uv pip install --python "$ovos_python" --no-deps --editable "$target_root"
  else
    echo "Neither pip in the OVOS virtualenv nor uv is available." >&2
    exit 1
  fi
  if ! "$existing_deployment"; then
    ensure_voice_stack
    "$ovos_python" "$target_root/scripts/patch-pronunciation.py"
    "$ovos_python" - <<'PY'
from scriptconv.phonemizers.mul import MisakiEnPhonemizer

phonemes = MisakiEnPhonemizer().phonemize_string(
    "Harvard Jarvis Ollama Facebook", "en-US"
)
if not phonemes or "None" in phonemes:
    raise SystemExit("Bella pronunciation fallback validation failed")
print("Bella pronunciation fallback validated.")
PY
  fi
  # These are bundled, reviewed first-party skills. Do not resolve their
  # dependencies or replace working OVOS voice packages on an upgrade.
  if ! "$ovos_python" -c 'import yt_dlp' >/dev/null 2>&1; then
    pip_install --no-deps yt-dlp
  fi
  pip_install --no-deps --editable "$target_root/plugins/ovos-skill-jarvis-media"
  pip_install --no-deps --editable "$target_root/plugins/jarvis-file-search"
fi

if "$existing_deployment"; then
  echo "Preserved the existing OVOS voice packages and models."
fi

if ! "$existing_deployment"; then
  install -m 0644 "$target_root/voice/jarvis-ready.wav" "$listening_sound"
  "$desktop_python" "$target_root/scripts/configure-audio-stack.py" \
    --config "$ovos_config" --listening-sound "$listening_sound"
  if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]]; then
    "$ovos_python" "$target_root/scripts/configure-intent-pipeline.py" \
      --config "$ovos_config" --merge-v3
  fi

mapfile -t wake_settings < <(python3 - "$configuration_source" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
identifier = data.get("wake_phrase", "hey_jarvis")
spoken = data.get("wake_phrase_spoken", str(identifier).replace("_", " "))
print(identifier)
print(spoken)
PY
)
wake_phrase="${wake_settings[0]}"
wake_phrase_spoken="${wake_settings[1]}"
  "$desktop_python" "$target_root/scripts/configure-wakeword.py" \
    --config "$ovos_config" --wake-phrase "$wake_phrase" \
    --spoken-phrase "$wake_phrase_spoken"
else
  echo "Preserved existing audio, wake-word, intent-pipeline and sound configuration."
  if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]]; then
    "$ovos_python" "$target_root/scripts/configure-intent-pipeline.py" \
      --config "$ovos_config" --merge-v3
  fi
fi

if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]]; then
  "$desktop_python" "$target_root/scripts/qwen-setup.py" --enable
fi

for helper in "${runtime_helpers[@]}"; do
  install -m 0755 "$target_root/system_helpers/$helper" "$target_bin/$helper"
done
install -m 0600 "$configuration_source" "$target_capabilities"
if [[ -n "$source_profile" ]]; then
  install -m 0600 "$source_profile" "$target_profile"
fi

mapfile -t shortcut_settings < <(python3 - "$configuration_source" <<'PY'
import json
import sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(data.get("listen_shortcut", "<Super>l"))
print(data.get("microphone_shortcut", "<Shift><Super>l"))
PY
)
listen_shortcut="${shortcut_settings[0]}"
microphone_shortcut="${shortcut_settings[1]}"
if ! "$existing_deployment" && [[ "${JARVIS_TEST_MODE:-0}" != 1 && \
      "$(<"$backup_root/cinnamon-shortcuts.state")" == available ]]; then
  JARVIS_HOME="$jarvis_home" "$desktop_python" \
    "$target_root/scripts/listen-shortcut.py" \
    --shortcut "$listen_shortcut" \
    --microphone-shortcut "$microphone_shortcut"
fi

tray_installed=false
if [[ "${JARVIS_TEST_MODE:-0}" == 1 ]] || \
   "$desktop_python" -c 'import gi; gi.require_version("Gtk", "3.0")' 2>/dev/null; then
  install -m 0755 "$target_root/tray/ovos-tray.py" "$target_bin/ovos-tray"
  install -m 0644 "$target_root/tray/"*.svg "$tray_icon_dir/"
  TRAY_EXEC="$target_bin/ovos-tray" "$desktop_python" - "$tray_autostart" <<'PY'
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
temporary = path.with_suffix(".desktop.new")
temporary.write_text(
    "[Desktop Entry]\nType=Application\nName=Jarvis Voice Controls\n"
    f"Exec={os.environ['TRAY_EXEC']}\nTerminal=false\n"
    "X-GNOME-Autostart-enabled=true\n",
    encoding="utf-8",
)
temporary.chmod(0o644)
temporary.replace(path)
PY
  tray_installed=true
else
  echo "GTK 3 tray support is unavailable; jarvis-setup remains available in the terminal." >&2
fi

# Older releases started a second tray icon. The unified tray displays the
# listener state itself. Retire only the autostart entry we created, after its
# exact contents have been included in the transaction backup above.
if [[ -f "$mic_autostart" ]] && \
   grep -Fxq 'Name=Jarvis Microphone Indicator' "$mic_autostart" && \
   grep -Fxq "Exec=$target_bin/jarvis-mic-indicator" "$mic_autostart"; then
  rm -- "$mic_autostart"
  if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]]; then
    pkill -f "$target_bin/jarvis-mic-indicator" 2>/dev/null || true
  fi
fi

render_unit() {
  local source="$1"
  local destination="$2"
  TARGET_BIN="$target_bin" LAUNCHER="$launcher" \
    python3 - "$source" "$destination" <<'PY'
import os
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8")
text = text.replace("@TARGET_BIN@", os.environ["TARGET_BIN"])
text = text.replace("@LAUNCHER@", os.environ["LAUNCHER"])
temporary = Path(sys.argv[2] + ".new")
temporary.write_text(text, encoding="utf-8")
temporary.chmod(0o644)
temporary.replace(sys.argv[2])
PY
}

render_unit "$target_root/systemd/hermes-launcher-repair.service.in" \
  "$systemd_dir/hermes-launcher-repair.service"
render_unit "$target_root/systemd/hermes-launcher-repair.path.in" \
  "$systemd_dir/hermes-launcher-repair.path"
render_unit "$target_root/systemd/jarvis-health-check.service.in" \
  "$systemd_dir/jarvis-health-check.service"
install -m 0644 "$target_root/systemd/jarvis-health-check.timer" \
  "$systemd_dir/jarvis-health-check.timer"
render_unit "$target_root/systemd/jarvis-update-check.service.in" \
  "$systemd_dir/jarvis-update-check.service"
install -m 0644 "$target_root/systemd/jarvis-update-check.timer" \
  "$systemd_dir/jarvis-update-check.timer"

profile_has_hermes="$(python3 - "$configuration_source" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print("yes" if "hermes_desktop" in data.get("applications", {}).values() else "no")
PY
)"

if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]]; then
  systemctl --user daemon-reload
  if [[ "$profile_has_hermes" == yes ]]; then
    systemctl --user enable --now hermes-launcher-repair.path >/dev/null
    "$target_bin/hermes-launcher-repair"
  else
    systemctl --user disable --now hermes-launcher-repair.path >/dev/null 2>&1 || true
  fi
  if "$health_check"; then
    systemctl --user enable --now jarvis-health-check.timer >/dev/null
    systemctl --user enable --now jarvis-update-check.timer >/dev/null
  else
    systemctl --user disable --now jarvis-health-check.timer >/dev/null 2>&1 || true
    systemctl --user disable --now jarvis-update-check.timer >/dev/null 2>&1 || true
  fi

  if "$restart"; then
    "$target_bin/jarvis-restart" --full
  fi

  python3 "$target_root/scripts/doctor.py" --ovos-python "$ovos_python"

  # Start the new tray only after final validation. A failed transaction must
  # not leave a process whose helpers have just been rolled back or removed.
  if "$tray_installed"; then
    pkill -f "$target_bin/ovos-tray" 2>/dev/null || true
    nohup "$target_bin/ovos-tray" > "$state_root/ovos-tray.log" 2>&1 &
  fi
fi

current_version="$(python3 - "$target_root/pyproject.toml" <<'PY'
import re
import sys
from pathlib import Path

match = re.search(r'^version = "([^"]+)"$', Path(sys.argv[1]).read_text(), re.MULTILINE)
print(match.group(1) if match else "unknown")
PY
)"
current_mode="$(python3 - "$target_capabilities" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("mode", "custom"))
PY
)"
CURRENT_BACKUP="$backup_root" CURRENT_MODE="$current_mode" CURRENT_VERSION="$current_version" \
  python3 - "$state_root/current.json" <<'PY'
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
temporary = path.with_suffix(".json.new")
temporary.write_text(json.dumps({
    "schema_version": 1,
    "installed_utc": datetime.now(timezone.utc).isoformat(),
    "version": os.environ["CURRENT_VERSION"],
    "mode": os.environ["CURRENT_MODE"],
    "rollback": os.environ["CURRENT_BACKUP"],
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
temporary.chmod(0o600)
temporary.replace(path)
PY

printf '%s\n' "$backup_root" > "$state_root/latest-backup"
chmod 0600 "$state_root/latest-backup"
transaction_active=false
trap cleanup EXIT

# The dynamic Whisper hints modify a third-party plugin only after its exact
# reviewed layout is checked. This add-on has its own backup and rollback;
# unknown plugin revisions are reported and left untouched.
if [[ "${JARVIS_TEST_MODE:-0}" != 1 && "$restart" == true ]]; then
  hint_installer="$target_root/extras/whisper-hints/install.py"
  if "$desktop_python" "$hint_installer" --check; then
    if ! "$desktop_python" "$hint_installer"; then
      echo "Whisper name hints were not enabled; inspect the add-on backup and status." >&2
    fi
  else
    echo "Whisper name hints require manual review for this plugin revision; existing STT was preserved." >&2
  fi
fi

if command -v flatpak >/dev/null 2>&1 && \
   flatpak info net.mkiol.SpeechNote >/dev/null 2>&1; then
  printf '%s\n' \
    "Speech Note detected; Jarvis will use its existing models and settings." \
    "Review or change it later from the Jarvis tray: Speech Note setup."
elif [[ "$speechnote_choice" == install ]] || \
     { [[ "$speechnote_choice" == ask ]] && \
       command -v flatpak >/dev/null 2>&1 && \
       confirm_default_no "Install optional Speech Note locally for this user?"; }; then
  printf '%s\n' \
    "Speech Note is a sizeable Flatpak and its language/voice models are separate downloads." \
    "It will be installed for this user only; no administrator access is used."
  if "$target_bin/jarvis-speechnote-setup" --install --yes; then
    printf '%s\n' \
      "Speech Note installed. Open it from the Jarvis tray to choose local models and a voice."
  else
    echo "Warning: optional Speech Note setup did not complete; Jarvis remains installed." >&2
  fi
fi

printf '%s\n' \
  "Installed Jarvis commands successfully." \
  "Configuration: $current_mode" \
  "Setup: jarvis-setup --gui" \
  "Doctor: jarvis-health-check" \
  "AI report: jarvis-report --issue \"Describe what failed\"" \
  "Rollback: bash $target_root/scripts/rollback.sh"
