# Final Hermes, Media and System Controls

## Purpose

This document records the OVOS command phase completed after `Final Local
Controls, Claude Routing and Command Editor`. It covers the final Claude
Desktop and Claude agent split, YouTube navigation, Hermes Desktop control,
universal Enter, media playback, state-aware Caps Lock and the distinction
between microphone, full-system and Jarvis-listener mute.

The objective remained narrow: expose useful desktop actions to a
non-technical user while keeping every action allowlisted, focus-verified and
independent from optional language-model services.

## Final validated baseline

The repository validator now reports:

```text
PASS: 20 Python modules compile
PASS: 88 intents match the expected inventory
PASS: 1259 vocabulary registrations are present
PASS: personal phrase validation rejects built-in collisions
PASS: personal phrases save atomically with private permissions
PASS: built-in phrases are grouped by editor action
PASS: 3 deployment profiles validate
PASS: package imports and create_skill() succeeds
```

The 1,259 figure is the immutable built-in vocabulary baseline. Personal
phrases remain machine-private and are counted separately.

## Claude Desktop and Claude agent completion

Ordinary Claude wording continues to target Claude Desktop. Wording that
contains `agent` continues to target the isolated `agent-claude` account.

The completed controls include:

- `New Claude chat` opens `claude://claude.ai/new` and verifies the resulting
  Claude Desktop window.
- `Message Claude`, `Ask Claude`, `Tell Claude`, `Write to Claude`, `Type into
  Claude` and equivalent approved forms open a clean chat, ask for the message,
  clear the composer, type it and press Enter.
- `New Claude agent`, `Create Claude subagent`, `Show Claude agents` and
  `Resume Claude agent` remain explicit isolated-agent operations.
- observed recognition forms such as `cloud`, `clawed` and `called` are
  allowlisted without weakening the required Claude/agent distinction.

If focus changes before a captured message is sent, the operation cancels.
Message text is not repeated aloud and no unnecessary `send it` confirmation is
required.

## YouTube search and Shorts

`Search YouTube` first checks whether the visible browser tab is already a
YouTube page. If it is, Jarvis uses YouTube's `/` shortcut to expose the search
field before asking for the query. If it is not, Jarvis opens YouTube in the
preferred supported browser and then follows the same visible sequence.

When several YouTube tabs exist, Jarvis uses only the currently visible tab. It
does not select a background tab by title because that would be ambiguous.

`Open YouTube Shorts` and the recognition-tolerant `YouTube reels` wording open
the Shorts feed. Automatic `play first result` and `play second result`
behaviour was deliberately removed. DOM order, advertisements, focus and result
layout are not stable enough for a dependable local command.

## Hermes Desktop integration

Hermes is now a validated application category in the Brain profile. The
allowlisted application helper can open, focus, minimise and close the verified
`hermes.Hermes` window and launches it through its desktop entry in a detached
transient user service.

Composer commands map only to documented Hermes shortcuts:

| Spoken action | Hermes action |
|---|---|
| `Focus Hermes composer` | `Ctrl+L` |
| `Open Hermes model picker` | `Ctrl+Shift+M` |
| `New line in Hermes` | `Shift+Enter` after focusing the composer |
| `Queue Hermes message` | `Ctrl+Enter` after focusing the composer |
| `Send next Hermes message` | `Ctrl+Shift+K` |
| `Open Hermes commands` | Type `/` in the composer |
| `Reference file in Hermes` | Type `@` in the composer |
| `Cancel Hermes run` | `Escape` |

Direct message forms including `Message Hermes`, `Ask Hermes`, `Tell Hermes`,
`Write to Hermes`, `Type into Hermes`, `Speak to Hermes` and `Talk to Hermes`
use a controlled follow-up:

1. open or focus Hermes;
2. verify its window class;
3. focus and clear the composer;
4. ask what to send;
5. verify that the same window still owns focus;
6. type the response and press Enter.

There is no read-back or second confirmation. The safe observed STT aliases
`Hermas` and `Omos` are registered. The unrelated phrase `from me` is not.

## Universal Enter and Caps Lock

`Press Enter`, `Press Return`, `Press Send`, `Hit Enter` and `Hit Return` send
Return to the focused application. This is intentionally independent from any
specific chat application.

Caps Lock commands read the current X11 lock state with `xset q` and press the
lock key only when a change is necessary. Caps Lock bypasses the normal
`--clearmodifiers` helper. Restoring cleared modifiers after a lock-key press
was found to immediately restore the old state, which made Caps Lock appear to
turn on and then off.

## Cinnamon and MPRIS media control

State-specific media commands use `playerctl`:

- play or resume media;
- pause media;
- stop media;
- next or skip track;
- previous or back track.

The helper therefore controls the same MPRIS-capable playback exposed through
Cinnamon's sound panel and keyboard media keys, including supported browser
playback. `playerctl` is an explicit installation dependency. Bare `play`,
`pause` and `stop` remain excluded because they collide with Jarvis speech,
dictation and conversation flows.

## Three separate mute scopes

The command system now preserves three different meanings:

| Command | Scope | Recovery |
|---|---|---|
| `Mute mic` / `Mute microphone` | Default system input | Keyboard or Cinnamon sound settings |
| `Mute system` / `Mute everything` | Default speaker and microphone | Keyboard or Cinnamon sound settings |
| `Mute Jarvis` / `Stop Jarvis listening` | `ovos-listener` only | Jarvis microphone tray icon |

Full-system mute speaks a warning before muting. The allowlisted helper uses
`wpctl` and falls back to `pactl`. If muting the microphone fails after muting
the speaker, it attempts to restore the speaker before returning failure.

There are deliberately no spoken system-unmute commands because a muted input
cannot hear them.

## Command editor integration

Every new action is represented in the existing command editor catalogue.
Users may add private alternative wording, but only to these approved actions.
They cannot enter arbitrary shell commands, executable paths or keyboard
macros.

The editor therefore grows with the command inventory without changing its
authority model.

## Installation and repeatability

The consolidated installer for this phase is:

```bash
bash scripts/install-hermes-composer-system-controls.sh
```

It validates the complete source tree first, checks `xdotool`, `xset` and
`playerctl`, creates a timestamped rollback copy, replaces the approved modules,
compiles the deployed package and restarts Jarvis once.

Running the installer more than once does not duplicate intents or vocabulary.
It replaces source files with the same deterministic versions and creates
another rollback snapshot.

## Operational observations

- The recurring `ovos_plugin_manager.templates.solvers` warning belongs to
  `ovos_yes_no_solver`; it is not caused by these commands.
- `Read the page` remains designed for browser semantic content and clipboard
  fallbacks. Electron applications such as Claude Desktop may not expose their
  rendered response through that path; use the application's read-aloud
  feature or select the text and say `Read selected text`.
- Desktop applications remain detached from `ovos-core.service`, so restarting
  Jarvis does not terminate applications that Jarvis launched.

## Final state

The command layer now provides local, visible control over browser search,
focused text, application windows, Claude Desktop, the isolated Claude agent,
Hermes Desktop, media, lock state and audio mute scope. None of these commands
requires the OVOS conversational model, and none grants arbitrary execution
authority.

