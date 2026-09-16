#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$REPO_ROOT/ovos_skill_jarvis_dispatcher/vocabulary.py"
TARGET_DIR="$HOME/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher"
TARGET="$TARGET_DIR/vocabulary.py"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="${TARGET}.before-search-phrases-${STAMP}"

if [[ ! -f "$TARGET" ]]; then
    echo "Dispatcher vocabulary not found: $TARGET" >&2
    exit 1
fi

python3 -m py_compile "$SOURCE"
cp -a "$TARGET" "$BACKUP"
install -m 0644 "$SOURCE" "$TARGET"
python3 -m py_compile "$TARGET_DIR/"*.py "$TARGET_DIR/integrations/"*.py

echo "Search phrase variants installed."
echo "Rollback file: $BACKUP"
echo "Restarting Jarvis once..."
jarvis-restart
