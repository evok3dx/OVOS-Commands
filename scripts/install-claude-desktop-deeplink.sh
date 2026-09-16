#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$REPO_ROOT/ovos_skill_jarvis_dispatcher"
TARGET="$HOME/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="${TARGET}.before-claude-desktop-deeplink-${STAMP}"

if [[ ! -d "$TARGET" ]]; then
    echo "Dispatcher package not found: $TARGET" >&2
    exit 1
fi

for command in xdg-open xdotool; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Required command not found: $command" >&2
        exit 1
    fi
done

python3 -m py_compile \
  "$SOURCE/__init__.py" \
  "$SOURCE/conversation.py" \
  "$SOURCE/custom_commands.py" \
  "$SOURCE/vocabulary.py" \
  "$SOURCE/integrations/claude_desktop.py"

cp -a "$TARGET" "$BACKUP"
install -m 0644 "$SOURCE/__init__.py" "$TARGET/__init__.py"
install -m 0644 "$SOURCE/conversation.py" "$TARGET/conversation.py"
install -m 0644 "$SOURCE/custom_commands.py" "$TARGET/custom_commands.py"
install -m 0644 "$SOURCE/vocabulary.py" "$TARGET/vocabulary.py"
install -m 0644 \
  "$SOURCE/integrations/claude_desktop.py" \
  "$TARGET/integrations/claude_desktop.py"

python3 -m py_compile "$TARGET/"*.py "$TARGET/integrations/"*.py

echo "Claude Desktop deep-link messaging installed."
echo "Rollback package: $BACKUP"
echo "Restarting Jarvis once..."
jarvis-restart
