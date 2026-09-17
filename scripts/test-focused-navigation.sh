#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HELPER="$ROOT/system_helpers/jarvis-focused-navigation"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin"
export JARVIS_NAVIGATION_LOG="$tmp/navigation.log"
export JARVIS_ACTIVE_WINDOW_STATE="$tmp/active-window-state"

cat > "$tmp/bin/xdotool" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  getactivewindow)
    if [[ "${JARVIS_TEST_FOCUS_CHANGE:-0}" == 1 ]]; then
      count=0
      [[ -f "$JARVIS_ACTIVE_WINDOW_STATE" ]] && count="$(<"$JARVIS_ACTIVE_WINDOW_STATE")"
      printf '%s\n' "$((count + 1))" > "$JARVIS_ACTIVE_WINDOW_STATE"
      if ((count == 0)); then
        printf '%s\n' 4242
      else
        printf '%s\n' 5252
      fi
    else
      printf '%s\n' 4242
    fi
    ;;
  key|windowactivate)
    printf '%s\n' "$*" >> "$JARVIS_NAVIGATION_LOG"
    ;;
  *)
    exit 2
    ;;
esac
EOF

cat > "$tmp/bin/xprop" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

case "${@: -1}" in
  WM_CLASS)
    printf 'WM_CLASS(STRING) = "%s", "%s"\n' \
      "${JARVIS_TEST_WINDOW_CLASS:-Navigator}" \
      "${JARVIS_TEST_WINDOW_CLASS:-Firefox}"
    ;;
  _NET_WM_WINDOW_TYPE)
    printf '%s\n' "${JARVIS_TEST_WINDOW_TYPE:-_NET_WM_WINDOW_TYPE_NORMAL}"
    ;;
  *)
    exit 2
    ;;
esac
EOF

chmod +x "$tmp/bin/xdotool" "$tmp/bin/xprop"

: > "$JARVIS_NAVIGATION_LOG"
for action in scroll_down scroll_up page_down page_up top bottom; do
  PATH="$tmp/bin:$PATH" "$HELPER" "$action"
done

python3 - "$JARVIS_NAVIGATION_LOG" <<'PY'
import sys
from pathlib import Path

lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
assert lines == [
    "key --clearmodifiers --repeat 4 --delay 50 Down",
    "key --clearmodifiers --repeat 4 --delay 50 Up",
    "key --clearmodifiers Page_Down",
    "key --clearmodifiers Page_Up",
    "key --clearmodifiers ctrl+Home",
    "key --clearmodifiers ctrl+End",
], lines
assert all("--window" not in line for line in lines), lines
PY

: > "$JARVIS_NAVIGATION_LOG"
PATH="$tmp/bin:$PATH" JARVIS_TEST_WINDOW_CLASS="Gnome-terminal" \
  "$HELPER" page_down
PATH="$tmp/bin:$PATH" JARVIS_TEST_WINDOW_CLASS="Gnome-terminal" \
  "$HELPER" top
python3 - "$JARVIS_NAVIGATION_LOG" <<'PY'
import sys
from pathlib import Path

lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
assert lines == [
    "windowactivate --sync 4242",
    "key --clearmodifiers shift+Page_Down",
    "windowactivate --sync 4242",
    "key --clearmodifiers ctrl+shift+Home",
], lines
PY

: > "$JARVIS_NAVIGATION_LOG"
if PATH="$tmp/bin:$PATH" JARVIS_TEST_WINDOW_CLASS="Cinnamon" \
   "$HELPER" page_down 2>/dev/null; then
  echo "Focused navigation accepted the Cinnamon desktop" >&2
  exit 1
fi
[[ ! -s "$JARVIS_NAVIGATION_LOG" ]]

: > "$JARVIS_NAVIGATION_LOG"
: > "$JARVIS_ACTIVE_WINDOW_STATE"
if PATH="$tmp/bin:$PATH" JARVIS_TEST_FOCUS_CHANGE=1 \
   "$HELPER" page_down 2>/dev/null; then
  echo "Focused navigation ignored an active-window change" >&2
  exit 1
fi
[[ ! -s "$JARVIS_NAVIGATION_LOG" ]]

echo "focused navigation regression test: PASS"
