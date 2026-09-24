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
printf '%s %s\n' "$1" "$(sed -n 's/^speech_speed2=//p' "$MOCK_SETTINGS")" >> "$MOCK_LOG"
if [[ "$1" == run && "${MOCK_FAIL:-0}" == 1 ]]; then exit 7; fi
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
grep -Fxq 'run 20' "$MOCK_LOG"
grep -Fxq 'speech_speed2=13' "$settings"
for attempt in {1..50}; do
  [[ ! -e "$HOME/.local/state/jarvis/reading-fast-active" ]] && break
  /usr/bin/sleep 0.01
done
[[ ! -e "$HOME/.local/state/jarvis/reading-fast-active" ]]

if MOCK_FAIL=1 bash "$repo_root/system_helpers/jarvis-read-visible-text" selection 2; then
  echo 'Failed Speech Note launch was reported as success' >&2
  exit 1
fi
grep -Fxq 'speech_speed2=13' "$settings"
[[ ! -e "$HOME/.local/state/jarvis/reading-fast-active" ]]

rm -- "$settings"
: > "$MOCK_LOG"
if bash "$repo_root/system_helpers/jarvis-read-visible-text" selection 2 >/dev/null 2>&1; then
  echo 'Speed change unexpectedly accepted missing Speech Note settings' >&2
  exit 1
fi
[[ ! -s "$MOCK_LOG" ]]

bash "$repo_root/system_helpers/jarvis-read-visible-text" selection 1
grep -q '^run ' "$MOCK_LOG"
echo 'PASS: Speech Note 2x applies temporarily, restores speed and fails safely'
