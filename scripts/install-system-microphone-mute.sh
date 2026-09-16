#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$REPO_ROOT/ovos_skill_jarvis_dispatcher"
TARGET="$HOME/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher"
SOURCE_HELPER="$REPO_ROOT/system_helpers/jarvis-system-microphone"
TARGET_HELPER="$HOME/.local/bin/jarvis-system-microphone"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="${TARGET}.before-system-microphone-mute-${STAMP}"

if [[ ! -d "$TARGET" ]]; then
    echo "Dispatcher package not found: $TARGET" >&2
    exit 1
fi

if ! command -v wpctl >/dev/null 2>&1 && \
   ! command -v pactl >/dev/null 2>&1; then
    echo "Neither wpctl nor pactl is available." >&2
    exit 1
fi

python3 -m py_compile \
  "$SOURCE/__init__.py" \
  "$SOURCE/system_audio.py" \
  "$SOURCE/vocabulary.py"

cp -a "$TARGET" "$BACKUP"
install -m 0644 "$SOURCE/__init__.py" "$TARGET/__init__.py"
install -m 0644 "$SOURCE/system_audio.py" "$TARGET/system_audio.py"
install -m 0644 "$SOURCE/vocabulary.py" "$TARGET/vocabulary.py"

mkdir -p "$HOME/.local/bin"
if [[ -f "$TARGET_HELPER" ]]; then
    cp -a "$TARGET_HELPER" "${TARGET_HELPER}.before-${STAMP}"
fi
install -m 0755 "$SOURCE_HELPER" "$TARGET_HELPER"

python3 -m py_compile "$TARGET/"*.py "$TARGET/integrations/"*.py

echo "System microphone mute commands installed."
echo "Rollback package: $BACKUP"
echo "Manual unmute: $TARGET_HELPER unmute"
echo "Restarting Jarvis once..."
jarvis-restart
