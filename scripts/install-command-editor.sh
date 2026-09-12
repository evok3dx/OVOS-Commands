#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_PACKAGE="$REPO_ROOT/ovos_skill_jarvis_dispatcher"
TARGET_PACKAGE="$HOME/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher"
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/jarvis"
STATE_ROOT="$HOME/.local/state/jarvis-command-editor"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$STATE_ROOT/backups/$STAMP"
OVOS_PYTHON="$HOME/.venvs/ovos/bin/python"

if [[ ! -d "$TARGET_PACKAGE" ]]; then
    echo "Jarvis dispatcher not found: $TARGET_PACKAGE" >&2
    exit 1
fi
if [[ ! -x "$OVOS_PYTHON" ]]; then
    echo "OVOS Python not found: $OVOS_PYTHON" >&2
    exit 1
fi
if ! python3 -c 'import gi; gi.require_version("Gtk", "3.0")' 2>/dev/null; then
    echo "GTK 3 support is missing." >&2
    echo "Install: sudo apt install python3-gi gir1.2-gtk-3.0" >&2
    exit 1
fi

python3 "$REPO_ROOT/scripts/validate_refactor.py"
python3 -m py_compile \
    "$REPO_ROOT/command_editor/jarvis-command-editor" \
    "$REPO_ROOT/tray/ovos-tray.py"

mkdir -p "$BACKUP_DIR" "$BIN_DIR" "$CONFIG_DIR"

backup_file() {
    local source="$1"
    local label="$2"
    if [[ -e "$source" ]]; then
        cp -a "$source" "$BACKUP_DIR/$label"
    else
        : > "$BACKUP_DIR/$label.missing"
    fi
}

backup_file "$TARGET_PACKAGE/__init__.py" package-init.py
backup_file "$TARGET_PACKAGE/vocabulary.py" vocabulary.py
backup_file "$TARGET_PACKAGE/custom_commands.py" custom_commands.py
backup_file "$TARGET_PACKAGE/integrations/claude_desktop.py" claude_desktop.py
backup_file "$BIN_DIR/ovos-tray" ovos-tray
backup_file "$BIN_DIR/jarvis-command-editor" jarvis-command-editor
backup_file "$CONFIG_DIR/builtin-command-phrases.json" builtin-command-phrases.json
printf '%s\n' "$BACKUP_DIR" > "$STATE_ROOT/latest-backup"

install -m 0644 "$SOURCE_PACKAGE/__init__.py" "$TARGET_PACKAGE/__init__.py"
install -m 0644 "$SOURCE_PACKAGE/vocabulary.py" "$TARGET_PACKAGE/vocabulary.py"
install -m 0644 "$SOURCE_PACKAGE/custom_commands.py" "$TARGET_PACKAGE/custom_commands.py"
install -m 0644 \
    "$SOURCE_PACKAGE/integrations/claude_desktop.py" \
    "$TARGET_PACKAGE/integrations/claude_desktop.py"
install -m 0755 \
    "$REPO_ROOT/command_editor/jarvis-command-editor" \
    "$BIN_DIR/jarvis-command-editor"
install -m 0755 "$REPO_ROOT/tray/ovos-tray.py" "$BIN_DIR/ovos-tray"

PYTHONPATH="${TARGET_PACKAGE%/*}" \
JARVIS_BUILTINS_PATH="$CONFIG_DIR/builtin-command-phrases.json" \
"$OVOS_PYTHON" <<'PY'
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

pkill -f "$BIN_DIR/ovos-tray" 2>/dev/null || true
nohup "$BIN_DIR/ovos-tray" > "$HOME/.local/state/ovos-tray.log" 2>&1 &
"$BIN_DIR/jarvis-restart"

echo "Command editor installed."
echo "Open the tray icon and choose Commands…"
echo "Rollback: bash scripts/uninstall-command-editor.sh"
