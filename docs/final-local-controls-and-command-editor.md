# Final Local Controls, Claude Routing and Command Editor

## Purpose

This document records the final OVOS command phase completed after `Focused
Commands, Application Integrations and Runtime Isolation`. It covers microphone
controls, the separation of Claude Desktop from the local Claude agent, and the
small tray-based command editor.

The objective remained the same: make useful controls accessible to a
non-technical user without weakening the allowlist, permitting arbitrary code,
or making optional integrations capable of disabling core voice commands.

## Final validated baseline

The repository validator now reports:

```text
PASS: 18 Python modules compile
PASS: 66 intents match the expected inventory
PASS: 998 vocabulary registrations are present
PASS: personal phrase validation rejects built-in collisions
PASS: personal phrases save atomically with private permissions
PASS: built-in phrases are grouped by editor action
PASS: 3 deployment profiles validate
PASS: package imports and create_skill() succeeds
```

The 998 figure is the immutable built-in vocabulary baseline. Personal phrases
are intentionally counted separately because each machine can have a different
private set.

## System microphone and Jarvis-listener controls

Two different mute operations are exposed:

- `Mute mic` and `Mute microphone` call the allowlisted
  `jarvis-system-microphone` helper. It uses `wpctl` when available and `pactl`
  as its fallback.
- `Mute Jarvis` and `Stop Jarvis listening` stop only `ovos-listener` through
  the existing `jarvis-mic-toggle` helper.

The distinction matters. Muting the system microphone affects every
application, while muting Jarvis leaves the device microphone available to
Zoom, dictation and other applications.

There is deliberately no spoken system-unmute command: once the input is muted,
Jarvis cannot hear it. The user can unmute from the keyboard, sound settings or
the helper. Jarvis listening is restored from the existing microphone tray
indicator.

## Claude Desktop and local Claude agent

The two Claude routes now have explicit semantics:

- ordinary wording such as `Open Claude`, `Focus Claude` and `Message Claude`
  targets Claude Desktop;
- wording that includes `agent`, such as `Message Claude agent`, targets the
  isolated local terminal agent.

Claude Desktop messaging opens or focuses the verified application, confirms
that the expected Claude window owns focus, asks for the message and types only
into that retained window. A focus change cancels the operation.

This matches normal usage: Claude Desktop provides the ongoing conversational
context, while the isolated agent remains available for a specific research,
coding or file task.

## Why a small GTK editor was chosen

The native OVOS GUI client was not installed on the Linux Mint Brain. Building
the current Qt/Kirigami stack would introduce a separate GUI runtime and
dependencies without improving the command workflow.

The existing Cinnamon tray already provided the natural control surface, so it
gained one item: **Commands…**. That opens a focused GTK 3 window rather than a
code editor or full administration dashboard.

The window provides:

1. search and category filtering;
2. a list of approved Jarvis actions;
3. every built-in phrase registered for the selected action;
4. personal phrases attached to that action;
5. add, remove and **Save & Reload** controls.

The final default size is 820 × 720, with a minimum action-list height of 260
pixels so the list remains usable alongside the two phrase panels.

## Security boundary

The editor changes wording, not authority.

- Built-in phrases are read-only.
- Personal phrases map only to an explicit action catalogue.
- Built-in collisions and reserved conversation words are rejected.
- Unknown action identifiers are rejected.
- Phrase length and total phrase count are bounded.
- Configuration is written atomically with mode `0600`.
- Invalid custom configuration is ignored without stopping the dispatcher.
- Shell commands, executable paths and arbitrary hotkeys cannot be entered.

Personal configuration is stored at:

```text
~/.config/jarvis/custom-commands.json
```

This keeps machine-specific wording outside the repository and avoids changing
the deterministic built-in count.

## Why arbitrary macros remain excluded

A sequence such as “open an application, verify it, then press a shortcut” is
technically possible. It would need a separate restricted macro model with an
allowlisted application, an allowlisted keystroke, window verification and
explicit timing rules.

The phrase editor does not pretend to provide that capability. Genuinely new
behaviour remains a reviewed code change, which is safer and easier to recover.

## Installation and rollback

The command editor is installed separately from the core dispatcher:

```bash
bash scripts/install-command-editor.sh
```

The installer validates the complete dispatcher, checks GTK support, backs up
every changed file, preserves an existing personal phrase file, generates the
built-in phrase inventory, restarts one tray process and performs one Jarvis
command reload.

Rollback is explicit:

```bash
bash scripts/uninstall-command-editor.sh
```

Rollback restores the previous source, tray and editor files. Personal phrases
are retained rather than deleted.

## Operational note

The recurring `ovos_plugin_manager.templates.solvers` deprecation warning comes
from `ovos_yes_no_solver`, not from this dispatcher or command editor. It is a
forward-compatibility notice for a future OVOS major release and does not
indicate that current commands failed.

## Final state

The completed OVOS command system now has four deliberate extension layers:

| Layer | Responsibility |
|---|---|
| Standard commands | Reusable browser, window, text, reading and system actions |
| Integrations | Guarded Standard Notes, Proton Mail, Zoom and Claude Desktop behaviour |
| Profiles | Approved application mappings for a particular machine |
| Personal phrases | Private alternative wording for existing approved actions |

This closes the OVOS command phase with a maintainable repository baseline, a
small user-facing command surface and no expansion of arbitrary execution
authority.
