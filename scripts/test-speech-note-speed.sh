#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_root="$(mktemp -d)"
trap 'rm -rf -- "$test_root"' EXIT
mkdir -p "$test_root/home/.var/app/net.mkiol.SpeechNote/config/net.mkiol/dsnote" \
  "$test_root/mock-bin"
settings="$test_root/home/.var/app/net.mkiol.SpeechNote/config/net.mkiol/dsnote/settings.conf"
printf '[General]\nspeech_speed2=13\n' > "$settings"

cat > "$test_root/mock-bin/xclip" <<'EOF'
#!/usr/bin/env bash
if [[ " $* " == *' -i '* ]]; then cat >/dev/null; else printf 'Selected text\n'; fi
EOF
cat > "$test_root/mock-bin/flatpak" <<'EOF'
#!/usr/bin/env bash
printf '%s %s\n' "$*" "$(sed -n 's/^speech_speed2=//p' "$MOCK_SETTINGS")" >> "$MOCK_LOG"
if [[ "$1" == run && "${MOCK_FAIL:-0}" == 1 ]]; then exit 7; fi
if [[ "$1" == run && "${MOCK_STALL:-0}" == 1 ]]; then /bin/sleep 5; fi
EOF
cat > "$test_root/mock-bin/gdbus" <<'EOF'
#!/usr/bin/env bash
if [[ -f "$MOCK_STATE" ]]; then echo '(<0>,)'; else touch "$MOCK_STATE"; echo '(<4>,)'; fi
EOF
cat > "$test_root/mock-bin/sleep" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$test_root/mock-bin/"*

export HOME="$test_root/home" PATH="$test_root/mock-bin:$PATH"
export MOCK_SETTINGS="$settings" MOCK_LOG="$test_root/flatpak.log" \
  MOCK_STATE="$test_root/saw-playing"
bash "$repo_root/system_helpers/jarvis-read-visible-text" selection 2
grep -Fxq 'run net.mkiol.SpeechNote --action start-reading-clipboard 20' "$MOCK_LOG"
grep -Fxq 'speech_speed2=13' "$settings"
grep -Fxq '13' "$HOME/.config/jarvis/reading-normal-speed"
for attempt in {1..300}; do
  [[ ! -e "$HOME/.local/state/jarvis/reading-fast-active" ]] && break
  /usr/bin/sleep 0.01
done
[[ ! -e "$HOME/.local/state/jarvis/reading-fast-active" ]]
grep -Fxq 'run net.mkiol.SpeechNote --start-in-tray 13' "$MOCK_LOG"

# A request that never confirms playback is stopped before the helper reports
# failure. It cannot start late with the temporary 2x value still in memory.
: > "$MOCK_LOG"
rm -f -- "$MOCK_STATE"
if MOCK_STALL=1 bash "$repo_root/system_helpers/jarvis-read-visible-text" selection 2; then
  echo 'Unconfirmed delayed Speech Note launch was reported as success' >&2
  exit 1
fi
grep -Fxq 'kill net.mkiol.SpeechNote 13' "$MOCK_LOG"
grep -Fxq 'speech_speed2=13' "$settings"
[[ ! -e "$HOME/.local/state/jarvis/reading-fast-active" ]]

if MOCK_FAIL=1 bash "$repo_root/system_helpers/jarvis-read-visible-text" selection 2; then
  echo 'Failed Speech Note launch was reported as success' >&2
  exit 1
fi
grep -Fxq 'speech_speed2=13' "$settings"
[[ ! -e "$HOME/.local/state/jarvis/reading-fast-active" ]]

# Ordinary reading preserves a valid speed selected manually in Speech Note.
printf '[General]\nspeech_speed2=15\n' > "$settings"
rm -f -- "$HOME/.config/jarvis/reading-normal-speed" "$MOCK_STATE"
: > "$MOCK_LOG"
bash "$repo_root/system_helpers/jarvis-read-visible-text" selection 1
grep -Fxq '15' "$HOME/.config/jarvis/reading-normal-speed"
grep -Fxq 'speech_speed2=15' "$settings"
grep -Fxq 'run net.mkiol.SpeechNote --action start-reading-clipboard 15' "$MOCK_LOG"

# A normal request clears a stale transaction and restores its exact saved
# speed before launching. The v2 marker also records whether Speech Note was
# resident before Jarvis temporarily changed its speed.
printf '[General]\nspeech_speed2=20\n' > "$settings"
printf '13\n' > "$HOME/.config/jarvis/reading-normal-speed"
mkdir -p "$HOME/.local/state/jarvis"
printf 'v2 abandoned 13 1\n' > "$HOME/.local/state/jarvis/reading-fast-active"
rm -f -- "$MOCK_STATE"
: > "$MOCK_LOG"
bash "$repo_root/system_helpers/jarvis-read-visible-text" selection 1
grep -Fxq 'speech_speed2=13' "$settings"
[[ ! -e "$HOME/.local/state/jarvis/reading-fast-active" ]]
grep -Fxq 'run net.mkiol.SpeechNote --action start-reading-clipboard 13' "$MOCK_LOG"

# A manually selected 2x default is also a valid preference when no temporary
# Jarvis transaction marker exists; ordinary reading must not reset it.
printf '[General]\nspeech_speed2=20\n' > "$settings"
rm -f -- "$HOME/.local/state/jarvis/reading-fast-active" "$MOCK_STATE"
: > "$MOCK_LOG"
bash "$repo_root/system_helpers/jarvis-read-visible-text" selection 1
grep -Fxq '20' "$HOME/.config/jarvis/reading-normal-speed"
grep -Fxq 'speech_speed2=20' "$settings"
grep -Fxq 'run net.mkiol.SpeechNote --action start-reading-clipboard 20' "$MOCK_LOG"

rm -- "$settings"
: > "$MOCK_LOG"
if bash "$repo_root/system_helpers/jarvis-read-visible-text" selection 2 >/dev/null 2>&1; then
  echo 'Speed change unexpectedly accepted missing Speech Note settings' >&2
  exit 1
fi
[[ ! -s "$MOCK_LOG" ]]

bash "$repo_root/system_helpers/jarvis-read-visible-text" selection 1
grep -q '^run ' "$MOCK_LOG"
echo 'PASS: Speech Note preserves manual defaults and restores temporary 2x safely'
