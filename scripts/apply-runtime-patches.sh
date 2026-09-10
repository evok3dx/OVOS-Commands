#!/usr/bin/env bash
set -u

apply_changes=false

case "${1:-}" in
  "") ;;
  --apply) apply_changes=true ;;
  *)
    echo "Usage: $0 [--apply]" >&2
    exit 2
    ;;
esac

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${OVOS_PYTHON:-$HOME/.venvs/ovos/bin/python}"

if [[ ! -x "$python_bin" ]]; then
    echo "OVOS Python not found: $python_bin" >&2
    exit 1
fi

site_packages="$($python_bin - <<'PY'
import sysconfig
print(sysconfig.get_paths()["purelib"])
PY
)"

version_of() {
    "$python_bin" - "$1" <<'PY'
from importlib.metadata import PackageNotFoundError, version
import sys
try:
    print(version(sys.argv[1]))
except PackageNotFoundError:
    print("")
PY
}

check_patch() {
    package="$1"
    expected="$2"
    patch_name="$3"
    target="$4"
    patch_file="$repo_dir/recovery/runtime-patches/$patch_name"
    installed="$(version_of "$package")"

    printf '\n%s\n' "$patch_name"

    if [[ "$installed" != "$expected" ]]; then
        echo "SKIP: expected $package $expected, found ${installed:-not installed}"
        return
    fi

    if patch --dry-run --reverse --batch --silent \
       -p1 -d "$site_packages" < "$patch_file" >/dev/null 2>&1; then
        echo "PASS: already applied"
        return
    fi

    if ! patch --dry-run --forward --batch --silent \
         -p1 -d "$site_packages" < "$patch_file" >/dev/null 2>&1; then
        echo "SKIP: patch is incompatible with the installed file"
        return
    fi

    if ! "$apply_changes"; then
        echo "PASS: compatible, not applied"
        return
    fi

    stamp="$(date +%Y%m%d-%H%M%S)"
    backup="$site_packages/$target.before-jarvis-$stamp"
    cp -a "$site_packages/$target" "$backup"
    echo "Backup: $backup"

    if patch --forward --batch -p1 -d "$site_packages" < "$patch_file"; then
        echo "PASS: applied"
    else
        echo "FAIL: this patch failed; continuing with remaining patches" >&2
    fi
}

check_patch ovos-core 2.1.1 ovos-core-phal-timeout.patch \
  ovos_core/skill_manager.py
check_patch ovos-dinkum-listener 0.5.0 listener-delayed-barge-in.patch \
  ovos_dinkum_listener/service.py
check_patch ovos-persona 0.7.1 persona-empty-utterance.patch \
  ovos_persona/__init__.py
check_patch ovos-persona 0.7.1 persona-can-stop.patch \
  ovos_persona/__init__.py

echo
if "$apply_changes"; then
    echo "Patch pass complete. Restart affected OVOS services after review."
else
    echo "Compatibility check complete. Use --apply to apply compatible patches."
fi
