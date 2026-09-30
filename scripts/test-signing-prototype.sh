#!/usr/bin/env bash
# Disposable keys only. This does not enable or change updater trust.
set -euo pipefail
command -v minisign >/dev/null 2>&1 || { echo 'BLOCKED: Minisign unavailable' >&2; exit 2; }
umask 077
work="$(mktemp -d "${TMPDIR:-/tmp}/jarvis-signing-test.XXXXXX")"
trap 'rm -rf -- "$work"' EXIT
minisign -v
minisign -G -W -p "$work/old.pub" -s "$work/old.key" >/dev/null
minisign -G -W -p "$work/new.pub" -s "$work/new.key" >/dev/null
printf '%s\n' 'Synthetic release checksum; no live artifact' > "$work/checksum"
minisign -S -s "$work/old.key" -m "$work/checksum" -x "$work/old.sig" >/dev/null
minisign -V -p "$work/old.pub" -m "$work/checksum" -x "$work/old.sig" -q
if minisign -V -p "$work/new.pub" -m "$work/checksum" -x "$work/old.sig" -q 2>/dev/null; then
  echo 'Wrong key accepted' >&2; exit 1
fi
minisign -S -s "$work/new.key" -m "$work/checksum" -x "$work/new.sig" >/dev/null
minisign -V -p "$work/new.pub" -m "$work/checksum" -x "$work/new.sig" -q
printf '%s\n' 'tampered' >> "$work/checksum"
if minisign -V -p "$work/new.pub" -m "$work/checksum" -x "$work/new.sig" -q 2>/dev/null; then
  echo 'Tampered content accepted' >&2; exit 1
fi
echo 'PASS: test keys accept authentic content, reject wrong keys/tampering; rotation needs explicit trust.'
