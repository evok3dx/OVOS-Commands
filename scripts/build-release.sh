#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version="$({ sed -nE 's/^version = "([^"]+)"/\1/p' "$repo_root/pyproject.toml" || true; } | head -n 1)"
[[ -n "$version" ]] || {
  echo "Could not read the project version." >&2
  exit 1
}

output="${1:-$repo_root/dist/ovos-commands-$version.tar.gz}"
archive_root="ovos-commands-$version"
checksum="$output.sha256"

python3 "$repo_root/scripts/validate_refactor.py"
mkdir -p "$(dirname "$output")"
temporary="$(mktemp "$(dirname "$output")/.release.XXXXXX.tar.gz")"
file_list="$(mktemp "$(dirname "$output")/.release-files.XXXXXX")"
archive_list="$(mktemp "$(dirname "$output")/.release-list.XXXXXX")"
checksum_temporary="$(mktemp "$(dirname "$output")/.release-checksum.XXXXXX")"
cleanup() {
  rm -f -- "$temporary" "$file_list" "$archive_list" "$checksum_temporary"
}
trap cleanup EXIT

if git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$repo_root" ls-files --cached --others --exclude-standard -z > "$file_list"
else
  python3 - "$repo_root" > "$file_list" <<'PY'
import os
import sys
from pathlib import Path

root = Path(sys.argv[1])
roots = (
    ".github", "command_editor", "docs", "mic", "ovos_skill_jarvis_dispatcher",
    "profiles", "scripts", "system_helpers", "systemd", "tray", "voice",
)
files = (
    ".gitignore", "COMMAND-EDITOR.md", "README.md", "compatibility.json",
    "deployment-manifest.json", "pyproject.toml",
)
excluded = {".git", "__pycache__", "dist"}
for relative in files:
    path = root / relative
    if path.is_file() and not path.is_symlink():
        os.write(1, relative.encode() + b"\0")
for relative in roots:
    for path in sorted((root / relative).rglob("*")):
        candidate = path.relative_to(root)
        if path.is_file() and not path.is_symlink() and not excluded.intersection(candidate.parts):
            os.write(1, str(candidate).encode() + b"\0")
PY
fi

tar --create --gzip --file "$temporary" \
  --directory "$repo_root" \
  --null --files-from "$file_list" \
  --transform="s|^|$archive_root/|"
tar -tzf "$temporary" > "$archive_list"
if grep -Eq '(^|/)(\.git|__pycache__|dist)(/|$)|\.pyc$' "$archive_list"; then
  echo "Release contains excluded build artefacts." >&2
  exit 1
fi
python3 - "$repo_root/deployment-manifest.json" "$archive_list" "$archive_root" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
archived = set(Path(sys.argv[2]).read_text(encoding="utf-8").splitlines())
root = sys.argv[3]
expected = {
    *(f"ovos_skill_jarvis_dispatcher/{name}" for name in manifest["package_modules"]),
    *(f"ovos_skill_jarvis_dispatcher/integrations/{name}"
      for name in manifest["integration_modules"]),
    *(f"system_helpers/{name}" for name in manifest["runtime_helpers"]),
    *(f"profiles/{name}" for name in manifest["profiles"]),
    *manifest["systemd_templates"],
}
for files in manifest["optional_components"].values():
    expected.update(files)
missing = sorted(f"{root}/{name}" for name in expected if f"{root}/{name}" not in archived)
if missing:
    raise SystemExit(
        "Release is missing manifest-listed files (are they tracked by Git?):\n"
        + "\n".join(missing)
    )
PY
mv -- "$temporary" "$output"

(cd "$(dirname "$output")" && sha256sum "$(basename "$output")") > "$checksum_temporary"
mv -- "$checksum_temporary" "$checksum"
(cd "$(dirname "$output")" && sha256sum --check "$(basename "$checksum")")
printf '%s\n' "Release: $output" "Checksum: $checksum"
