# Maintenance guide

## One source of truth

`deployment-manifest.json` defines the modules, integrations, runtime helpers,
profiles and optional desktop assets that make up a complete release.
Installation and validation consume the same inventory.

Release changes and open acceptance checks are recorded once in
[`releases.md`](releases.md). Put reusable problem/solution guidance in
[`troubleshooting.md`](troubleshooting.md), approved constraints in
[`12-decisions.md`](12-decisions.md), and completed investigation detail under
[`history/`](history/README.md). Current documents should link to those records
instead of copying a release narrative.

When adding a capability:

1. Put reusable behaviour in a standard module.
2. Put product-specific behaviour under `integrations/`.
3. Add machine selection only through an allowlisted capability mapping.
4. Add spoken forms to the central vocabulary.
5. Update the manifest only when the file inventory changes.
6. Update the explicit intent and vocabulary regression totals.
7. Run validation before deployment.

For a spoken action, follow the complete command-system update map in the root
[`AGENTS.md`](../AGENTS.md). This keeps deterministic phrases, Qwen exposure,
custom-command collisions and the generated Control Centre Commands list in
sync.

When adding or changing an application window signature, also:

1. capture the real `wmctrl -lx` and `WM_CLASS` values on the affected machine;
2. add the narrowest reviewed literal signature that is required;
3. use `|` only for independent fixed alternatives;
4. verify `jarvis-app-window focus <integration>` on every known packaging variant;
5. verify the product-specific shortcut only after focus succeeds;
6. compare against an existing known-good machine when behaviour differs.

`jarvis-app-window` deliberately treats `|`-separated window signatures as a
list of literal alternatives. Do not replace that with a single literal match
against the full joined value. The 16 September 2026 reference system/laptop comparison
proved that such a mismatch can make an already-open app appear missing.

See [`window-focus-and-app-integration.md`](window-focus-and-app-integration.md)
for the validated troubleshooting sequence.

## Control Centre and tray

| Location | What it shows or controls |
|---|---|
| Dashboard | System Online/Offline, starting, paused or attention state; Speech, Listener and Commands; Run/Stop, restart commands and microphone controls. |
| Dashboard → Recent Activity | Reviewed completed action labels from the last five minutes, with Refresh and an unavailable message if the reader cannot respond. |
| General | Light/Dark appearance; independent tray and voice login choices; No logs or Diagnostics for 5 minutes. |
| Maintenance → Isolation | Current core/private-model policy, Refresh status and Check isolation. Policy configuration is separate from a network-test result. |
| Maintenance → Recent logs | Temporary diagnostics with fixed failure reasons, elapsed time and collector availability. Enable in General before reproducing a problem. |
| Updates | Explicit check/install controls. A successful up-to-date check uses a green button; an available update uses blue; an unavailable check remains unconfirmed. |

Dashboard and tray share the same service-state reader. With isolation active,
they inspect/control the real system workers instead of the compatibility user
relays. Current core/listener readiness and service states keep Starting visible
until the reviewed startup checks pass. A failed worker is not silently presented as stopped.
Pausing the Jarvis microphone leaves other applications' microphones alone.

Recent Activity is separate from logging: No logs still allows fixed action
labels in memory. The feed contains at most 32 rows and displays the latest
five matching rows in the GUI; restarting command handling clears its session.
It never records transcripts, dictated content, queries or window titles.

For inspection versus actual network checks and their limits, see
[Control Centre status and checks](core-isolation.md#control-centre-status-and-checks).
For expiry, existing logs and other applications, see the
[logging policy](security-and-updates.md#application-logging-in-43).

## Supported entry points

A successful **Maintenance → Health check** shows a green **No errors found**
button. Warnings remain in the expanded results. Running another check resets
the previous success indicator; failures stay visible. This checks the host
and installation, separately from the explicit isolation network tests.

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
| `jarvis-health-check` | Validate the live host and Jarvis installation |
| `jarvis-isolation-check --test-network --test-model` | Explicit current-worker network and private-model checks; private report in Downloads |
| `jarvis-report --issue "..."` | Build a private diagnostic handoff |
| `jarvis-update check` | Check the configured release source without installing |
| `jarvis-update install` | Verify and install a newer release transactionally |
| `jarvis-update rollback` | Restore the latest Jarvis deployment snapshot |
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
- Window-class alternatives are fixed in reviewed helpers, never supplied by speech or arbitrary profile values.
- V4 generic writing and submission refuse terminal windows.
- Zoom links are validated locally before invoking the registered URI handler.
- Claude and ChatGPT controls are limited to ordinary chat applications.
- Agent users, sudo rules and privileged helpers are outside normal setup.
- Actual Hermes helper permissions and tool access require owner-machine review;
  ordinary installation does not install an agent platform or prove its isolation.
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

The update ownership boundary is intentionally small:

- release-managed package code, documented runtime helpers and desktop assets
  are updated;
- OVOS configuration, capabilities, personal commands, shortcuts, sounds and
  unlisted private helpers are machine-owned and preserved;
- the reviewed runtime is staged as a unit, or reused only with matching
  provenance; the previous environment remains available for rollback and model
  caches are preserved;
- fresh installations still receive the complete reviewed setup.

Do not add a machine-owned path to the replacement set merely because the
installer can recreate it. Add a migration only when the new release cannot
operate safely with the existing value, and cover that migration with an
upgrade-preservation regression test.

## Release discipline

The version in a local working directory name is not authoritative. The
published version is the latest GitHub Release; the source version is the
version declared in `pyproject.toml` and repository metadata. `main` may contain
fixes that have not yet been released.

Before publishing a release that changes desktop integration behaviour:

```text
known-good machine
+ affected/new machine
+ capability mapping
+ wmctrl/WM_CLASS capture
+ jarvis-app-window focus test
+ app shortcut test
+ spoken-intent test
+ repository validation
+ deployment/rollback test
```

Do not publish a portability change based only on one machine's window title or
class.

## Documentation policy

`README.md`, `docs/command-reference.md`, `docs/troubleshooting.md`, this guide,
`docs/profiles-and-integrations.md` and
`docs/window-focus-and-app-integration.md` describe current operation. Files
under `docs/history/` preserve implementation rationale and old observed
baselines; their installer names and counts must not be treated as current
instructions. `docs/releases.md` is the only current per-release ledger.

## Temporary repairs and test folders

**PLANNED owner cleanup:** retire obsolete one-off public repair scripts and
their preparation/publication workflows after supported devices have upgraded
and their recovery links are no longer needed. Raw GitHub URLs serve files
from repository commits; there is no separate raw-file storage area. Removing
a current file does not remove copies from Git history or old release archives.

The current repair inventory includes `apply-gui-update-lock-fix.py`,
`apply-v4-final-fix.py`, `apply-v4-lifecycle-fix.py`,
`apply-v4-media-timing-fix.py` and `apply-v4-weather-fix.py` under `scripts/`.
Keep the GUI updater repair while older isolated deployments need it. Review
documentation and regression references together before deleting a repair.

Owner-run clipboard trials use `Downloads/Jarvis-Clipboard-Test-*` and the
downloaded clipboard patch files. Remove those identified copies only after
the released installation works and no helper/process still uses them. Other
Downloads trials require their own inventory; a broad `Jarvis-*` deletion is
unsafe. Preserve active isolation candidates/receipts, installation journals,
rollback backups, models and settings. Never automatically prune an unfinished
update or its recovery evidence.
