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
state_root="$jarvis_home/.local/state/jarvis"
ovos_python="${OVOS_PYTHON:-$jarvis_home/.venvs/ovos/bin/python}"
restart=true
check_only=false
health_check=true
profile_name="${JARVIS_PROFILE:-}"
setup_mode=""
setup_apps=""
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

install_official_ovos() {
  local installer_repository installer_commit installer_archive_sha256
  local installer_archive_url installer_parent installer_archive installer_root
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
  installer_root="$installer_parent/source"
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
request = urllib.request.Request(url, headers={"User-Agent": "OVOS-Commands/2.2.2"})
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
    rm -rf -- "$installer_parent"
    return 1
  fi
  mkdir -p "$installer_root"
  if ! tar -xzf "$installer_archive" --strip-components=1 -C "$installer_root"; then
    echo "The verified OVOS installer archive could not be extracted." >&2
    rm -rf -- "$installer_parent"
    return 1
  fi
  [[ -f "$installer_root/setup.sh" ]] || {
    echo "The verified OVOS installer archive does not contain setup.sh." >&2
    rm -rf -- "$installer_parent"
    return 1
  }

  # The official installer uses Git for its version label and OVOS intent
  # cache. Minimal Linux Mint installations do not always include it.
  if ! command -v git >/dev/null 2>&1; then
    if ! command -v apt-get >/dev/null 2>&1; then
      echo "The official OVOS installer requires Git." >&2
      echo "Automatic Git setup currently supports Linux Mint, Ubuntu and Debian." >&2
      rm -rf -- "$installer_parent"
      return 1
    fi
    printf '%s\n' \
      "Installing Git, a command-line prerequisite required by Open Voice OS." \
      "No desktop applications are being installed."
    if ! sudo apt-get update || \
        ! sudo apt-get install --no-install-recommends git; then
      echo "Git could not be installed, so OVOS setup cannot continue." >&2
      rm -rf -- "$installer_parent"
      return 1
    fi
    command -v git >/dev/null 2>&1 || {
      echo "Git installation completed but the git command is still unavailable." >&2
      rm -rf -- "$installer_parent"
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
    "It may request your administrator password for system preparation."
  installer_status=0
  (cd "$installer_root" && sudo bash setup.sh) || installer_status=$?

  if [[ -f "$scenario_backup" ]]; then
    install -m 0600 "$scenario_backup" "$scenario_path"
  else
    rm -f -- "$scenario_path"
  fi
  rm -rf -- "$installer_parent"

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
EOF
  if ! command -v wpctl >/dev/null 2>&1 && ! command -v pactl >/dev/null 2>&1; then
    missing_commands+=("wpctl or pactl")
    prerequisite_packages+=("pulseaudio-utils")
  fi
  if ! python3 -c 'import gi; gi.require_version("Gtk", "3.0")' 2>/dev/null; then
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

if "$check_only"; then
  if [[ "${JARVIS_TEST_MODE:-0}" == 1 ]]; then
    echo "PASS: repository and profile validate in test mode"
  else
    python3 "$repo_root/scripts/doctor.py" --ovos-python "$ovos_python"
  fi
  printf '%s\n' "Preflight passed." "No files changed."
  exit 0
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
        bash "$rollback_script" "$backup_root" --no-restart || true
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
  "$(dirname "$tray_autostart")" \
  "$stage_release"

if [[ -f "$target_capabilities" ]]; then
  cp -a "$target_capabilities" "$configuration_source"
elif [[ -n "$source_profile" ]]; then
  JARVIS_HOME="$jarvis_home" python3 "$repo_root/scripts/setup.py" \
    --migrate-profile "$source_profile" --output "$configuration_source" --no-restart
elif [[ -f "$target_profile" ]]; then
  JARVIS_HOME="$jarvis_home" python3 "$repo_root/scripts/setup.py" \
    --migrate-profile "$target_profile" --output "$configuration_source" --no-restart
else
  setup_arguments=(--output "$configuration_source" --no-restart)
  if [[ -n "$setup_mode" ]]; then
    setup_arguments+=(--mode "$setup_mode")
  fi
  if [[ -n "$setup_apps" ]]; then
    setup_arguments+=(--apps "$setup_apps")
  fi
  JARVIS_HOME="$jarvis_home" python3 "$repo_root/scripts/setup.py" "${setup_arguments[@]}"
fi

# Copy only reviewed release roots. This avoids deploying unrelated files from
# a checkout (for example local notes, credentials or previous build output).
release_roots=(
  .github command_editor docs mic ovos_skill_jarvis_dispatcher profiles
  scripts system_helpers systemd tray
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
  --exclude='*.wav' \
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
for icon in ovos-ready.svg ovos-starting.svg ovos-stopped.svg ovos-failed.svg; do
  backup_file "$tray_icon_dir/$icon" "tray/$icon"
done

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
fi

for helper in "${runtime_helpers[@]}"; do
  install -m 0755 "$target_root/system_helpers/$helper" "$target_bin/$helper"
done
install -m 0600 "$configuration_source" "$target_capabilities"
if [[ -n "$source_profile" ]]; then
  install -m 0600 "$source_profile" "$target_profile"
fi

tray_installed=false
if [[ "${JARVIS_TEST_MODE:-0}" == 1 ]] || \
   python3 -c 'import gi; gi.require_version("Gtk", "3.0")' 2>/dev/null; then
  install -m 0755 "$target_root/tray/ovos-tray.py" "$target_bin/ovos-tray"
  install -m 0644 "$target_root/tray/"*.svg "$tray_icon_dir/"
  TRAY_EXEC="$target_bin/ovos-tray" python3 - "$tray_autostart" <<'PY'
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

  if "$tray_installed"; then
    pkill -f "$target_bin/ovos-tray" 2>/dev/null || true
    nohup "$target_bin/ovos-tray" > "$state_root/ovos-tray.log" 2>&1 &
  fi

  if "$restart"; then
    if command -v jarvis-restart >/dev/null 2>&1; then
      jarvis-restart
    elif systemctl --user cat ovos-core.service >/dev/null 2>&1; then
      systemctl --user restart ovos-core.service
    else
      echo "OVOS core service was not found; restart OVOS manually." >&2
    fi
  fi

  python3 "$target_root/scripts/doctor.py" --ovos-python "$ovos_python"
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

printf '%s\n' \
  "Installed Jarvis commands successfully." \
  "Configuration: $current_mode" \
  "Setup: jarvis-setup --gui" \
  "Doctor: jarvis-health-check" \
  "AI report: jarvis-report --issue \"Describe what failed\"" \
  "Rollback: bash $target_root/scripts/rollback.sh"
