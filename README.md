# OVOS Commands

Private OVOS Jarvis voice-control system.

This repository preserves the tested voice-command dispatcher, allowlisted
desktop helpers, status indicators, recovery material, configuration examples,
runtime patches, validation tools and implementation history.

Supported wake phrase: `Hey Jarvis`.

## What it does

Jarvis provides local voice control for:

- Brave and Firefox search, navigation and page reading
- Desktop application and focused-window control
- Speech Note dictation, typing and read-back
- Codex and Claude agent windows, messaging and response reading
- Voice-system status, microphone control and safe restart operations

See the [Jarvis command reference](docs/command-reference.md) for practical
examples and links to each command module.

## System architecture

The system is divided into independent layers so an optional component can
fail without taking down direct voice control:

| Layer | Implementation | Language model required |
|---|---|---|
| Wake phrase | OpenWakeWord | No |
| Speech recognition | Faster Whisper | No |
| Spoken output | Kokoro through Phoonnx | No |
| Commands | Modular Jarvis dispatcher | No |
| General conversation | OVOS Persona and Ollama | Optional |

The dispatcher module named `conversation.py` handles controlled command
follow-ups such as asking what to search for. It remains part of the core
command system and is unrelated to optional Qwen conversation.

For command-only configuration, optional conversation setup and model guidance
for different hardware, see the
[Optional local conversation add-on](docs/conversation-addon.md).

## Repository layout

| Path | Purpose |
|---|---|
| `ovos_skill_jarvis_dispatcher/` | Modular OVOS command skill |
| `system_helpers/` | Allowlists and focused desktop automation |
| `tray/` | Independent OVOS status indicator |
| `mic/` | Independent microphone indicator and toggle |
| `scripts/` | Validation, deployment and configuration tools |
| `recovery/` | Runtime patches, service templates, hooks and recovery assets |
| `docs/` | Command reference, tests and implementation decisions |

## Validation and deployment

Validate the dispatcher before deployment:

```bash
python3 scripts/validate_refactor.py
```

Deploy the modular dispatcher to the current user's OVOS source installation:

```bash
bash scripts/deploy-modular-refactor.sh
```

Install the independent indicators when required:

```bash
bash scripts/install-ovos-tray.sh
bash scripts/install-jarvis-mic-indicator.sh
```

Deployment scripts create rollback copies before replacing live files. Runtime
package patches are not automatically applied by dispatcher deployment.

## Browser reading

`Read the page` extracts the main `<main>`, `<article>` or
`[role=main]` content supplied by Firefox or Brave. If semantic extraction is
not available, it safely falls back to copied page text.

`Read the full page` deliberately reads everything, while
`Read selected text` reads only the current selection.

## Runtime resilience

Multi-turn command failures are contained inside `ConversationMixin`. An
unexpected exception clears temporary conversation state and leaves unrelated
browser, desktop, dictation and agent commands available.

Optional changes to installed OVOS packages are stored as separate,
version-checked patches. The patch tool tests each patch independently, skips
incompatible changes and creates a rollback copy before applying anything.

See [Recovery infrastructure](recovery/README.md) for the preserved service
layout, security boundaries, configuration fragments, agent hooks and runtime
patch procedure.

## Status indicators

The OVOS tray shield is green when the required services and dispatcher are
ready, amber while starting, red on failure and grey when stopped. Its menu
provides command restart, full voice-system restart, start, stop and recent-log
actions.

The separate microphone icon is green while `ovos-listener` is active and red
while stopped. Clicking it toggles only the listener without stopping the rest
of OVOS. Both indicators use process locks to prevent duplicate instances.

## Documentation

- [Command reference](docs/command-reference.md)
- [Voice-system optimisation and stabilisation](docs/ovos-voice-system-optimisation-and-stabilisation.md)
- [Modular refactor runtime tests](docs/modular-refactor-runtime-tests.md)
- [Optional local conversation add-on](docs/conversation-addon.md)
- [Recovery infrastructure](recovery/README.md)

## Known-good baseline

The initial commit preserves the tested monolithic dispatcher before its
behaviour-preserving modular refactor. The current modular validation baseline
is maintained by `scripts/validate_refactor.py`.
