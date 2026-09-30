#!/usr/bin/env bash
# Read-only scanner: no uploads, installs or automatic secret deletion.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mode="${1:-quick}"
command -v gitleaks >/dev/null 2>&1 || {
  echo 'BLOCKED: gitleaks is required; no secret-scan pass can be claimed.' >&2
  exit 2
}
gitleaks version
case "$mode" in
  quick)
    gitleaks dir "$repo_root" --redact --no-banner
    ;;
  history)
    git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null
    gitleaks git "$repo_root" --redact --no-banner --log-opts=--all
    ;;
  release)
    [[ $# == 2 && -f "$2" ]] || { echo 'Usage: security-audit.sh release ARCHIVE' >&2; exit 2; }
    work="$(mktemp -d "${TMPDIR:-/tmp}/jarvis-release-audit.XXXXXX")"
    trap 'rm -rf -- "$work"' EXIT
    python3 - "$repo_root" "$2" "$work" <<'PY'
import importlib.util
import sys
from pathlib import Path
repo,archive,directory=map(Path,sys.argv[1:])
sys.path.insert(0,str(repo/'scripts'))
from release_privacy import check_path
spec=importlib.util.spec_from_file_location('updater',repo/'scripts/update.py')
updater=importlib.util.module_from_spec(spec);spec.loader.exec_module(updater)
root=updater.safe_extract(archive,directory/'extracted')
for path in root.rglob('*'):
    try:
        check_path(path.relative_to(root).as_posix())
    except ValueError:
        raise SystemExit('BLOCKED: private/unreviewed artifact in release')
print('Release extraction and private-artifact check passed.')
PY
    gitleaks dir "$work/extracted" --redact --no-banner
    ;;
  *) echo 'Usage: security-audit.sh {quick|history|release ARCHIVE}' >&2; exit 2 ;;
esac
echo "PASS: secret scan ($mode). This is scanner evidence, not proof that no secret exists."
