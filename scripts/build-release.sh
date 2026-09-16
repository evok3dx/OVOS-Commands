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
  git -C "$repo_root" ls-files -z > "$file_list"
else
  python3 - "$repo_root" > "$file_list" <<'PY'
import os
import sys
from pathlib import Path

root = Path(sys.argv[1])
roots = (
    ".github", "command_editor", "docs", "mic", "ovos_skill_jarvis_dispatcher",
    "profiles", "scripts", "system_helpers", "systemd", "tray",
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
mv -- "$temporary" "$output"

(cd "$(dirname "$output")" && sha256sum "$(basename "$output")") > "$checksum_temporary"
mv -- "$checksum_temporary" "$checksum"
(cd "$(dirname "$output")" && sha256sum --check "$(basename "$checksum")")
printf '%s\n' "Release: $output" "Checksum: $checksum"
