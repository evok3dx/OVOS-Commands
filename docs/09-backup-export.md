# Backups and settings export

**VERIFIED in code:** the installer snapshots the Jarvis deployment it replaces
and rolls it back after a failed installation. `scripts/rollback.sh` restores
that snapshot on request. This is for the **same machine**; it does not provision
another desktop.

The Control Centre's **Maintenance → Export settings** writes a private `.tar.gz`
with a manifest and SHA-256 hashes. `scripts/settings_export.py` reads only
allowlisted per-user settings files, excludes links and large files, and does
not overwrite an existing archive. It can include saved OVOS settings and
service credentials. The current allowlist covers app choices, spoken names,
personal commands, wake phrase, shortcuts, local-router settings, update
settings, listening/volume configuration, personas, the listening cue and the
saved normal Speech Note reading speed. Inspect and keep it private. It excludes recordings, logs,
models, installed applications and source changes. Restoration is manual: unpack
to a separate folder, inspect the manifest and copy selected settings after
review. No automatic cross-machine import is implemented.

**PLANNED:** merge-based, privacy-filtered import that respects the destination
machine's enabled applications, voice packages and shortcuts. Until that is
implemented and tested, do not treat an export as a portable installation.

## Uninstall

**VERIFIED in isolated tests:** Maintenance's Advanced section and
`jarvis-uninstall` remove Jarvis's own packages, helpers, tray, launchers and
managed user services. Qwen, Jarvis settings/history and the complete OVOS
environment are independent explicit choices. Speech Note and unrelated
desktop applications are never removed. This is deliberately separate from
rollback: rollback restores the previous Jarvis deployment; uninstall removes
the current one.
