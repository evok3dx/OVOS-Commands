#!/usr/bin/env bash
# Compatibility entry point retained for existing documentation and habits.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "deploy-modular-refactor.sh is deprecated; using install.sh." >&2
exec bash "$script_dir/install.sh" "$@"
