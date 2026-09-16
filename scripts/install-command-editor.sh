#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
jarvis_home="${JARVIS_HOME:-$HOME}"
target_package="$jarvis_home/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher"
bin_dir="$jarvis_home/.local/bin"
config_dir="$jarvis_home/.config/jarvis"
state_root="$jarvis_home/.local/state/jarvis-command-editor"
stamp="$(date +%Y%m%d-%H%M%S-%N)"
backup_dir="$state_root/backups/$stamp"
ovos_python="${OVOS_PYTHON:-$jarvis_home/.venvs/ovos/bin/python}"
desktop_python="${JARVIS_DESKTOP_PYTHON:-/usr/bin/python3}"

[[ -d "$target_package" ]] || {
  echo "Jarvis dispatcher not found: $target_package" >&2
  exit 1
}
[[ -x "$ovos_python" ]] || {
  echo "OVOS Python not found: $ovos_python" >&2
  exit 1
}
if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]] &&
   ! "$desktop_python" -c 'import gi; gi.require_version("Gtk", "3.0")' 2>/dev/null; then
  echo "GTK 3 support is missing." >&2
  echo "Install: sudo apt install python3-gi gir1.2-gtk-3.0" >&2
  exit 1
fi

python3 "$repo_root/scripts/validate_refactor.py"
"$desktop_python" -m py_compile "$repo_root/command_editor/jarvis-command-editor"

mkdir -p "$backup_dir" "$bin_dir" "$config_dir"
for name in jarvis-command-editor builtin-command-phrases.json; do
  case "$name" in
    jarvis-command-editor) target="$bin_dir/$name" ;;
    *) target="$config_dir/$name" ;;
  esac
  if [[ -e "$target" ]]; then
    cp -a "$target" "$backup_dir/$name"
  else
    : > "$backup_dir/$name.missing"
  fi
done
printf '%s\n' "$backup_dir" > "$state_root/latest-backup"

install -m 0755 \
  "$repo_root/command_editor/jarvis-command-editor" \
  "$bin_dir/jarvis-command-editor"

PYTHONPATH="${target_package%/*}" \
JARVIS_BUILTINS_PATH="$config_dir/builtin-command-phrases.json" \
"$ovos_python" <<'PY'
import json
import os
import tempfile
from pathlib import Path

from ovos_skill_jarvis_dispatcher.custom_commands import (
    DEFAULT_CONFIG_PATH,
    collect_builtin_inventory,
    collect_builtin_phrases,
    write_mapping,
)
from ovos_skill_jarvis_dispatcher.profile import load_profile

profile = load_profile()
phrases = sorted(collect_builtin_phrases(profile))
inventory = collect_builtin_inventory(profile)
target = Path(os.environ["JARVIS_BUILTINS_PATH"])
descriptor, temporary_name = tempfile.mkstemp(
    prefix="builtin-command-phrases.", suffix=".tmp", dir=target.parent
)
with os.fdopen(descriptor, "w", encoding="utf-8") as output:
    json.dump(
        {"version": 1, "phrases": phrases, "actions": inventory},
        output,
        indent=2,
        sort_keys=True,
    )
    output.write("\n")
os.chmod(temporary_name, 0o600)
os.replace(temporary_name, target)
if not DEFAULT_CONFIG_PATH.exists():
    write_mapping({}, profile=profile, builtin_phrases=phrases)
PY

printf '%s\n' \
  "Command editor installed: $bin_dir/jarvis-command-editor" \
  "Install the optional tray to open it from the status menu." \
  "Rollback: bash scripts/uninstall-command-editor.sh"
