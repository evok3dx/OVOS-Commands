#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_PACKAGE="$REPO_ROOT/ovos_skill_jarvis_dispatcher"
TARGET_PACKAGE="$HOME/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher"
SOURCE_WINDOW_HELPER="$REPO_ROOT/system_helpers/jarvis-focused-window"
TARGET_WINDOW_HELPER="$HOME/.local/bin/jarvis-focused-window"
SOURCE_READER_HELPER="$REPO_ROOT/system_helpers/jarvis-read-visible-text"
TARGET_READER_HELPER="$HOME/.local/bin/jarvis-read-visible-text"
SOURCE_APP_HELPER="$REPO_ROOT/system_helpers/jarvis-app-window"
TARGET_APP_HELPER="$HOME/.local/bin/jarvis-app-window"
PROFILE_NAME="${JARVIS_PROFILE:-brain}"
SOURCE_PROFILE="$REPO_ROOT/profiles/$PROFILE_NAME.json"
TARGET_PROFILE_DIR="$HOME/.config/jarvis"
TARGET_PROFILE="$TARGET_PROFILE_DIR/profile.json"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="${TARGET_PACKAGE}.before-modular-refactor-${STAMP}"

python3 "$REPO_ROOT/scripts/validate_refactor.py"

if [[ ! "$PROFILE_NAME" =~ ^[a-zA-Z0-9._-]+$ ]] || \
   [[ ! -f "$SOURCE_PROFILE" ]]; then
    echo "Profile not found: $SOURCE_PROFILE" >&2
    exit 1
fi

# Resolve the selected profile before touching any live files. This catches
# invalid JSON, unknown categories and unsupported integration identifiers.
SOURCE_PROFILE="$SOURCE_PROFILE" SOURCE_PACKAGE="$SOURCE_PACKAGE" python3 <<'PY'
import importlib.util
import json
import os
from pathlib import Path

module_path = Path(os.environ["SOURCE_PACKAGE"]) / "profile.py"
spec = importlib.util.spec_from_file_location("jarvis_profile", module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.resolve_profile(
    json.loads(Path(os.environ["SOURCE_PROFILE"]).read_text(encoding="utf-8"))
)
PY

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
    profile.py \
    vocabulary.py \
    wakeword.py; do
    install -m 0644 "$SOURCE_PACKAGE/$module" "$TARGET_PACKAGE/$module"
done

mkdir -p "$TARGET_PACKAGE/integrations"
install -m 0644 \
  "$SOURCE_PACKAGE/integrations/__init__.py" \
  "$SOURCE_PACKAGE/integrations/standard_notes.py" \
  "$TARGET_PACKAGE/integrations/"

python3 -m py_compile \
  "$TARGET_PACKAGE"/*.py \
  "$TARGET_PACKAGE"/integrations/*.py

if [[ -f "$TARGET_WINDOW_HELPER" ]]; then
    cp -a \
      "$TARGET_WINDOW_HELPER" \
      "${TARGET_WINDOW_HELPER}.before-restore-window-${STAMP}"
fi
install -m 0755 "$SOURCE_WINDOW_HELPER" "$TARGET_WINDOW_HELPER"

if [[ -f "$TARGET_READER_HELPER" ]]; then
    cp -a \
      "$TARGET_READER_HELPER" \
      "${TARGET_READER_HELPER}.before-main-content-${STAMP}"
fi
install -m 0755 "$SOURCE_READER_HELPER" "$TARGET_READER_HELPER"

if [[ -f "$TARGET_APP_HELPER" ]]; then
    cp -a \
      "$TARGET_APP_HELPER" \
      "${TARGET_APP_HELPER}.before-profile-integrations-${STAMP}"
fi
install -m 0755 "$SOURCE_APP_HELPER" "$TARGET_APP_HELPER"

mkdir -p "$TARGET_PROFILE_DIR"
if [[ -f "$TARGET_PROFILE" ]]; then
    cp -a "$TARGET_PROFILE" "${TARGET_PROFILE}.before-${STAMP}"
fi
install -m 0600 "$SOURCE_PROFILE" "$TARGET_PROFILE"

echo "Deployed modular dispatcher."
echo "Rollback copy: $BACKUP"
echo "Profile: $PROFILE_NAME"
echo "Restarting Jarvis..."
jarvis-restart

systemctl --user --no-pager --full status ovos-core.service
