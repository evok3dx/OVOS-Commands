#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
jarvis_home="${JARVIS_HOME:-$HOME}"
bin_dir="$jarvis_home/.local/bin"
icon_dir="$jarvis_home/.local/share/icons/ovos-tray"
autostart_dir="$jarvis_home/.config/autostart"
state_dir="$jarvis_home/.local/state/jarvis-ui"
desktop_file="$autostart_dir/ovos-tray.desktop"

if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]] &&
   ! python3 -c 'import gi; gi.require_version("Gtk", "3.0")' 2>/dev/null; then
  echo "Missing python3-gi / GTK 3 support." >&2
  echo "Install: sudo apt install python3-gi gir1.2-gtk-3.0" >&2
  exit 1
fi

python3 -m py_compile "$repo_root/tray/ovos-tray.py"
mkdir -p "$bin_dir" "$icon_dir" "$autostart_dir" "$state_dir"
install -m 0755 "$repo_root/tray/ovos-tray.py" "$bin_dir/ovos-tray"
install -m 0644 "$repo_root/tray/"*.svg "$icon_dir/"

desktop_tmp="$(mktemp)"
trap 'rm -f "$desktop_tmp"' EXIT
cat > "$desktop_tmp" <<EOF
[Desktop Entry]
Type=Application
Name=Voice System Status
Exec=$bin_dir/ovos-tray
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
install -m 0644 "$desktop_tmp" "$desktop_file"

if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]]; then
  pkill -f "$bin_dir/ovos-tray" 2>/dev/null || true
  nohup "$bin_dir/ovos-tray" > "$state_dir/ovos-tray.log" 2>&1 &
fi

echo "Voice-system tray installed."
