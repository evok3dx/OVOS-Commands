#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_root="$(mktemp -d)"
trap 'rm -rf -- "$test_root"' EXIT
trap 'printf "Speech Note fixture failed at line %s\n" "$LINENO" >&2' ERR
mkdir -p "$test_root/home/.var/app/net.mkiol.SpeechNote/config/net.mkiol/dsnote" \
  "$test_root/mock-bin"
settings="$test_root/home/.var/app/net.mkiol.SpeechNote/config/net.mkiol/dsnote/settings.conf"
printf '[General]\nspeech_speed2=13\n' > "$settings"

cat > "$test_root/mock-bin/xclip" <<'EOF'
#!/usr/bin/env bash
if [[ " $* " == *' -silent '* && " $* " == *' -i '* ]]; then
  cat >/dev/null
  printf 'clipboard-owner-start\n' >> "$MOCK_SEQUENCE"
  touch "$MOCK_STATE.owner"
  trap 'rm -f "$MOCK_STATE.owner"; printf "clipboard-owner-stop\n" >> "$MOCK_SEQUENCE"; exit 0' TERM
  while true; do /usr/bin/sleep 0.02; done
elif [[ " $* " == *' -i '* ]]; then
  cat >/dev/null
  rm -f "$MOCK_STATE.owner" "$MOCK_STATE.copy"
  printf 'clipboard-clear\n' >> "$MOCK_SEQUENCE"
else
  [[ -e "$MOCK_STATE.copy" || -e "$MOCK_STATE.owner" ]] || exit 1
  rm -f "$MOCK_STATE.copy"
  printf 'Selected text\n'
fi
EOF
cat > "$test_root/mock-bin/xdotool" <<'EOF'
#!/usr/bin/env bash
if [[ "$1" == getactivewindow ]]; then printf '123\n'; fi
if [[ "$*" == *'ctrl+c'* ]]; then touch "$MOCK_STATE.copy"; fi
EOF
cat > "$test_root/mock-bin/xprop" <<'EOF'
#!/usr/bin/env bash
printf 'WM_CLASS(STRING) = "DesktopEditors", "ONLYOFFICE"\n'
EOF
cat > "$test_root/mock-bin/flatpak" <<'EOF'
#!/usr/bin/env bash
printf '%s %s\n' "$*" "$(sed -n 's/^speech_speed2=//p' "$MOCK_SETTINGS")" >> "$MOCK_LOG"
if [[ "$*" == *'start-reading-clipboard'* ]]; then
  printf 'reader-request\n' >> "$MOCK_SEQUENCE"
fi
if [[ "$1" == run && "${MOCK_FAIL:-0}" == 1 ]]; then exit 7; fi
if [[ "$1" == run && "${MOCK_STALL:-0}" == 1 ]]; then /bin/sleep 5; fi
EOF
cat > "$test_root/mock-bin/gdbus" <<'EOF'
#!/usr/bin/env bash
if [[ "${MOCK_MONITOR_HOLD:-0}" == 1 ]]; then
  echo '(<4>,)'
  exit 0
fi
if [[ "${MOCK_GDBUS_ZERO:-0}" == 1 ]]; then echo '(<0>,)'; exit 0; fi
# Playback cannot begin before the mocked reader received this request. The
# old unconditional playing state raced the asynchronous launch on CI.
if ! grep -Fxq 'reader-request' "$MOCK_SEQUENCE" 2>/dev/null; then
  echo '(<0>,)'
  exit 0
fi
count="$(cat "$MOCK_STATE" 2>/dev/null || printf '0')"
count=$((count + 1))
printf '%s\n' "$count" > "$MOCK_STATE"
if (( count <= 2 )); then echo '(<4>,)'; else echo '(<0>,)'; fi
EOF
cat > "$test_root/mock-bin/sleep" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == 1 ]]; then
  /usr/bin/sleep 0.05
  printf 'handoff-delay\n' >> "$MOCK_SEQUENCE"
fi
if [[ "${MOCK_MONITOR_HOLD:-0}" == 1 ]]; then /usr/bin/sleep 0.02; fi
exit 0
EOF
chmod +x "$test_root/mock-bin/"*

export HOME="$test_root/home" PATH="$test_root/mock-bin:$PATH"
export MOCK_SETTINGS="$settings" MOCK_LOG="$test_root/flatpak.log" \
  MOCK_STATE="$test_root/saw-playing" MOCK_SEQUENCE="$test_root/sequence.log"
bash "$repo_root/system_helpers/jarvis-read-visible-text" selection 2
grep -Fxq 'run net.mkiol.SpeechNote --action start-reading-clipboard 20' "$MOCK_LOG"
for attempt in {1..100}; do
  grep -Fxq 'reader-request' "$MOCK_SEQUENCE" 2>/dev/null && break
  /usr/bin/sleep 0.01
done
python3 - "$MOCK_SEQUENCE" <<'PY'
import sys
from pathlib import Path

events = Path(sys.argv[1]).read_text().splitlines()
assert "reader-request" in events, events
start = events.index("clipboard-owner-start")
request = events.index("reader-request", start)
delay = events.index("handoff-delay", request)
stop = events.index("clipboard-owner-stop", delay)
assert start < request < delay < stop, events
assert events[-1] == "clipboard-clear", events
PY
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
if MOCK_STALL=1 MOCK_GDBUS_ZERO=1 \
   bash "$repo_root/system_helpers/jarvis-read-visible-text" selection 2; then
  echo 'Unconfirmed delayed Speech Note launch was reported as success' >&2
  exit 1
fi
grep -Fxq 'kill net.mkiol.SpeechNote 13' "$MOCK_LOG"
grep -Fxq 'speech_speed2=13' "$settings"
[[ ! -e "$HOME/.local/state/jarvis/reading-fast-active" ]]

if MOCK_FAIL=1 MOCK_GDBUS_ZERO=1 \
   bash "$repo_root/system_helpers/jarvis-read-visible-text" selection 2; then
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

# The temporary-2x completion monitor may remain alive for the whole passage,
# but it must not inherit the setup transaction lock. Run this isolation check
# last so its intentionally long-lived mock cannot affect other cases.
printf '[General]\nspeech_speed2=13\n' > "$settings"
rm -f -- "$MOCK_STATE" "$HOME/.local/state/jarvis/reading-fast-active"
: > "$MOCK_LOG"
MOCK_MONITOR_HOLD=1 bash \
  "$repo_root/system_helpers/jarvis-read-visible-text" selection 2
if ! flock -n "$HOME/.local/state/jarvis/reading-speed.lock" -c true; then
  echo 'Completed reading setup left its transaction lock held' >&2
  exit 1
fi
# The temporary clipboard owner must not inherit the same lock either.
if ! flock -n "$HOME/.local/state/jarvis/reading-speed.lock" -c true; then
  echo 'Clipboard ownership left the reading transaction lock held' >&2
  exit 1
fi
rm -f -- "$HOME/.local/state/jarvis/reading-fast-active"
/usr/bin/sleep 0.2

echo 'PASS: Speech Note preserves manual defaults and restores temporary 2x safely'
