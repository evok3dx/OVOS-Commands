#!/usr/bin/env bash
set -euo pipefail

TARGET_PACKAGE="$HOME/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher"
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/jarvis"
STATE_ROOT="$HOME/.local/state/jarvis-command-editor"
LATEST="$STATE_ROOT/latest-backup"

if [[ ! -f "$LATEST" ]]; then
    echo "No command-editor rollback was found." >&2
    exit 1
fi
BACKUP_DIR="$(<"$LATEST")"
if [[ ! -d "$BACKUP_DIR" ]]; then
    echo "Rollback directory is missing: $BACKUP_DIR" >&2
    exit 1
fi

restore_file() {
    local target="$1"
    local label="$2"
    local mode="$3"
    if [[ -f "$BACKUP_DIR/$label.missing" ]]; then
        rm -f -- "$target"
    else
        install -m "$mode" "$BACKUP_DIR/$label" "$target"
    fi
}

restore_file "$TARGET_PACKAGE/__init__.py" package-init.py 0644
restore_file "$TARGET_PACKAGE/vocabulary.py" vocabulary.py 0644
restore_file "$TARGET_PACKAGE/custom_commands.py" custom_commands.py 0644
restore_file \
    "$TARGET_PACKAGE/integrations/claude_desktop.py" claude_desktop.py 0644
restore_file "$BIN_DIR/ovos-tray" ovos-tray 0755
restore_file "$BIN_DIR/jarvis-command-editor" jarvis-command-editor 0755
restore_file \
    "$CONFIG_DIR/builtin-command-phrases.json" builtin-command-phrases.json 0600

pkill -f "$BIN_DIR/ovos-tray" 2>/dev/null || true
if [[ -x "$BIN_DIR/ovos-tray" ]]; then
    nohup "$BIN_DIR/ovos-tray" > "$HOME/.local/state/ovos-tray.log" 2>&1 &
fi
"$BIN_DIR/jarvis-restart"

echo "Command editor removed and previous files restored."
echo "Personal phrases were preserved in $CONFIG_DIR/custom-commands.json"
