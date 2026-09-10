# OVOS Commands

Private OVOS Jarvis voice-control system.

This repository contains the custom Jarvis dispatcher and, after packaging,
its allowlisted desktop helpers, configuration examples, runtime patches,
verification tools, rollback tools, and implementation documentation.

## Known-good baseline

The initial commit preserves the tested monolithic dispatcher before its
behaviour-preserving modular refactor.

Supported wake phrase: `Hey Jarvis`.

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

## OVOS tray indicator

Install the independent Cinnamon/GTK status indicator with:

```bash
bash scripts/install-ovos-tray.sh
```

The shield is green when the three OVOS services and Jarvis dispatcher are
ready, amber while starting, red on failure and grey when stopped. Its menu
provides core restart, full restart, start, stop and recent logs. It polls
local systemd state every three seconds and does not load any AI models.
