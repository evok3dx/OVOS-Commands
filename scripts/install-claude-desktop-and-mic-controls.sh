#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$REPO_ROOT/ovos_skill_jarvis_dispatcher"
TARGET="$HOME/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher"
SOURCE_SYSTEM_MIC="$REPO_ROOT/system_helpers/jarvis-system-microphone"
TARGET_SYSTEM_MIC="$HOME/.local/bin/jarvis-system-microphone"
JARVIS_MIC_TOGGLE="$HOME/.local/bin/jarvis-mic-toggle"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="${TARGET}.before-claude-desktop-and-mic-controls-${STAMP}"

if [[ ! -d "$TARGET" ]]; then
    echo "Dispatcher package not found: $TARGET" >&2
    exit 1
fi

if [[ ! -x "$JARVIS_MIC_TOGGLE" ]]; then
    echo "Existing Jarvis microphone toggle not found: $JARVIS_MIC_TOGGLE" >&2
    exit 1
fi

if ! command -v wpctl >/dev/null 2>&1 && \
   ! command -v pactl >/dev/null 2>&1; then
    echo "Neither wpctl nor pactl is available." >&2
    exit 1
fi

python3 -m py_compile \
  "$SOURCE/__init__.py" \
  "$SOURCE/conversation.py" \
  "$SOURCE/system_audio.py" \
  "$SOURCE/vocabulary.py" \
  "$SOURCE/integrations/claude_desktop.py"

cp -a "$TARGET" "$BACKUP"
install -m 0644 "$SOURCE/__init__.py" "$TARGET/__init__.py"
install -m 0644 "$SOURCE/conversation.py" "$TARGET/conversation.py"
install -m 0644 "$SOURCE/system_audio.py" "$TARGET/system_audio.py"
install -m 0644 "$SOURCE/vocabulary.py" "$TARGET/vocabulary.py"
install -m 0644 \
  "$SOURCE/integrations/claude_desktop.py" \
  "$TARGET/integrations/claude_desktop.py"

mkdir -p "$HOME/.local/bin"
if [[ -f "$TARGET_SYSTEM_MIC" ]]; then
    cp -a "$TARGET_SYSTEM_MIC" "${TARGET_SYSTEM_MIC}.before-${STAMP}"
fi
install -m 0755 "$SOURCE_SYSTEM_MIC" "$TARGET_SYSTEM_MIC"

python3 -m py_compile "$TARGET/"*.py "$TARGET/integrations/"*.py

echo "Claude Desktop routing and microphone controls installed."
echo "Rollback package: $BACKUP"
echo "Restarting Jarvis once..."
jarvis-restart
