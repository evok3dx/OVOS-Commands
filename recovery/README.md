# Recovery infrastructure

This directory preserves the small OVOS runtime changes and sanitised configuration required to reproduce the tested Jarvis voice system.

It intentionally excludes:

- API keys and credentials
- agent response payloads
- private conversation history
- raw machine backups
- hard-coded user home directories

## Runtime patches

The patches target the versions recorded in `inventory/runtime-versions.txt`:

- OVOS Core 2.1.1: limit the missing PHAL connectivity response wait to three seconds.
- OVOS Dinkum Listener 0.5.0: delay fake barge-in attenuation until after the wake acknowledgement sound begins.
- OVOS Persona 0.7.1: ignore empty utterances.
- OVOS Persona 0.7.1: advertise stoppable output.

Use `scripts/apply-runtime-patches.sh` without arguments to inspect compatibility. Pass `--apply` only after reviewing the result. Each patch is checked and applied separately. An incompatible optional patch is skipped rather than aborting all recovery work.

Installed-package updates may replace these changes. Re-run the compatibility check after upgrading OVOS and prefer upstream fixes when they become available.

## Configuration

`config/mycroft-command-only.fragment.json` documents the tested voice-command profile. It is a fragment, not a complete replacement for `mycroft.conf`.

The local conversation system is optional. See `docs/conversation-addon.md`.

## Security model

The recovery material is configuration and source only. Runtime response files remain outside Git under `/var/spool/jarvis-responses`, with restricted ownership and permissions. Privileged agent messaging remains allowlisted and should never accept an arbitrary command, user name or destination path.

The `agent-hooks` directory contains source hooks only. It contains no captured response data. The matching systemd path units preserve the tested split: completion notifications may be enabled automatically, while full response-reading path units remain disabled unless explicitly requested.

Files ending in `.in` are templates. Replace the named placeholders during installation rather than committing a real account name.
