# Jarvis · OVOS Commands

Voice shortcuts and desktop control for Linux Mint. Jarvis handles reviewed
commands locally; the local Qwen model interprets a limited set
of enabled-app requests. It never executes a model-generated shell command.

Jarvis was built to make everyday Linux control feel natural without turning
speech into an unrestricted command line. Exact commands stay fast and local;
Qwen is only a fallback for approved actions, and machine-specific choices
remain yours.

> **Version 3.6:** Linux Mint on X11 with Python 3.11 is the workstation
> target. The separate Media and File Search plugins stay bundled. The first
> laptop installation is a supervised test of the reference system-compatible OVOS stack.

## Get started

For the published version, download its archive and matching `.sha256` from
[Releases](https://github.com/evok3dx/OVOS-Commands/releases/latest):

```bash
version=3.6.0
sha256sum --check "ovos-commands-$version.tar.gz.sha256"
tar -xzf "ovos-commands-$version.tar.gz"
cd "ovos-commands-$version"
bash scripts/install.sh --check
bash scripts/install.sh
```

In a trusted source checkout, run `python3 scripts/validate_refactor.py` before installation.
`--check` is read-only. On a fresh workstation, the normal installer can offer
to prepare missing OVOS and basic desktop tools.

```mermaid
flowchart TD
  A["Fresh install"] --> C["Prepare OVOS (administrator access once) and model"]
  B["Update"] --> D["Back up Jarvis and stage OVOS"]
  C --> D
  D --> E["Install Jarvis; preserve machine settings; check"]
  E -->|"Failure"| F["Restore backup"]
```

A fresh OVOS setup may request administrator access **once** for the official
OVOS installer and missing system tools. The installer asks before downloading
the required local Qwen model; Ollama must already be installed and running.
Daily use and Jarvis updates run as your desktop user. This update stages the
complete audited reference system package set in a clean staged OVOS virtualenv. It keeps
the previous virtualenv for rollback and preserves local
models, wake and audio settings, saved apps, personal commands, shortcuts,
sounds and private host helpers. `bash scripts/rollback.sh` restores the
previous Jarvis deployment and OVOS virtualenv. See [exact pins and migration
details](docs/07-installer-updates.md).

## What you can do

| Area | Examples | Where to adjust it |
|---|---|---|
| Apps and windows | “Open Firefox”, “Open notes”, “Open mail”, “Close window” | Jarvis → Apps & Commands |
| Navigation and writing | “Page down”, “Top of page”, “New line”, “Full stop” | [Command reference](docs/command-reference.md) |
| Media and files | “Play {title}”, “Pause music”, “Find {filename}” | Jarvis → Apps & Commands |
| Voice | Wake phrase, shortcuts, background-audio level, optional Speech Note | Jarvis → Voice |
| Updates | Version, release date, update check and install | Jarvis → Updates |
| Maintenance | Health check, settings export and support | Jarvis → Maintenance |

The **single tray icon** shows service, update and Jarvis microphone status.
The Control Centre keeps app selection, default app roles, commands, voice settings, maintenance and updates
in one window. Its Overview shows Speech, Listener and Commands separately,
plus installed/latest release information after an update check. Fresh setup
offers Recommended, All and Custom app choices; Recommended is the default and
enables only detected everyday apps. Closing the tray window closes
only the interface. The voice services keep running.

The Defaults page chooses which enabled app answers friendly names such as
**browser**, **notes**, **mail**, **calendar** and **office**. Native packages,
Flatpaks and safe desktop-menu entries are detected without accepting spoken
commands or paths. Brave remains the first Media browser; enabled Firefox is
the bounded fallback when Brave cannot open a validated YouTube result.

Settings export creates a private archive that you can inspect and restore
manually. It may contain credentials; keep it private. It does not include
models, recordings, applications or code, and it is separate from the
installer's automatic rollback backup.

**Maintenance → Advanced → Uninstall Jarvis** removes the commands, plugins,
tray and managed user services. It can also remove the local Qwen model,
personal Jarvis settings and the complete OVOS environment after separate,
explicit choices. It never silently removes Speech Note or other desktop apps.

The model download is prompted only when missing. The installer checks the
local routing stages before enabling them. It leaves a different configured
model alone and stops for review. On the older i7, latency still needs a real
voice test. [Local routing details](docs/04-local-routing.md).

## Security model

- Speech and Qwen select only reviewed action IDs. They never produce a shell
  command, executable path or arbitrary URL.
- Risky actions remain strict; changing focus cancels pending typing or search.
- Configuration writes are private and atomic. Updates stage, validate and
  retain rollback before replacing a working deployment.
- No new listening port is introduced. Ollama remains on its existing local
  endpoint, and exports exclude models, logs, recordings and unknown files.

See [Security and updates](docs/security-and-updates.md) for the full boundary.

## Guides

- [V3.1 laptop test checklist](docs/v3.1-checklist.md) · [V3 features](docs/v3-update.md)
- [V3.6 final release checklist](docs/v3.6-release-checklist.md)
- [Architecture and components](docs/01-architecture.md)
- [OVOS voice and reference system media status](docs/06-ovos-voice.md)
- [Media and filename search](docs/10-media-files.md)
- [Install, update and rollback details](docs/07-installer-updates.md)
- [Settings export and voice preservation](docs/09-backup-export.md)
- [Supported commands](docs/command-reference.md) · [Profiles and applications](docs/profiles-and-integrations.md)
- [Troubleshooting](docs/troubleshooting.md) · [Security and updates](docs/security-and-updates.md)
- [Living V3 audit](docs/v2.4-audit.md) · [Detailed source reconciliation](docs/v3-final-audit.md) · [Decisions](docs/12-decisions.md)

This is a small workstation project. Check the health report and try a few
spoken commands after updating either machine; an automated code check cannot
verify a microphone, GPU driver or external media provider for you.

## Licence and thanks

Jarvis is Apache-2.0 licensed. See [licence and acknowledgements](NOTICE.md) for
the OpenVoiceOS, openWakeWord, Whisper, Qwen, Ollama, phoonnx, Speech Note and
desktop projects that make it possible. Third-party packages and models retain
their own licences.
