#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_root="$(mktemp -d "${TMPDIR:-/tmp}/jarvis-deployment-test.XXXXXX")"

cleanup() {
  case "$test_root" in
    "${TMPDIR:-/tmp}"/jarvis-deployment-test.*)
      rm -rf -- "$test_root"
      ;;
  esac
}
trap cleanup EXIT

manifest_list() {
  python3 - "$repo_root/deployment-manifest.json" "$1" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(*data[sys.argv[2]], sep="\n")
PY
}

mapfile -t helpers < <(manifest_list runtime_helpers)

# A check-only run on a fresh home must not create a deployment.
fresh_home="$test_root/fresh"
mkdir -p "$fresh_home"
JARVIS_HOME="$fresh_home" JARVIS_TEST_MODE=1 \
  bash "$repo_root/scripts/install.sh" --check
test ! -e "$fresh_home/.local/src/ovos-skill-jarvis-dispatcher"

# Fresh installation creates a complete, self-contained source deployment.
JARVIS_HOME="$fresh_home" JARVIS_TEST_MODE=1 \
  bash "$repo_root/scripts/install.sh" --mode all --no-restart

fresh_target="$fresh_home/.local/src/ovos-skill-jarvis-dispatcher"
test -f "$fresh_target/pyproject.toml"
test -f "$fresh_target/compatibility.json"
test ! -e "$fresh_home/.config/jarvis/profile.json"
python3 - "$fresh_home/.config/jarvis/capabilities.json" <<'PY'
import json
import stat
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
assert data["mode"] == "all-detected"
assert data["applications"] == {
    "brave": "brave", "firefox": "firefox", "terminal": "terminal"
}
assert data["private_extensions"] == {"agents": False}
assert stat.S_IMODE(path.stat().st_mode) == 0o600
PY

# Setup supports one-step core mode and a reviewed custom selection.
JARVIS_HOME="$fresh_home" JARVIS_TEST_MODE=1 \
  python3 "$fresh_target/scripts/setup.py" --mode core \
  --output "$test_root/core.json" --no-restart
JARVIS_HOME="$fresh_home" JARVIS_TEST_MODE=1 \
  python3 "$fresh_target/scripts/setup.py" --mode custom --apps firefox \
  --output "$test_root/custom.json" --no-restart
python3 - "$test_root/core.json" "$test_root/custom.json" <<'PY'
import json
import sys
from pathlib import Path

core = json.loads(Path(sys.argv[1]).read_text())
custom = json.loads(Path(sys.argv[2]).read_text())
assert core["applications"] == {}
assert custom["applications"] == {"firefox": "firefox"}
PY

# Normal setup cannot enable private agents, while an existing named Brain
# profile retains its already-customised extension during migration only.
JARVIS_HOME="$fresh_home" JARVIS_TEST_MODE=1 \
  python3 "$fresh_target/scripts/setup.py" \
  --migrate-profile "$repo_root/profiles/brain.json" \
  --output "$test_root/migrated-brain.json" --no-restart
python3 - "$test_root/migrated-brain.json" <<'PY'
import json
import sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
assert data["private_extensions"] == {"agents": True}
PY

# A disabled/private-window periodic check is read-only and exits quietly.
printf '%s\n' '{"repository": null}' > "$fresh_home/.config/jarvis/update.json"
JARVIS_HOME="$fresh_home" python3 "$fresh_target/scripts/update.py" check --quiet
for helper in "${helpers[@]}"; do
  cmp "$repo_root/system_helpers/$helper" "$fresh_home/.local/bin/$helper"
done
for unit in \
  hermes-launcher-repair.service \
  hermes-launcher-repair.path \
  jarvis-health-check.service \
  jarvis-health-check.timer \
  jarvis-update-check.service \
  jarvis-update-check.timer; do
  test -f "$fresh_home/.config/systemd/user/$unit"
done
grep -q '^OnCalendar=monthly$' \
  "$fresh_home/.config/systemd/user/jarvis-update-check.timer"
! grep -q '^OnUnitActiveSec=' \
  "$fresh_home/.config/systemd/user/jarvis-update-check.timer"
for state in ready starting stopped failed; do
  test -f "$fresh_home/.local/share/icons/ovos-tray/ovos-$state-update.svg"
done
HOME="$fresh_home" python3 - "$fresh_target/tray/ovos-tray.py" <<'PY'
import importlib.util
import json
import sys
import types
from pathlib import Path

gi = types.ModuleType("gi")
gi.require_version = lambda *_args: None
repository = types.ModuleType("gi.repository")
repository.GLib = object()
repository.Gtk = object()
sys.modules["gi"] = gi
sys.modules["gi.repository"] = repository

spec = importlib.util.spec_from_file_location("ovos_tray", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
tray = module.OvosTray.__new__(module.OvosTray)
status = Path.home() / ".local/state/jarvis/updates/latest.json"
status.parent.mkdir(parents=True, exist_ok=True)
status.write_text(json.dumps({
    "installed": "2.2.0", "latest": "2.3.0", "update_available": True,
}), encoding="utf-8")
assert tray._available_update() == "2.3.0"
commands = []
tray._terminal_command = commands.append
tray.update_release = "2.3.0"
tray._updates()
assert commands == ["jarvis-update install"]
status.write_text(json.dumps({
    "installed": "2.1.0", "latest": "2.2.0", "update_available": True,
}), encoding="utf-8")
assert tray._available_update() is None
commands.clear()
tray.update_release = None
tray._updates()
assert commands == ["jarvis-update check"]
PY

# The AI bundle is bounded, self-describing and redacts supplied secret shapes.
report="$test_root/ai-report.tar.gz"
JARVIS_HOME="$fresh_home" JARVIS_REPOSITORY="$fresh_target" JARVIS_TEST_MODE=1 \
  "$fresh_home/.local/bin/jarvis-report" \
  --issue 'Contact person@example.com with api_key=DO-NOT-SHARE' \
  --output "$report"
test "$(stat -c '%a' "$report")" = 600
report_dir="$test_root/report"
mkdir -p "$report_dir"
tar -xzf "$report" -C "$report_dir"
bundle="$(find "$report_dir" -mindepth 1 -maxdepth 1 -type d -name 'jarvis-ai-report-*' -print -quit)"
test -n "$bundle"
grep -q '<redacted-email>' "$bundle/ISSUE.md"
grep -q 'api_key=<redacted>' "$bundle/ISSUE.md"
! grep -R -q 'DO-NOT-SHARE\|person@example.com' "$bundle"
! grep -R -q '/workspace/' "$bundle"
(cd "$bundle" && sha256sum --check MANIFEST.sha256 >/dev/null)
python3 - "$report" <<'PY'
import stat
import sys
import tarfile

with tarfile.open(sys.argv[1], "r:gz") as archive:
    for member in archive.getmembers():
        expected = 0o700 if member.isdir() else 0o600
        assert stat.S_IMODE(member.mode) == expected, (member.name, oct(member.mode))
PY

# Optional log collection remains explicit and produces a reviewable marker.
log_report="$test_root/ai-report-with-logs.tar.gz"
JARVIS_HOME="$fresh_home" JARVIS_TEST_MODE=1 \
  python3 "$fresh_target/scripts/create_ai_report.py" \
  --issue 'Intermittent service warning' --include-logs --output "$log_report"
tar -tzf "$log_report" > "$test_root/log-report-files.txt"
grep -q 'OPTIONAL_SANITISED_LOGS.txt' "$test_root/log-report-files.txt"

# Rolling back a fresh install removes deployed files and retains the replaced
# release in the recoverable retired directory.
JARVIS_HOME="$fresh_home" JARVIS_TEST_MODE=1 \
  bash "$fresh_target/scripts/rollback.sh" --no-restart
test ! -e "$fresh_target"
test ! -e "$fresh_home/.config/jarvis/profile.json"
test ! -e "$fresh_home/.config/jarvis/capabilities.json"
for helper in "${helpers[@]}"; do
  test ! -e "$fresh_home/.local/bin/$helper"
done

# A mid-transaction failure restores the previous deployment automatically.
failure_home="$test_root/failure"
failure_target="$failure_home/.local/src/ovos-skill-jarvis-dispatcher"
mkdir -p "$failure_target" "$failure_home/.local/bin" "$failure_home/.config/jarvis"
printf '%s\n' previous > "$failure_target/previous-release.txt"
cp "$repo_root/profiles/default.json" "$failure_home/.config/jarvis/profile.json"
for helper in "${helpers[@]}"; do
  printf '#!/usr/bin/env bash\necho previous %s\n' "$helper" \
    > "$failure_home/.local/bin/$helper"
  chmod 0755 "$failure_home/.local/bin/$helper"
done
if JARVIS_HOME="$failure_home" JARVIS_TEST_MODE=1 JARVIS_TEST_FAIL_AFTER_DEPLOY=1 \
  bash "$repo_root/scripts/install.sh" --profile brain --no-restart; then
  echo "Injected deployment failure unexpectedly succeeded." >&2
  exit 1
fi
test -f "$failure_target/previous-release.txt"
cmp "$repo_root/profiles/default.json" "$failure_home/.config/jarvis/profile.json"
for helper in "${helpers[@]}"; do
  grep -q "previous $helper" "$failure_home/.local/bin/$helper"
done

# Upgrade rollback restores an existing tree byte-for-byte where it matters.
upgrade_home="$test_root/upgrade"
upgrade_target="$upgrade_home/.local/src/ovos-skill-jarvis-dispatcher"
mkdir -p "$upgrade_target" "$upgrade_home/.local/bin" "$upgrade_home/.config/jarvis"
tar --create --file=- --directory "$repo_root" \
  --exclude='./.git' --exclude='./dist' --exclude='*/__pycache__' . \
  | tar --extract --file=- --directory "$upgrade_target"
cp "$repo_root/ovos_skill_jarvis_dispatcher/wakeword.py" \
  "$upgrade_target/ovos_skill_jarvis_dispatcher/agents.py"
printf '%s\n' legacy > "$upgrade_target/legacy-only.txt"
cp "$repo_root/profiles/default.json" "$upgrade_home/.config/jarvis/profile.json"
for helper in "${helpers[@]}"; do
  printf '#!/usr/bin/env bash\necho legacy %s\n' "$helper" \
    > "$upgrade_home/.local/bin/$helper"
  chmod 0755 "$upgrade_home/.local/bin/$helper"
done

JARVIS_HOME="$upgrade_home" JARVIS_TEST_MODE=1 \
  bash "$repo_root/scripts/install.sh" --profile brain --no-restart
cmp "$repo_root/ovos_skill_jarvis_dispatcher/agents.py" \
  "$upgrade_target/ovos_skill_jarvis_dispatcher/agents.py"
test ! -e "$upgrade_target/legacy-only.txt"

JARVIS_HOME="$upgrade_home" JARVIS_TEST_MODE=1 \
  bash "$upgrade_target/scripts/rollback.sh" --no-restart
cmp "$repo_root/ovos_skill_jarvis_dispatcher/wakeword.py" \
  "$upgrade_target/ovos_skill_jarvis_dispatcher/agents.py"
test -f "$upgrade_target/legacy-only.txt"
cmp "$repo_root/profiles/default.json" "$upgrade_home/.config/jarvis/profile.json"
for helper in "${helpers[@]}"; do
  grep -q "legacy $helper" "$upgrade_home/.local/bin/$helper"
done

echo "PASS: fresh install, reports, failure recovery, upgrade and rollback"
