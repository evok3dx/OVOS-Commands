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
- Focused text editing, clipboard actions and field navigation
- Standard Notes, Proton Mail and Zoom-specific integrations
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
| `ovos_skill_jarvis_dispatcher/integrations/` | Contained application-specific actions |
| `profiles/` | Validated machine profiles and app mappings |
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

For users who speak immediately after the wake-word beep, the reversible
listener tuning helper can retain the earliest command audio:

```bash
bash scripts/set-instant-listen.sh enable
jarvis-restart --full
```

Use `status` to inspect the setting or `disable` to restore delayed capture.
Every change creates a timestamped configuration backup.

Install the independent indicators when required:

```bash
bash scripts/install-ovos-tray.sh
bash scripts/install-jarvis-mic-indicator.sh
```

Deployment scripts create rollback copies before replacing live files. Runtime
package patches are not automatically applied by dispatcher deployment.

## Standard commands, integrations and custom profiles

The project deliberately separates three concepts:

| Layer | Purpose | Examples |
|---|---|---|
| Standard commands | Reusable behaviour across applications | Tab, Shift+Tab, copy, paste, save, search this page |
| Integrations | Allowlisted behaviour tied to one application | Standard Notes new/search, Proton Mail compose/search, copied-link Zoom join |
| Profiles | Personal machine mappings without arbitrary commands | `notes` → `standard_notes`, `mail` → `proton_mail` |

Generic behaviour belongs in modules such as `text_editing.py`, `browser.py`
and `desktop.py`. Product-specific behaviour belongs in an independently
guarded module under `integrations/`. Personal app choices belong in JSON under
`profiles/`. This keeps reusable commands portable while preventing one optional
integration from disabling the rest of the dispatcher.

Current integrations:

- `standard_notes.py`: new note, current-note search and all-notes search
- `proton_mail.py`: new message and mailbox search
- `zoom.py`: locally validates a copied Zoom invitation and launches the
  registered `zoommtg` handler without browser redirection

The Brain profile is an example deployment, not a universal default. Exact
executables, app choices, secrets and local paths should remain in profiles or
allowlisted helpers rather than being mixed into generic command logic.

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

Desktop applications are started through detached transient user services.
This prevents an OVOS command restart from terminating an application merely
because Jarvis originally launched it. The application helper also selects the
Brain's regular Flatpak Brave installation (`com.brave.Browser`), avoiding the
separate profile created by the concurrently installed DEB executable.

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
- [Profiles and application integrations](docs/profiles-and-integrations.md)
- [Focused commands, integrations and runtime isolation](docs/focused-commands-integrations-and-runtime-isolation.md)
- [Recovery infrastructure](recovery/README.md)

## Known-good baseline

The initial commit preserves the tested monolithic dispatcher before its
behaviour-preserving modular refactor. The current modular validation baseline
is maintained by `scripts/validate_refactor.py`: 15 Python modules, 63 intents,
994 vocabulary registrations and three validated profiles.
