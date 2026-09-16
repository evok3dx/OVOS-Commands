#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_PACKAGE="$REPO_ROOT/ovos_skill_jarvis_dispatcher"
TARGET_PACKAGE="$HOME/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher"
SOURCE_HELPER="$REPO_ROOT/system_helpers/jarvis-app-window"
TARGET_HELPER="$HOME/.local/bin/jarvis-app-window"
PROFILE="$HOME/.config/jarvis/profile.json"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="${TARGET_PACKAGE}.before-hermes-window-controls-${STAMP}"

python3 "$REPO_ROOT/scripts/validate_refactor.py"

if [[ ! -d "$TARGET_PACKAGE" ]]; then
    echo "Target package not found: $TARGET_PACKAGE" >&2
    exit 1
fi

if [[ ! -f "$PROFILE" ]]; then
    echo "Active Jarvis profile not found: $PROFILE" >&2
    exit 1
fi

mkdir -p "$BACKUP"
cp -a "$TARGET_PACKAGE/profile.py" "$BACKUP/profile.py"
cp -a "$TARGET_PACKAGE/vocabulary.py" "$BACKUP/vocabulary.py"
cp -a "$PROFILE" "${PROFILE}.before-hermes-window-controls-${STAMP}"

if [[ -f "$TARGET_HELPER" ]]; then
    cp -a "$TARGET_HELPER" "${TARGET_HELPER}.before-hermes-window-controls-${STAMP}"
fi

install -m 0644 "$SOURCE_PACKAGE/profile.py" "$TARGET_PACKAGE/profile.py"
install -m 0644 "$SOURCE_PACKAGE/vocabulary.py" "$TARGET_PACKAGE/vocabulary.py"
install -m 0755 "$SOURCE_HELPER" "$TARGET_HELPER"

python3 - "$PROFILE" <<'PY'
import json
import os
import sys
import tempfile
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
applications = data.get("applications")
if not isinstance(applications, dict):
    raise SystemExit("Profile applications must be a JSON object")

applications["hermes"] = "hermes_desktop"
payload = json.dumps(data, indent=2) + "\n"
fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
PY

python3 -m py_compile \
  "$TARGET_PACKAGE/profile.py" \
  "$TARGET_PACKAGE/vocabulary.py"

echo "Installed guarded Hermes Desktop window controls."
echo "Message and response scraping were deliberately not enabled."
echo "Rollback package: $BACKUP"
echo "Restarting Jarvis once..."
jarvis-restart
