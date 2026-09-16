#!/usr/bin/env bash
set -euo pipefail

jarvis_home="${JARVIS_HOME:-$HOME}"
bin_dir="$jarvis_home/.local/bin"
config_dir="$jarvis_home/.config/jarvis"
state_root="$jarvis_home/.local/state/jarvis-command-editor"
latest="$state_root/latest-backup"

[[ -f "$latest" ]] || {
  echo "No command-editor rollback was found." >&2
  exit 1
}
backup_dir="$(<"$latest")"

BACKUP_DIR="$backup_dir" STATE_ROOT="$state_root" python3 <<'PY'
import os
from pathlib import Path

backup = Path(os.environ["BACKUP_DIR"]).resolve()
base = (Path(os.environ["STATE_ROOT"]) / "backups").resolve()
if backup == base or base not in backup.parents or not backup.is_dir():
    raise SystemExit(f"Unsafe or missing rollback directory: {backup}")
PY

mkdir -p "$bin_dir" "$config_dir"

restore_file() {
  local name="$1"
  local target="$2"
  local mode="$3"
  if [[ -f "$backup_dir/$name.missing" ]]; then
    rm -f -- "$target"
  else
    install -m "$mode" "$backup_dir/$name" "$target"
  fi
}

restore_file jarvis-command-editor "$bin_dir/jarvis-command-editor" 0755
restore_file \
  builtin-command-phrases.json \
  "$config_dir/builtin-command-phrases.json" \
  0600

echo "Command editor rollback restored. Personal phrases were preserved."
