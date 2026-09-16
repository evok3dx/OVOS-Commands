#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_PACKAGE="$REPO_ROOT/ovos_skill_jarvis_dispatcher"
TARGET_PACKAGE="$HOME/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher"
STAMP="$(date +%Y%m%d-%H%M%S)"

for module in browser.py desktop.py dictation.py helpers.py; do
    python3 -m py_compile "$SOURCE_PACKAGE/$module"

    if [[ -f "$TARGET_PACKAGE/$module" ]]; then
        cp -a \
          "$TARGET_PACKAGE/$module" \
          "$TARGET_PACKAGE/${module}.before-quiet-feedback-${STAMP}"
    fi

    install -m 0644 \
      "$SOURCE_PACKAGE/$module" \
      "$TARGET_PACKAGE/$module"
done

python3 -m py_compile "$TARGET_PACKAGE"/*.py

echo "Quiet feedback update installed."
echo "Restarting Jarvis core once..."
jarvis-restart
