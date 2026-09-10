#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bin_dir="$HOME/.local/bin"
icon_dir="$HOME/.local/share/icons/ovos-tray"
autostart_dir="$HOME/.config/autostart"
state_dir="$HOME/.local/state"

if ! python3 -c 'import gi; gi.require_version("Gtk", "3.0")' 2>/dev/null; then
    echo "Missing python3-gi / GTK 3 support." >&2
    echo "Install it with: sudo apt install python3-gi gir1.2-gtk-3.0" >&2
    exit 1
fi

mkdir -p "$bin_dir" "$icon_dir" "$autostart_dir" "$state_dir"
install -m 0755 "$repo_root/tray/ovos-tray.py" "$bin_dir/ovos-tray"
install -m 0644 "$repo_root/tray/"*.svg "$icon_dir/"

desktop_file="$autostart_dir/ovos-tray.desktop"
{
    printf '%s\n' '[Desktop Entry]'
    printf '%s\n' 'Type=Application'
    printf '%s\n' 'Name=Voice System Status'
    printf 'Exec=%s\n' "$bin_dir/ovos-tray"
    printf '%s\n' 'Terminal=false'
    printf '%s\n' 'X-GNOME-Autostart-enabled=true'
} > "$desktop_file"

pkill -f "$bin_dir/ovos-tray" 2>/dev/null || true
nohup "$bin_dir/ovos-tray" > "$state_dir/ovos-tray.log" 2>&1 &

echo "Voice-system tray installed and started."
