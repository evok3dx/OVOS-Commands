#!/usr/bin/env bash
set -euo pipefail

TARGET="$HOME/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher/vocabulary.py"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="${TARGET}.before-address-variants-${STAMP}"

if [[ ! -f "$TARGET" ]]; then
    echo "Vocabulary file not found: $TARGET" >&2
    exit 1
fi

cp -a "$TARGET" "$BACKUP"

TARGET="$TARGET" python3 <<'PY'
import os
from pathlib import Path

path = Path(os.environ["TARGET"])
text = path.read_text(encoding="utf-8")

anchor = '    "focus the address bar": "address",\n'
if '    "focus address bar": "address",\n' not in text:
    if text.count(anchor) != 1:
        raise SystemExit("Focus-address anchor was not found exactly once.")
    text = text.replace(
        anchor,
        '    "focus address bar": "address",\n' + anchor,
        1,
    )

anchor = '    "go to the address bar": "address",\n'
if '    "go to address bar": "address",\n' not in text:
    if text.count(anchor) != 1:
        raise SystemExit("Go-to-address anchor was not found exactly once.")
    text = text.replace(
        anchor,
        anchor + '    "go to address bar": "address",\n',
        1,
    )

path.write_text(text, encoding="utf-8")
PY

python3 -m py_compile \
  "$HOME/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher/"*.py \
  "$HOME/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher/integrations/"*.py

for phrase in \
    '"focus address bar": "address"' \
    '"focus the address bar": "address"' \
    '"focus on the address bar": "address"' \
    '"go to address bar": "address"' \
    '"go to the address bar": "address"'; do
    rg -Fq "$phrase" "$TARGET" || {
        echo "Validation failed: $phrase" >&2
        exit 1
    }
done

echo "Address-bar variants installed."
echo "Rollback: $BACKUP"
echo "Restarting Jarvis once..."
jarvis-restart
