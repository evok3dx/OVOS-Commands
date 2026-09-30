#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
jarvis_home="${JARVIS_HOME:-$HOME}"
target_root="$jarvis_home/.local/src/ovos-skill-jarvis-dispatcher"
target_bin="$jarvis_home/.local/bin"
config_root="$jarvis_home/.config/jarvis"
state_root="$jarvis_home/.local/state/jarvis"
systemd_root="$jarvis_home/.config/systemd/user"
ovos_python="${OVOS_PYTHON:-$jarvis_home/.venvs/ovos/bin/python}"
yes=false
remove_model=false
remove_settings=false
remove_ovos=false

usage() {
  cat <<'EOF'
Usage: jarvis-uninstall [OPTIONS]

Remove the Jarvis commands, plugins, tray, launchers and managed user services.
Speech Note and other desktop applications are never removed.

Options:
  --yes              Confirm the uninstall
  --remove-model     Also remove qwen3:4b-instruct-2507-q4_K_M from Ollama
  --remove-settings  Also remove Jarvis settings, custom commands and history
  --remove-ovos      Also remove ~/.venvs/ovos and per-user OVOS configuration
  -h, --help         Show this help
EOF
}

while (($#)); do
  case "$1" in
    --yes) yes=true ;;
    --remove-model) remove_model=true ;;
    --remove-settings) remove_settings=true ;;
    --remove-ovos) remove_ovos=true ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
  shift
done

python3 "$repo_root/scripts/isolation_services.py" --guard-uninstall "$jarvis_home"

if ! "$yes"; then
  if [[ ! -t 0 || ! -t 1 ]]; then
    echo "Refusing a non-interactive uninstall without --yes." >&2
    exit 2
  fi
  read -r -p "Remove Jarvis from this user account? [y/N] " answer
  [[ "${answer,,}" == y || "${answer,,}" == yes ]] || exit 0
fi

mapfile -t helpers < <(python3 - "$repo_root/deployment-manifest.json" <<'PY'
import json,sys
from pathlib import Path
for name in json.loads(Path(sys.argv[1]).read_text())["runtime_helpers"]:
    print(name)
PY
)

units=(hermes-launcher-repair.path jarvis-health-check.timer jarvis-update-check.timer)
unit_files=(
  hermes-launcher-repair.service hermes-launcher-repair.path
  jarvis-health-check.service jarvis-health-check.timer
  jarvis-update-check.service jarvis-update-check.timer
)

if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]]; then
  systemctl --user stop ovos.service ovos-core.service ovos-listener.service \
    ovos-audio.service >/dev/null 2>&1 || true
  systemctl --user disable --now "${units[@]}" >/dev/null 2>&1 || true
  if [[ -f "$repo_root/extras/whisper-hints/install.py" && \
        -f "$state_root/whisper-app-hints/latest.json" ]]; then
    python3 "$repo_root/extras/whisper-hints/install.py" --rollback >/dev/null 2>&1 || true
  fi
  pkill -f "$target_bin/ovos-tray" 2>/dev/null || true
  if [[ -x "$ovos_python" ]]; then
    env -u PIP_CONSTRAINT "$ovos_python" -m pip uninstall --yes \
      ovos-skill-jarvis-dispatcher ovos-skill-jarvis-media \
      jarvis-file-search-skill >/dev/null 2>&1 || true
  fi
  # Restore the oldest pre-Jarvis Cinnamon shortcut snapshot when available.
  first_snapshot="$(find "$state_root/backups" -mindepth 2 -maxdepth 2 \
      -name cinnamon-shortcuts.json -type f -print 2>/dev/null | sort | head -n 1)"
  if [[ -n "$first_snapshot" && -x "$target_bin/jarvis-listen-shortcut" ]]; then
    python3 "$target_bin/jarvis-listen-shortcut" \
      --restore-snapshot "$first_snapshot" >/dev/null 2>&1 || true
  fi
fi

for helper in "${helpers[@]}"; do
  rm -f -- "$target_bin/$helper"
done
rm -f -- "$target_bin/ovos-tray" "$target_bin/jarvis-mic-indicator" \
  "$target_bin/jarvis-mic-toggle"
rm -f -- "$jarvis_home/.config/autostart/ovos-tray.desktop" \
  "$jarvis_home/.config/autostart/jarvis-voice.desktop" \
  "$jarvis_home/.config/autostart/jarvis-mic-indicator.desktop" \
  "$jarvis_home/.local/share/applications/jarvis-ovos.desktop"
for unit in "${unit_files[@]}"; do
  rm -f -- "$systemd_root/$unit"
done
rm -rf -- "$jarvis_home/.local/share/icons/ovos-tray"

if "$remove_model" && command -v ollama >/dev/null 2>&1; then
  ollama rm qwen3:4b-instruct-2507-q4_K_M >/dev/null 2>&1 || true
fi

if "$remove_settings"; then
  rm -rf -- "$config_root" "$state_root" "$jarvis_home/.local/state/jarvis-ui"
fi

if "$remove_ovos"; then
  [[ "$ovos_python" == "$jarvis_home/.venvs/ovos/bin/python" ]] || {
    echo "Refusing to remove a non-standard OVOS environment: $ovos_python" >&2
    exit 1
  }
  if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]]; then
    systemctl --user disable --now ovos.service >/dev/null 2>&1 || true
  fi
  rm -rf -- "$jarvis_home/.venvs/ovos"
  rm -f -- "$jarvis_home/.config/mycroft/mycroft.conf" \
    "$jarvis_home/.config/ovos/ovos.conf" "$jarvis_home/.config/ovos/mycroft.conf"
fi

rm -rf -- "$target_root"
if [[ "${JARVIS_TEST_MODE:-0}" != 1 ]]; then
  systemctl --user daemon-reload >/dev/null 2>&1 || true
fi
printf '%s\n' 'Jarvis was removed. Speech Note and other desktop applications were left untouched.'
