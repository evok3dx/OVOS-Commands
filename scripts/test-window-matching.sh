#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HELPER="$ROOT/system_helpers/jarvis-app-window"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin"

# Deliberately expose only the *second* reviewed Standard Notes-style
# alternative. A broken single-literal matcher would fail this test.
cat > "$tmp/bin/wmctrl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  -lx)
    printf '%s\n' '0x05c00004  0 standard-notes.Standard-notes testhost Standard Notes'
    ;;
  -ir|-ia)
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
EOF

cat > "$tmp/bin/xdotool" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "getactivewindow" ]]; then
  # 0x05c00004 in decimal.
  printf '%s\n' '96468996'
  exit 0
fi
if [[ "${1:-}" == "windowactivate" ]]; then
  exit 0
fi
if [[ "${1:-}" == "windowminimize" ]]; then
  exit 0
fi
exit 0
EOF

chmod +x "$tmp/bin/wmctrl" "$tmp/bin/xdotool"

PATH="$tmp/bin:$PATH" "$HELPER" focus standard_notes

echo "window matching regression test: PASS"
