#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
manifest="$repo_root/deployment-manifest.json"
jarvis_home="${JARVIS_HOME:-$HOME}"
state_root="$jarvis_home/.local/state/jarvis"
backup_base="$state_root/backups"
latest="$state_root/latest-backup"
target_root="$jarvis_home/.local/src/ovos-skill-jarvis-dispatcher"
target_bin="$jarvis_home/.local/bin"
target_profile="$jarvis_home/.config/jarvis/profile.json"
target_capabilities="$jarvis_home/.config/jarvis/capabilities.json"
systemd_dir="$jarvis_home/.config/systemd/user"
launcher="$jarvis_home/.local/share/applications/hermes.desktop"
tray_icon_dir="$jarvis_home/.local/share/icons/ovos-tray"
tray_autostart="$jarvis_home/.config/autostart/ovos-tray.desktop"
mic_icon_dir="$jarvis_home/.local/share/jarvis"
mic_autostart="$jarvis_home/.config/autostart/jarvis-mic-indicator.desktop"
ovos_config="$jarvis_home/.config/mycroft/mycroft.conf"
listening_sound="$jarvis_home/.local/share/ovos/sounds/jarvis-ready.wav"
shortcut_state="$jarvis_home/.config/jarvis/listen-shortcut.json"
ovos_python="${OVOS_PYTHON:-$jarvis_home/.venvs/ovos/bin/python}"
backup_root=""
restart=true

usage() {
  echo "Usage: scripts/rollback.sh [BACKUP] [--no-restart] [--ovos-python PATH]" >&2
}

while (($#)); do
  case "$1" in
    --no-restart)
      restart=false
      shift
      ;;
    --ovos-python)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      ovos_python="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      usage
      exit 2
      ;;
    *)
      [[ -z "$backup_root" ]] || { usage; exit 2; }
      backup_root="$1"
      shift
      ;;
  esac
done

if [[ -z "$backup_root" ]]; then
  [[ -f "$latest" ]] || {
    echo "No Jarvis deployment backup was found." >&2
    exit 1
  }
  backup_root="$(<"$latest")"
fi

BACKUP_ROOT="$backup_root" BACKUP_BASE="$backup_base" python3 <<'PY'
import os
from pathlib import Path

backup = Path(os.environ["BACKUP_ROOT"]).resolve()
base = Path(os.environ["BACKUP_BASE"]).resolve()
if backup == base or base not in backup.parents:
    raise SystemExit(f"Refusing backup path outside {base}: {backup}")
if not backup.is_dir():
    raise SystemExit(f"Backup directory not found: {backup}")
PY

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

restore_file() {
  local saved="$1"
  local target="$2"
  local mode="$3"
  mkdir -p "$(dirname "$target")"
  if [[ -f "$saved.missing" ]]; then
    rm -f -- "$target"
  elif [[ -f "$saved" ]]; then
    install -m "$mode" "$saved" "$target"
  else
    echo "Backup entry is missing: $saved" >&2
    exit 1
  fi
}

validate_restore_entry() {
  local saved="$1"
  [[ -f "$saved" || -f "$saved.missing" ]] || {
    echo "Backup entry is missing: $saved" >&2
    exit 1
  }
}

if [[ ! -d "$backup_root/target-root" && ! -f "$backup_root/target-root.missing" ]]; then
  echo "Target source backup is incomplete: $backup_root" >&2
  exit 1
fi
validate_restore_entry "$backup_root/profile.json"
validate_restore_entry "$backup_root/capabilities.json"
if [[ -f "$backup_root/router.json" || -f "$backup_root/router.json.missing" ]]; then
  validate_restore_entry "$backup_root/router.json"
fi
for helper in "${runtime_helpers[@]}"; do
  validate_restore_entry "$backup_root/helpers/$helper"
done
for unit in \
  hermes-launcher-repair.service \
  hermes-launcher-repair.path \
  jarvis-health-check.service \
  jarvis-health-check.timer \
  jarvis-update-check.service \
  jarvis-update-check.timer; do
  validate_restore_entry "$backup_root/systemd/$unit"
done
validate_restore_entry "$backup_root/hermes.desktop"
validate_restore_entry "$backup_root/tray/ovos-tray"
validate_restore_entry "$backup_root/tray/ovos-tray.desktop"
for icon in \
  ovos-ready.svg ovos-ready-update.svg \
  ovos-starting.svg ovos-starting-update.svg \
  ovos-stopped.svg ovos-stopped-update.svg \
  ovos-failed.svg ovos-failed-update.svg; do
  validate_restore_entry "$backup_root/tray/$icon"
done
validate_restore_entry "$backup_root/mic/jarvis-mic-indicator"
validate_restore_entry "$backup_root/mic/jarvis-mic-toggle"
validate_restore_entry "$backup_root/mic/jarvis-mic-indicator.desktop"
validate_restore_entry "$backup_root/mic/mic-active.svg"
validate_restore_entry "$backup_root/mic/mic-muted.svg"
validate_restore_entry "$backup_root/mycroft.conf"
validate_restore_entry "$backup_root/sounds/jarvis-ready.wav"
validate_restore_entry "$backup_root/listen-shortcut.json"
[[ -f "$backup_root/managed-packages.json" ]] || {
  echo "Backup entry is missing: $backup_root/managed-packages.json" >&2
  exit 1
}
[[ -f "$backup_root/cinnamon-shortcuts.state" ]] || {
  echo "Backup entry is missing: $backup_root/cinnamon-shortcuts.state" >&2
  exit 1
}

# Stop the process belonging to the deployment being replaced. A failed fresh
# install must not leave a tray whose helper files have just been removed.
if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]]; then
  pkill -f "$target_bin/ovos-tray" 2>/dev/null || true
  pkill -f "$target_bin/jarvis-mic-indicator" 2>/dev/null || true
fi

retired_base="$state_root/retired"
retired_root="$retired_base/rollback-$(date +%Y%m%d-%H%M%S-%N)"
mkdir -p "$retired_base"
if [[ -d "$target_root" ]]; then
  mv -- "$target_root" "$retired_root"
fi

if [[ -d "$backup_root/target-root" ]]; then
  cp -a "$backup_root/target-root" "$target_root"
elif [[ ! -f "$backup_root/target-root.missing" ]]; then
  echo "Target source backup is incomplete: $backup_root" >&2
  exit 1
fi

restore_file "$backup_root/profile.json" "$target_profile" 0600
restore_file "$backup_root/capabilities.json" "$target_capabilities" 0600
if [[ -f "$backup_root/router.json" || -f "$backup_root/router.json.missing" ]]; then
  restore_file "$backup_root/router.json" "$jarvis_home/.config/jarvis/router.json" 0600
fi
for helper in "${runtime_helpers[@]}"; do
  restore_file "$backup_root/helpers/$helper" "$target_bin/$helper" 0755
done
for unit in \
  hermes-launcher-repair.service \
  hermes-launcher-repair.path \
  jarvis-health-check.service \
  jarvis-health-check.timer \
  jarvis-update-check.service \
  jarvis-update-check.timer; do
  restore_file "$backup_root/systemd/$unit" "$systemd_dir/$unit" 0644
done
restore_file "$backup_root/hermes.desktop" "$launcher" 0644
restore_file "$backup_root/tray/ovos-tray" "$target_bin/ovos-tray" 0755
restore_file "$backup_root/tray/ovos-tray.desktop" "$tray_autostart" 0644
for icon in \
  ovos-ready.svg ovos-ready-update.svg \
  ovos-starting.svg ovos-starting-update.svg \
  ovos-stopped.svg ovos-stopped-update.svg \
  ovos-failed.svg ovos-failed-update.svg; do
  restore_file "$backup_root/tray/$icon" "$tray_icon_dir/$icon" 0644
done
restore_file "$backup_root/mic/jarvis-mic-indicator" \
  "$target_bin/jarvis-mic-indicator" 0755
restore_file "$backup_root/mic/jarvis-mic-toggle" \
  "$target_bin/jarvis-mic-toggle" 0755
restore_file "$backup_root/mic/jarvis-mic-indicator.desktop" \
  "$mic_autostart" 0644
restore_file "$backup_root/mic/mic-active.svg" \
  "$mic_icon_dir/mic-active.svg" 0644
restore_file "$backup_root/mic/mic-muted.svg" \
  "$mic_icon_dir/mic-muted.svg" 0644
restore_file "$backup_root/mycroft.conf" "$ovos_config" 0600
restore_file "$backup_root/sounds/jarvis-ready.wav" "$listening_sound" 0644
restore_file "$backup_root/listen-shortcut.json" "$shortcut_state" 0600

if [[ "${JARVIS_TEST_MODE:-0}" != 1 && \
      "$(<"$backup_root/cinnamon-shortcuts.state")" == available ]]; then
  shortcut_script="$repo_root/scripts/listen-shortcut.py"
  [[ -f "$shortcut_script" ]] || shortcut_script="$retired_root/scripts/listen-shortcut.py"
  /usr/bin/python3 "$shortcut_script" \
    --restore-snapshot "$backup_root/cinnamon-shortcuts.json"
fi

if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]]; then
  [[ -x "$ovos_python" ]] || {
    echo "OVOS virtualenv Python not found: $ovos_python" >&2
    exit 1
  }
  if [[ -d "$target_root" ]]; then
    "$ovos_python" -m pip install --disable-pip-version-check \
      --no-deps --editable "$target_root"
  else
    "$ovos_python" -m pip uninstall --yes ovos-skill-jarvis-dispatcher >/dev/null
  fi

  mapfile -t restore_requirements < <(python3 - "$backup_root/managed-packages.json" <<'PY'
import json
import sys
from pathlib import Path

for package, saved in json.loads(Path(sys.argv[1]).read_text()).items():
    if isinstance(saved, dict):
        version = saved.get("version")
        direct = saved.get("direct_url") or {}
    else:  # Backward compatibility with pre-2.2.8 backups.
        version = saved
        direct = {}
    if version is None:
        continue
    url = direct.get("url")
    vcs = direct.get("vcs_info") or {}
    if url and vcs.get("vcs") and vcs.get("commit_id"):
        print(f"{package} @ {vcs['vcs']}+{url}@{vcs['commit_id']}")
    elif url:
        archive = direct.get("archive_info") or {}
        digest = archive.get("hash")
        suffix = f"#{digest}" if digest and "#" not in url else ""
        print(f"{package} @ {url}{suffix}")
    else:
        print(f"{package}=={version}")
PY
)
  mapfile -t remove_packages < <(python3 - "$backup_root/managed-packages.json" <<'PY'
import json
import sys
from pathlib import Path
for package, saved in json.loads(Path(sys.argv[1]).read_text()).items():
    version = saved.get("version") if isinstance(saved, dict) else saved
    if version is None:
        print(package)
PY
)
  if ((${#restore_requirements[@]})); then
    "$ovos_python" -m pip install --disable-pip-version-check \
      "${restore_requirements[@]}"
  fi
  if ((${#remove_packages[@]})); then
    "$ovos_python" -m pip uninstall --yes "${remove_packages[@]}" >/dev/null 2>&1 || true
  fi
  if [[ -f "$backup_root/pronunciation-source" && \
        -f "$backup_root/pronunciation/mul.py" ]]; then
    pronunciation_source="$(<"$backup_root/pronunciation-source")"
    install -m 0644 "$backup_root/pronunciation/mul.py" "$pronunciation_source"
  fi

  systemctl --user daemon-reload
  for unit in hermes-launcher-repair.path jarvis-health-check.timer jarvis-update-check.timer; do
    state_file="$backup_root/$unit.state"
    if [[ "$unit" == hermes-launcher-repair.path && ! -f "$state_file" ]]; then
      state_file="$backup_root/hermes-path-unit-state"
    fi
    if [[ -f "$state_file" && "$(<"$state_file")" == enabled ]]; then
      systemctl --user enable --now "$unit" >/dev/null
    else
      systemctl --user disable --now "$unit" >/dev/null 2>&1 || true
    fi
  done

  if [[ -x "$target_bin/ovos-tray" && -f "$tray_autostart" ]]; then
    nohup "$target_bin/ovos-tray" > "$state_root/ovos-tray.log" 2>&1 &
  fi
  if [[ -x "$target_bin/jarvis-mic-indicator" && -f "$mic_autostart" ]] && \
     ! grep -Eq '^(Hidden=true|X-GNOME-Autostart-enabled=false)$' "$mic_autostart"; then
    nohup "$target_bin/jarvis-mic-indicator" \
      > "$state_root/jarvis-mic-indicator.log" 2>&1 &
  fi

  if "$restart"; then
    if [[ -x "$target_bin/jarvis-restart" ]]; then
      "$target_bin/jarvis-restart" --full
    elif systemctl --user cat ovos-core.service >/dev/null 2>&1; then
      systemctl --user stop \
        ovos-core.service ovos-listener.service ovos-audio.service
      systemctl --user start ovos-audio.service
      systemctl --user start ovos-listener.service
      systemctl --user start ovos-core.service
    fi
  fi
fi

printf '%s\n' \
  "Restored Jarvis deployment from: $backup_root" \
  "Replaced deployment retained at: $retired_root"
