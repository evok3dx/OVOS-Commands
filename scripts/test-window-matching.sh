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
    if [[ -z "${JARVIS_WINDOW_STATE:-}" || -e "$JARVIS_WINDOW_STATE" ]]; then
      printf '%s\n' "${JARVIS_WINDOW_LINE:-0x05c00004  0 standard-notes.Standard-notes testhost Standard Notes}"
    fi
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

# ONLYOFFICE uses its real desktop entry through the reviewed GIO launcher.
# The helper then waits for one of the fixed native/Flatpak window classes.
office_home="$tmp/home"
office_state="$tmp/office-window.state"
office_log="$tmp/office-launch.log"
mkdir -p "$office_home/.local/bin"
cat > "$office_home/.local/bin/jarvis-desktop-launch" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "$JARVIS_LAUNCH_LOG"
touch "$JARVIS_WINDOW_STATE"
EOF
chmod +x "$office_home/.local/bin/jarvis-desktop-launch"
HOME="$office_home" PATH="$tmp/bin:$PATH" \
  JARVIS_WINDOW_STATE="$office_state" \
  JARVIS_WINDOW_LINE='0x05c00004  0 org.onlyoffice.desktopeditors host ONLYOFFICE Desktop Editors' \
  JARVIS_LAUNCH_LOG="$office_log" \
  "$HELPER" open onlyoffice
grep -Fxq 'office' "$office_log"

echo "window matching regression test: PASS"
