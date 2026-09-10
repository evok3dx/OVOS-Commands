#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="$repo_root/mic"
bin_dir="$HOME/.local/bin"
icon_dir="$HOME/.local/share/jarvis"
autostart_dir="$HOME/.config/autostart"
state_dir="$HOME/.local/state/jarvis-mic-indicator"
desktop_file="$autostart_dir/jarvis-mic-indicator.desktop"
stamp="$(date +%Y%m%d-%H%M%S)"
backup_dir="$state_dir/backups/$stamp"
desktop_tmp="$(mktemp)"

cleanup() {
    rm -f "$desktop_tmp"
}
trap cleanup EXIT

for command in systemctl notify-send; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Missing required command: $command" >&2
        exit 1
    fi
done

if ! python3 -c \
  'import gi; gi.require_version("Gtk", "3.0")' \
  2>/dev/null; then
    echo "Missing python3-gi / GTK 3 support." >&2
    echo "Install it with: sudo apt install python3-gi gir1.2-gtk-3.0" >&2
    exit 1
fi

python3 -m py_compile "$source_dir/jarvis-mic-indicator"
bash -n "$source_dir/jarvis-mic-toggle"

SOURCE_DIR="$source_dir" python3 <<'PY'
import os
from pathlib import Path
from xml.etree import ElementTree

source = Path(os.environ["SOURCE_DIR"])
for name in ("mic-active.svg", "mic-muted.svg"):
    ElementTree.parse(source / name)
print("PASS: microphone scripts and icons validate")
PY

mkdir -p \
  "$bin_dir" \
  "$icon_dir" \
  "$autostart_dir" \
  "$state_dir"

{
    printf '%s\n' '[Desktop Entry]'
    printf '%s\n' 'Type=Application'
    printf '%s\n' 'Name=Jarvis Microphone Indicator'
    printf '%s\n' 'Comment=Shows and controls the Jarvis microphone state'
    printf 'Exec=%s\n' "$bin_dir/jarvis-mic-indicator"
    printf '%s\n' 'Icon=audio-input-microphone'
    printf '%s\n' 'Terminal=false'
    printf '%s\n' 'X-GNOME-Autostart-enabled=true'
    printf '%s\n' 'X-GNOME-Autostart-Delay=3'
} > "$desktop_tmp"

backup_if_changed() {
    local source="$1"
    local target="$2"

    if [[ -f "$target" ]] && ! cmp -s "$source" "$target"; then
        mkdir -p "$backup_dir"
        cp -a "$target" "$backup_dir/$(basename "$target")"
    fi
}

backup_if_changed \
  "$source_dir/jarvis-mic-indicator" \
  "$bin_dir/jarvis-mic-indicator"
backup_if_changed \
  "$source_dir/jarvis-mic-toggle" \
  "$bin_dir/jarvis-mic-toggle"
backup_if_changed \
  "$source_dir/mic-active.svg" \
  "$icon_dir/mic-active.svg"
backup_if_changed \
  "$source_dir/mic-muted.svg" \
  "$icon_dir/mic-muted.svg"
backup_if_changed "$desktop_tmp" "$desktop_file"

install -m 0755 \
  "$source_dir/jarvis-mic-indicator" \
  "$bin_dir/jarvis-mic-indicator"
install -m 0755 \
  "$source_dir/jarvis-mic-toggle" \
  "$bin_dir/jarvis-mic-toggle"
install -m 0644 \
  "$source_dir/mic-active.svg" \
  "$icon_dir/mic-active.svg"
install -m 0644 \
  "$source_dir/mic-muted.svg" \
  "$icon_dir/mic-muted.svg"
install -m 0644 "$desktop_tmp" "$desktop_file"

pkill -f "$bin_dir/jarvis-mic-indicator" 2>/dev/null || true
nohup "$bin_dir/jarvis-mic-indicator" \
  > "$state_dir/indicator.log" 2>&1 &

echo "Jarvis microphone indicator installed and started."
if [[ -d "$backup_dir" ]]; then
    echo "Changed-file backups: $backup_dir"
fi
