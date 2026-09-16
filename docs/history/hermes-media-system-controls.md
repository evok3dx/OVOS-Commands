# Hermes composer and system controls

> Historical record. Use `scripts/install.sh` for the current deployment.

This package adds focused keyboard, Cinnamon media and verified Hermes Desktop
controls to the current modular Jarvis dispatcher. It does not change Git.

## Install

```bash
cd ~/Downloads/OVOS-caps-lock-persistence-v12
bash scripts/install-hermes-composer-system-controls.sh
```

The installer validates the full package, checks required desktop commands,
backs up the live dispatcher, installs only the changed modules and restarts
Jarvis once. Running it twice replaces the same modules; it does not duplicate
commands.

## Universal keyboard

- `Press Enter`
- `Press Return`
- `Press Send`
- `Caps Lock on`
- `Caps Lock off`

Caps Lock reads the current X11 state before acting, so repeated on/off commands
cannot accidentally reverse it. Its lock-key event deliberately bypasses the
normal modifier-clearing helper so Cinnamon keeps the requested state.

## Cinnamon media

- `Play media` / `Play music` / `Resume playback`
- `Pause media` / `Pause music` / `Pause playback`
- `Stop media` / `Stop playback` / `Stop playing`
- `Next track` / `Next song` / `Skip track`
- `Previous track` / `Previous song` / `Back track`

Media actions use `playerctl` and control the active MPRIS player used by the
Cinnamon sound controls. Bare `stop`, `play` and `pause` were deliberately not
registered because they collide with Jarvis conversation and dictation flows.

## Hermes Desktop

- `Focus Hermes composer`
- `Open Hermes model picker`
- `New line in Hermes`
- `Queue Hermes message`
- `Send next Hermes message`
- `Open Hermes commands`
- `Reference file in Hermes`
- `Cancel Hermes run`
- `Message Hermes` / `Ask Hermes` / `Tell Hermes`
- `Write to Hermes` / `Type into Hermes` / `Talk to Hermes`

Every Hermes action opens or focuses Hermes, verifies its window class and only
then sends the documented shortcut. Direct messaging clears the composer, asks
what to send, types the answer and presses Enter without repeating it aloud.
Profile switching and the ambiguous voice toggle shown in Hermes help were
deliberately left out.

All actions and their complete phrase variations appear in the OVOS tray
command editor, where additional personal phrases can be attached to these
approved actions.

Observed Whisper forms `Hermas` and `Omos` are restricted aliases for the
Hermes target, so phrases such as `Message Hermas` still use the same verified
messaging flow. The broader transcription `from me` is deliberately excluded.

Validated baseline: 20 Python modules, 88 intents, 1,259 built-in vocabulary
registrations and three deployment profiles.
