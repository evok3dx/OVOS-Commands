#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$REPO_ROOT/system_helpers/jarvis-app-window"
TARGET="$HOME/.local/bin/jarvis-app-window"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="${TARGET}.before-detached-launch-${STAMP}"

if [[ ! -f "$TARGET" ]]; then
    echo "Application helper not found: $TARGET" >&2
    exit 1
fi

/usr/bin/bash -n "$SOURCE"
cp -a "$TARGET" "$BACKUP"
install -m 0755 "$SOURCE" "$TARGET"
/usr/bin/bash -n "$TARGET"

echo "Detached application launcher installed."
echo "Brave target: Flatpak com.brave.Browser"
echo "Rollback file: $BACKUP"
echo "No Jarvis restart is required."
