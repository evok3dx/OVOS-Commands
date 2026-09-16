#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_PACKAGE="$REPO_ROOT/ovos_skill_jarvis_dispatcher"
TARGET_PACKAGE="$HOME/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="${TARGET_PACKAGE}.before-youtube-commands-${STAMP}"

python3 "$REPO_ROOT/scripts/validate_refactor.py"

if [[ ! -d "$TARGET_PACKAGE" ]]; then
    echo "Target package not found: $TARGET_PACKAGE" >&2
    exit 1
fi

mkdir -p "$BACKUP"
for module in __init__.py browser.py custom_commands.py vocabulary.py; do
    cp -a "$TARGET_PACKAGE/$module" "$BACKUP/$module"
    install -m 0644 "$SOURCE_PACKAGE/$module" "$TARGET_PACKAGE/$module"
done

python3 -m py_compile \
  "$TARGET_PACKAGE/__init__.py" \
  "$TARGET_PACKAGE/browser.py" \
  "$TARGET_PACKAGE/custom_commands.py" \
  "$TARGET_PACKAGE/vocabulary.py"

echo "Installed YouTube search and Shorts voice commands."
echo "Rollback copy: $BACKUP"
echo "Restarting Jarvis..."
jarvis-restart
