#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$REPO_ROOT/ovos_skill_jarvis_dispatcher"
TARGET="$HOME/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="${TARGET}.before-text-editing-${STAMP}"

if [[ ! -d "$TARGET" ]]; then
    echo "Dispatcher package not found: $TARGET" >&2
    exit 1
fi

python3 -m py_compile \
  "$SOURCE/__init__.py" \
  "$SOURCE/text_editing.py" \
  "$SOURCE/vocabulary.py"

cp -a "$TARGET" "$BACKUP"

install -m 0644 "$SOURCE/__init__.py" "$TARGET/__init__.py"
install -m 0644 "$SOURCE/text_editing.py" "$TARGET/text_editing.py"
install -m 0644 "$SOURCE/vocabulary.py" "$TARGET/vocabulary.py"

python3 -m py_compile \
  "$TARGET/"*.py \
  "$TARGET/integrations/"*.py

echo "Focused text-editing commands installed."
echo "Rollback package: $BACKUP"
echo "Restarting Jarvis once..."
jarvis-restart
