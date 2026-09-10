# OVOS Commands

Private OVOS Jarvis voice-control system.

This repository contains the custom Jarvis dispatcher and, after packaging,
its allowlisted desktop helpers, configuration examples, runtime patches,
verification tools, rollback tools, and implementation documentation.

## Known-good baseline

The initial commit preserves the tested monolithic dispatcher before its
behaviour-preserving modular refactor.

Supported wake phrase: `Hey Jarvis`.

## System architecture

Jarvis is divided into independent layers so an optional component can fail
without taking down direct voice control:

- Wake-word detection uses OpenWakeWord.
- Speech recognition uses Faster Whisper.
- Spoken output uses Kokoro through Phoonnx.
- The modular dispatcher handles browser, desktop, dictation, agent and
  multi-step voice commands.
- OVOS Persona and Ollama provide optional general conversation.

The core command system does not require Qwen, Ollama or another language
model. The dispatcher file named `conversation.py` handles controlled command
follow-ups and remains part of the core system.

For the command-only profile, optional conversation setup and model guidance
for different hardware, see
[Optional local conversation add-on](docs/conversation-addon.md).

## Browser reading

`Read the page` extracts the main `<main>` or `<article>` content from the
HTML clipboard data supplied by Firefox or Brave. If semantic extraction is
not available, it safely falls back to all copied page text. `Read the full
page` deliberately reads the complete browser selection, while `Read selected
text` remains unchanged.

## Runtime resilience

Multi-turn conversation failures are contained inside `ConversationMixin`.
An unexpected exception clears the temporary conversation state and leaves
unrelated browser, desktop, dictation and agent commands available. Syntax or
import failures can still prevent the combined skill from loading; the tray
indicator reports that startup state so it can be restarted or investigated.

Optional changes to installed OVOS packages are stored as separate,
version-checked patches. The patch tool tests each one independently, skips
incompatible changes and creates a rollback copy before applying anything.

The complete layout, security boundaries, preserved services and recovery
procedure are documented in [Recovery infrastructure](recovery/README.md).

## OVOS tray indicator

Install the independent Cinnamon/GTK status indicator with:

```bash
bash scripts/install-ovos-tray.sh
```

The shield is green when the three OVOS services and Jarvis dispatcher are
ready, amber while starting, red on failure and grey when stopped. Its menu
uses plain-language labels: Restart Commands reloads the core and dispatcher,
while Restart Voice System also reloads the listener and wake word. It also
provides start, stop and recent-log actions. It polls local systemd state every
three seconds and does not load any AI models.

## Jarvis microphone indicator

Install the separate microphone status and control icon with:

```bash
bash scripts/install-jarvis-mic-indicator.sh
```

The microphone icon is green while `ovos-listener` is active and red while it
is stopped. Clicking it toggles only the listener, which disables or restores
wake-word and push-to-command input without stopping the rest of OVOS. A file
lock prevents duplicate indicator processes. The installer validates Python,
shell and SVG sources, generates a portable autostart entry, backs up changed
live files and restarts the indicator.
