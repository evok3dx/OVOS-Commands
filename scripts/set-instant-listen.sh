#!/usr/bin/env bash
set -euo pipefail

mode="${1:-}"
config="${XDG_CONFIG_HOME:-$HOME/.config}/mycroft/mycroft.conf"

case "$mode" in
  enable|disable|status)
    ;;
  *)
    echo "Usage: $0 {enable|disable|status}" >&2
    exit 2
    ;;
esac

if [[ ! -f "$config" ]]; then
    echo "OVOS configuration not found: $config" >&2
    exit 1
fi

if [[ "$mode" == "status" ]]; then
    CONFIG="$config" python3 <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["CONFIG"])
config = json.loads(path.read_text(encoding="utf-8"))
value = config.get("listener", {}).get("instant_listen", False)
print(f"instant_listen: {str(bool(value)).lower()}")
PY
    exit 0
fi

stamp="$(date +%Y%m%d-%H%M%S-%N)"
backup="${config}.before-instant-listen-${stamp}"
cp -a "$config" "$backup"

CONFIG="$config" MODE="$mode" python3 <<'PY'
import json
import os
import tempfile
from pathlib import Path

path = Path(os.environ["CONFIG"])
enabled = os.environ["MODE"] == "enable"
config = json.loads(path.read_text(encoding="utf-8"))
config.setdefault("listener", {})["instant_listen"] = enabled

descriptor, temporary_name = tempfile.mkstemp(
    prefix=f".{path.name}.",
    dir=path.parent,
    text=True,
)
try:
    with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
        json.dump(config, temporary, indent=2)
        temporary.write("\n")
        temporary.flush()
        os.fsync(temporary.fileno())
    os.chmod(temporary_name, path.stat().st_mode & 0o777)
    os.replace(temporary_name, path)
except Exception:
    try:
        os.unlink(temporary_name)
    except FileNotFoundError:
        pass
    raise
PY

echo "Updated: $config"
echo "Backup:  $backup"
echo "instant_listen: $([[ "$mode" == "enable" ]] && echo true || echo false)"
echo "Run: jarvis-restart --full"
