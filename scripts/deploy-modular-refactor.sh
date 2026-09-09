#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_PACKAGE="$REPO_ROOT/ovos_skill_jarvis_dispatcher"
TARGET_PACKAGE="$HOME/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="${TARGET_PACKAGE}.before-modular-refactor-${STAMP}"

branch="$(git -C "$REPO_ROOT" branch --show-current)"
if [[ "$branch" != "modular-refactor" ]]; then
    echo "Refusing deployment from branch: $branch"
    echo "Check out modular-refactor first."
    exit 1
fi

python3 "$REPO_ROOT/scripts/validate_refactor.py"

if [[ ! -d "$TARGET_PACKAGE" ]]; then
    echo "Target package not found: $TARGET_PACKAGE"
    exit 1
fi

cp -a "$TARGET_PACKAGE" "$BACKUP"

for module in \
    __init__.py \
    agents.py \
    browser.py \
    conversation.py \
    desktop.py \
    dictation.py \
    helpers.py \
    vocabulary.py \
    wakeword.py; do
    install -m 0644 "$SOURCE_PACKAGE/$module" "$TARGET_PACKAGE/$module"
done

python3 -m py_compile "$TARGET_PACKAGE"/*.py

echo "Deployed modular dispatcher."
echo "Rollback copy: $BACKUP"
echo "Restarting Jarvis..."
jarvis-restart

systemctl --user --no-pager --full status ovos-core.service

