#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$REPO_ROOT/system_helpers/jarvis-read-visible-text"
TARGET="$HOME/.local/bin/jarvis-read-visible-text"
STAMP="$(date +%Y%m%d-%H%M%S)"

bash -n "$SOURCE"
command -v xdotool >/dev/null
command -v xclip >/dev/null
command -v xprop >/dev/null
command -v flatpak >/dev/null

if [[ -f "$TARGET" ]]; then
    cp -a "$TARGET" "${TARGET}.before-universal-reader-${STAMP}"
fi

install -m 0755 "$SOURCE" "$TARGET"

echo "Universal focused-content reader installed."
echo "No OVOS restart is required."
echo "Rollback: ${TARGET}.before-universal-reader-${STAMP}"
