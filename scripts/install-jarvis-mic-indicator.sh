#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
jarvis_home="${JARVIS_HOME:-$HOME}"
source_dir="$repo_root/mic"
bin_dir="$jarvis_home/.local/bin"
icon_dir="$jarvis_home/.local/share/jarvis"
autostart_dir="$jarvis_home/.config/autostart"
state_dir="$jarvis_home/.local/state/jarvis-ui"
desktop_file="$autostart_dir/jarvis-mic-indicator.desktop"
desktop_python="${JARVIS_DESKTOP_PYTHON:-/usr/bin/python3}"

if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]]; then
  for command in systemctl notify-send; do
    command -v "$command" >/dev/null 2>&1 || {
      echo "Missing required command: $command" >&2
      exit 1
    }
  done
  if ! "$desktop_python" -c 'import gi; gi.require_version("Gtk", "3.0")' 2>/dev/null; then
    echo "Missing python3-gi / GTK 3 support." >&2
    echo "Install: sudo apt install python3-gi gir1.2-gtk-3.0" >&2
    exit 1
  fi
fi

"$desktop_python" -m py_compile "$source_dir/jarvis-mic-indicator"
bash -n "$source_dir/jarvis-mic-toggle"

SOURCE_DIR="$source_dir" "$desktop_python" <<'PY'
import os
from pathlib import Path
from xml.etree import ElementTree

source = Path(os.environ["SOURCE_DIR"])
for name in ("mic-active.svg", "mic-muted.svg"):
    ElementTree.parse(source / name)
PY

mkdir -p "$bin_dir" "$icon_dir" "$autostart_dir" "$state_dir"
install -m 0755 "$source_dir/jarvis-mic-indicator" "$bin_dir/jarvis-mic-indicator"
install -m 0755 "$source_dir/jarvis-mic-toggle" "$bin_dir/jarvis-mic-toggle"
install -m 0644 "$source_dir/mic-active.svg" "$icon_dir/mic-active.svg"
install -m 0644 "$source_dir/mic-muted.svg" "$icon_dir/mic-muted.svg"

desktop_tmp="$(mktemp)"
trap 'rm -f "$desktop_tmp"' EXIT
cat > "$desktop_tmp" <<EOF
[Desktop Entry]
Type=Application
Name=Jarvis Microphone Indicator
Comment=Shows and controls the Jarvis microphone state
Exec=$bin_dir/jarvis-mic-indicator
Icon=audio-input-microphone
Terminal=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=3
EOF
install -m 0644 "$desktop_tmp" "$desktop_file"

if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]]; then
  pkill -f "$bin_dir/jarvis-mic-indicator" 2>/dev/null || true
  nohup "$bin_dir/jarvis-mic-indicator" \
    > "$state_dir/jarvis-mic-indicator.log" 2>&1 &
fi

echo "Jarvis microphone indicator installed."
