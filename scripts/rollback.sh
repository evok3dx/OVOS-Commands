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

  if "$restart"; then
    if command -v jarvis-restart >/dev/null 2>&1; then
      jarvis-restart
    elif systemctl --user cat ovos-core.service >/dev/null 2>&1; then
      systemctl --user restart ovos-core.service
    fi
  fi
fi

printf '%s\n' \
  "Restored Jarvis deployment from: $backup_root" \
  "Replaced deployment retained at: $retired_root"
