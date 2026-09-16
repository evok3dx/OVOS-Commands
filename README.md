# OVOS Commands

> [!WARNING]
> **Experimental software.** This project is tested for a small, known group
> of Linux Mint workstations. Review the limitations and run the preflight
> check before installing it on another machine.

Allowlisted voice control for the Linux Mint Jarvis workstation. Routine
commands run locally and do not require a language model.

Repository: [evok3dx/OVOS-Commands](https://github.com/evok3dx/OVOS-Commands)

The repository may be private between announced update windows. Existing
installations continue to work while it is private, but anonymous update
checks and downloads are available only while it is public.

## Quick start

Download the `ovos-commands-2.2.1.tar.gz` archive and matching `.sha256` file
from the [latest GitHub release](https://github.com/evok3dx/OVOS-Commands/releases/latest),
then verify and install it:

```bash
sha256sum --check ovos-commands-2.2.1.tar.gz.sha256
tar -xzf ovos-commands-2.2.1.tar.gz
cd ovos-commands-2.2.1
bash scripts/install.sh
```

From a trusted Git checkout, the equivalent development flow is:

```bash
python3 scripts/validate_refactor.py
bash scripts/install.sh --check
bash scripts/install.sh
```

On a clean Linux Mint laptop, the installer first offers to prepare the
reviewed official OVOS virtualenv baseline and any missing minimal desktop-
control prerequisites. That one-time preparation uses administrator access;
it installs OVOS and command-line dependencies, not desktop applications.
OVOS is installed with telemetry, its LLM fallback and extra community skills
disabled. Existing OVOS installations are left alone.

After preparation, the installer validates the complete inventory, backs up
every replaced component under
`~/.local/state/jarvis/backups/`, deploys one coherent version and restarts
Jarvis once. A failed transaction restores the previous deployment. It works
from a Git checkout or an extracted release archive. Jarvis installation,
configuration, updates and daily operation remain user-space.

First setup offers one simple choice:

1. all detected supported applications;
2. core voice controls only;
3. a custom selection from detected supported applications.

Jarvis never installs or recommends desktop applications. Reopen the same
selection later from the tray or with `jarvis-setup`. Legacy `--profile`
support exists only to migrate an older deployment.

`bash scripts/install.sh --check` remains a read-only diagnostic for machines
whose prerequisites already exist. On a clean laptop, run the normal installer
first so it can offer the reviewed setup.

Restore the most recent deployment with:

```bash
bash scripts/rollback.sh
```

The former `scripts/deploy-modular-refactor.sh` entry point remains as a thin
compatibility wrapper. New documentation and automation use `scripts/install.sh`.

## Capabilities

- Brave and Firefox search, navigation and semantic page reading
- YouTube search and Shorts navigation without unstable result auto-selection
- Open, focus, minimise, maximise and close controls across enabled apps
- Clipboard, text editing, Enter, Tab and Shift+Tab controls
- OS-default Mail, explicit Proton Mail and copied-link Zoom integrations
- Claude Desktop, ChatGPT Desktop and Hermes Desktop controls
- Explicit Claude and ChatGPT website commands using the default browser
- Speech Note dictation and local text-to-speech
- System microphone, speaker, Jarvis-listener and media controls
- State-aware Caps Lock
- Safe personal phrase editor with no arbitrary command execution

See the [command reference](docs/command-reference.md) for spoken forms.

## Universal reading

`Read page`, `Read full page`, `Read window`, `Read app`, `Read screen` and
`Read content` all use the same local reader. Claude and Hermes are never asked
to interpret the screen.

- Brave and Firefox prefer semantic main-content extraction.
- GTK, Qt and Electron apps use AT-SPI accessibility first.
- Claude and Hermes launch with renderer accessibility enabled.
- Clipboard copying is a compatibility fallback.
- Terminal uses terminal-safe copy shortcuts.
- Menus, toolbars, buttons and status UI are excluded where accessibility
  metadata permits.

Speech Note performs local playback. OVOS listening is muted during playback
to prevent self-triggering and restored when reading ends or is interrupted.

## Architecture

| Layer | Responsibility |
|---|---|
| Standard modules | Portable browser, window, text, reading and system actions |
| Integrations | Guarded product-specific behaviour |
| Capabilities | Detected and user-approved application mappings |
| Personal phrases | Alternative wording for existing approved actions |
| Helpers | Fixed, allowlisted local automation |

Core modules live in `ovos_skill_jarvis_dispatcher/`. Product-specific actions
live in `ovos_skill_jarvis_dispatcher/integrations/`. Desktop automation is
restricted to reviewed helpers in `system_helpers/`.

`deployment-manifest.json` is the canonical file inventory shared by
installation and validation. Intent names and vocabulary totals remain
explicit regression tripwires in `scripts/validate_refactor.py`.

Hermes launches through `hermes-secure-launch`, uses the rootless Podman socket
and retains the configured `/srv/agent-inbox/hermes:/workspace:rw` boundary.
The launcher watcher restores the secure desktop entry if a Hermes update
regenerates it.

## Desktop controls

The canonical installer adds the Jarvis tray automatically when GTK 3 is
already available. It provides Setup, health check, support report, update
check, safe restarts, start/stop and logs. No package installation is attempted
if GTK is unavailable; all functions remain accessible from the terminal.

The command editor and microphone indicator remain optional:

```bash
bash scripts/install-command-editor.sh
bash scripts/install-jarvis-mic-indicator.sh
```

The command editor maps personal wording only to approved actions. The OVOS
tray controls service status and safe restarts. The microphone indicator
controls only `ovos-listener.service`.

Wake-word capture tuning remains independent and reversible:

```bash
bash scripts/set-instant-listen.sh enable
jarvis-restart --full
```

## Development and releases

```bash
python3 scripts/validate_refactor.py
bash scripts/test-deployment.sh
bash scripts/build-release.sh
```

CI validates Python 3.10 through 3.13, checks every shell entry point and
builds a clean release archive. Archives exclude Git metadata, caches, logs,
local configuration and previous builds. Each archive has a `.sha256` sidecar
for corruption detection; that checksum is not a publisher signature.

A silent monthly timer checks the configured GitHub release source without
changing the workstation. There are no automatic popups. When a newer release
is found, the tray gains a small red badge and its menu reports the version.
Installation remains manual through `jarvis-update install`, verifies SHA-256,
uses the transactional installer and retains rollback. Checks fail quietly
while the repository is private or the laptop is offline. A separate GitHub
workflow checks current OVOS APIs without changing any workstation.

During an announced public update window, users can select **Check for
updates** in the tray. After detection, the same menu entry changes to the
available version; selecting it opens the supervised installer and confirmation
prompt.

Publishing ordinary commits never updates clients. A client sees an update
only after a higher semantic version is published as a GitHub Release with the
matching versioned archive and checksum assets. Releases are prepared as
drafts, checked, and then published under GitHub release immutability. After
the small user group has updated, the repository may be made private again.

See the [maintenance guide](docs/maintenance.md) before changing inventory or
deployment, and the [repository audit](docs/repository-audit.md) for the v21
cleanup decisions. Earlier implementation reports are retained under
[`docs/history/`](docs/history/README.md) as historical records only.
The [security and update policy](docs/security-and-updates.md) defines the
supported platform, privilege boundary, checksum limits and supervised OVOS
update procedure.

## AI-assisted diagnosis

Create a privacy-first handoff that a coding AI can inspect without a custom
prompt:

```bash
jarvis-report --issue "Describe what failed"
```

The resulting archive contains a safe source snapshot, versions, validation,
service state, integrity hashes and its own AI instructions. It excludes raw
logs, audio, transcripts, clipboard contents and messages by default, and it is
never uploaded automatically. See [AI-assisted maintenance](docs/ai-maintenance.md).

## Repository map

| Path | Purpose |
|---|---|
| `ovos_skill_jarvis_dispatcher/` | Modular OVOS skill |
| `system_helpers/` | Allowlisted local automation |
| `profiles/` | Legacy migration mappings |
| `command_editor/` | Safe GTK personal-phrase editor |
| `tray/` and `mic/` | Independent status controls |
| `scripts/` | Install, rollback, validation, packaging and optional setup |
| `docs/` | Current guides and archived implementation records |

## Validated baseline

- 21 Python modules
- 90 intents
- 1,701 Brain-compatibility vocabulary registrations
- 4 deployment profiles
- 11 runtime helpers
- 6 managed user-systemd units

Normal capability files omit private agent vocabulary, so their registration
count is intentionally smaller. The larger compatibility inventory protects an
existing customised Brain installation during migration.
