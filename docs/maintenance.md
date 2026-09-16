# Maintenance guide

## One source of truth

`deployment-manifest.json` defines the modules, integrations, runtime helpers,
profiles and optional desktop assets that make up a complete release.
Installation and validation consume the same inventory.

When adding a capability:

1. Put reusable behaviour in a standard module.
2. Put product-specific behaviour under `integrations/`.
3. Add machine selection only through an allowlisted capability mapping.
4. Add spoken forms to the central vocabulary.
5. Update the manifest only when the file inventory changes.
6. Update the explicit intent and vocabulary regression totals.
7. Run validation before deployment.

## Supported entry points

| Command | Purpose |
|---|---|
| `python3 scripts/validate_refactor.py` | Static inventory and safety checks |
| `bash scripts/install.sh --check` | Preflight without changing files |
| `bash scripts/install.sh` | Canonical validated deployment |
| `bash scripts/rollback.sh` | Restore the latest deployment backup |
| `bash scripts/build-release.sh` | Validated release archive |
| `bash scripts/test-deployment.sh` | Isolated install/rollback regression |
| `python3 scripts/setup.py` | Detect and select reviewed applications |
| `jarvis-speechnote-setup` | Manage the optional per-user Speech Note add-on |
| `python3 scripts/update.py` | Check, verify, install or roll back a release |
| `python3 scripts/check_upstream.py` | Read-only OVOS upstream drift report |
| `python3 scripts/doctor.py` | Host, API and deployment compatibility checks |
| `bash scripts/deploy-modular-refactor.sh` | Legacy compatibility wrapper |

Feature-by-feature patch installers are intentionally not part of the current
maintenance model. The canonical installer is idempotent and deploys one
coherent baseline. The tray is installed automatically only when GTK 3 is
already available. Missing GTK does not trigger package installation or block
voice commands.

## Safety boundaries

- Personal phrases cannot add shell commands or arbitrary executables.
- Focused-window actions refuse the desktop and Cinnamon panel.
- Application actions resolve through capabilities and fixed helper cases.
- Terminal text entry never presses Enter automatically.
- Zoom links are validated locally before invoking the registered URI handler.
- Claude and ChatGPT controls are limited to ordinary chat applications.
- Agent users, sudo rules and privileged helpers are outside normal setup.
- Hermes terminal execution remains isolated from the host home directory.
- Secrets, raw logs, audio captures, backups and local configuration are
  excluded from Git and release archives.

## Deployment and rollback

The installer performs source validation and capability resolution before creating
a backup or replacing live files. A deployment snapshot contains the previous
package, private capability file, runtime helpers, tray, Hermes launcher and
systemd watcher units.
If any step fails after replacement begins, the exit trap invokes rollback and
retains the failed deployment under the recoverable `retired` directory.

The latest snapshot path is stored at
`~/.local/state/jarvis/latest-backup`. `scripts/rollback.sh` accepts an explicit
snapshot path or uses that latest pointer. It rejects paths outside the Jarvis
backup directory.

Updates are supervised. The monthly local release check and weekly upstream
compatibility workflow are read-only. Only an explicit `jarvis-update install`
changes the deployment, and it uses checksum verification and rollback
protection.

## Documentation policy

`README.md`, `docs/command-reference.md`, this guide and
`docs/profiles-and-integrations.md` describe current operation. Files under
`docs/history/` preserve implementation rationale and old observed baselines;
their installer names and counts must not be treated as current instructions.
