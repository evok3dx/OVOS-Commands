#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_PACKAGE="$REPO_ROOT/ovos_skill_jarvis_dispatcher"
TARGET_PACKAGE="$HOME/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="${TARGET_PACKAGE}.before-hermes-system-controls-${STAMP}"

python3 "$REPO_ROOT/scripts/validate_refactor.py"

if [[ ! -d "$TARGET_PACKAGE" ]]; then
    echo "Target package not found: $TARGET_PACKAGE" >&2
    exit 1
fi

for dependency in /usr/bin/xdotool /usr/bin/xset /usr/bin/playerctl; do
    if [[ ! -x "$dependency" ]]; then
        echo "Required command is missing: $dependency" >&2
        if [[ "$dependency" == "/usr/bin/playerctl" ]]; then
            echo "Install it first with: sudo apt install playerctl" >&2
        fi
        exit 1
    fi
done

cp -a "$TARGET_PACKAGE" "$BACKUP"
mkdir -p "$TARGET_PACKAGE/integrations"

for module in \
    __init__.py \
    conversation.py \
    custom_commands.py \
    system_controls.py \
    vocabulary.py; do
    install -m 0644 "$SOURCE_PACKAGE/$module" "$TARGET_PACKAGE/$module"
done

install -m 0644 \
  "$SOURCE_PACKAGE/integrations/hermes_desktop.py" \
  "$TARGET_PACKAGE/integrations/hermes_desktop.py"

python3 -m py_compile \
  "$TARGET_PACKAGE"/*.py \
  "$TARGET_PACKAGE"/integrations/*.py

echo "Installed Enter, media, Caps Lock and Hermes messaging controls."
echo "Rollback copy: $BACKUP"
echo "Restarting Jarvis once..."
jarvis-restart
