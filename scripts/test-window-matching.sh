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
  -l|-lx)
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

cat > "$tmp/bin/xprop" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "${JARVIS_WM_CLASS:-WM_CLASS(STRING) = \"standard-notes\", \"Standard-notes\"}"
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

chmod +x "$tmp/bin/wmctrl" "$tmp/bin/xdotool" "$tmp/bin/xprop"

HOME="$tmp/home" PATH="$tmp/bin:$PATH" "$HELPER" focus standard_notes

# Real Debian, hyphenated/AppImage and Flatpak signatures use the full property.
for signature in \
  'WM_CLASS(STRING) = "standard notes", "Standard Notes"' \
  'WM_CLASS(STRING) = "standard-notes", "Standard-notes"' \
  'WM_CLASS(STRING) = "standardnotes", "StandardNotes"' \
  'WM_CLASS(STRING) = "org.standardnotes.standardnotes", "org.standardnotes.standardnotes"'; do
  HOME="$tmp/home" PATH="$tmp/bin:$PATH" JARVIS_WM_CLASS="$signature" \
    "$HELPER" focus standard_notes
done
for signature in \
  'WM_CLASS(STRING) = "brave-browser", "Brave-browser"' \
  'WM_CLASS(STRING) = "standard", "SomethingElse"' \
  'WM_CLASS(STRING) = "fake-standard-notes", "NotNotes"'; do
  if HOME="$tmp/home" PATH="$tmp/bin:$PATH" JARVIS_WM_CLASS="$signature" \
    "$HELPER" minimize standard_notes 2>/dev/null; then
    echo 'An unrelated class was mistaken for Standard Notes' >&2; exit 1
  fi
done

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
  JARVIS_WM_CLASS='WM_CLASS(STRING) = "org.onlyoffice.desktopeditors", "org.onlyoffice.desktopeditors"' \
  JARVIS_LAUNCH_LOG="$office_log" \
  "$HELPER" open onlyoffice
grep -Fxq 'office' "$office_log"

# Application words in a browser title cannot identify a Zoom window.
if HOME="$office_home" PATH="$tmp/bin:$PATH" \
  JARVIS_WINDOW_LINE='0x05c00004 0 brave-browser.Brave-browser host Zoom.Zoom meeting' \
  JARVIS_WM_CLASS='WM_CLASS(STRING) = "brave-browser", "Brave-browser"' \
  "$HELPER" minimize zoom 2>/dev/null; then
  echo 'Window title was mistaken for WM_CLASS' >&2
  exit 1
fi

# Proton Mail's spaced property must be recognised immediately. No launch
# command may run when its window already exists.
for action in open focus minimize maximize close; do
  HOME="$tmp/home" PATH="$tmp/bin:$PATH" \
    JARVIS_WINDOW_LINE='0x05c00004 0 fixture-host Inbox' \
    JARVIS_WM_CLASS='WM_CLASS(STRING) = "proton mail", "Proton Mail"' \
    "$HELPER" "$action" proton_mail
done

# Exact identities survive packaging variants; title/class substrings do not.
for signature in \
  'WM_CLASS(STRING) = "brave-browser", "Brave-browser"' \
  'WM_CLASS(STRING) = "fake-proton mail", "Proton Mail Fake"' \
  'WM_CLASS(STRING) = "proton mail", "Unrelated"' \
  'WM_CLASS:  not found.'; do
  if HOME="$tmp/home" PATH="$tmp/bin:$PATH" \
    JARVIS_WINDOW_LINE='0x05c00004 0 fixture-host Proton Mail' \
    JARVIS_WM_CLASS="$signature" "$HELPER" minimize proton_mail 2>/dev/null; then
    echo 'An unrelated or malformed class was mistaken for Proton Mail' >&2
    exit 1
  fi
done

for entry in \
  'onlyoffice|WM_CLASS(STRING) = "DesktopEditors", "ONLYOFFICE"' \
  'firefox|WM_CLASS(STRING) = "Navigator", "firefox"' \
  'settings|WM_CLASS(STRING) = "cinnamon-settings.py", "Cinnamon-settings.py"'; do
  HOME="$tmp/home" PATH="$tmp/bin:$PATH" JARVIS_WM_CLASS="${entry#*|}" \
    "$HELPER" focus "${entry%%|*}"
done

echo "window matching regression test: PASS"
