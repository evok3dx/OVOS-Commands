# Jarvis command reference

The wake phrase is `Hey Jarvis`. Commands are handled locally by the
dispatcher and do not require Ollama or Qwen.

This is a practical command index. Pronunciation variants and recognition
corrections are maintained centrally in
[`vocabulary.py`](../ovos_skill_jarvis_dispatcher/vocabulary.py).

## Desktop applications

Supported applications include Brave, Firefox, Signal, Zoom, Terminal,
Standard Notes, ONLYOFFICE, Claude Desktop, Proton Mail and Proton Calendar.

Examples:

- `Open Firefox`
- `Show Standard Notes`
- `Focus Proton Mail`
- `Minimise Zoom`
- `Close Signal`

Open, launch, start, focus, show, switch, minimise, hide, close, quit and exit
variants are supported where applicable.

## Browser search and navigation

Examples:

- `Search Firefox`
- `Search Brave`
- `Scroll down`
- `Page up`
- `Go to the top`
- `Go back`
- `Go forward`
- `Open a new tab`
- `Close tab`
- `Refresh the page`
- `Focus the address bar`

Search commands ask a controlled follow-up question for the search terms.

## Reading

Examples:

- `Read the page`
- `Read the full page`
- `Read selected text`
- `Read window`
- `Read it back`
- `Read the latest response`
- `Read the Codex response`
- `Read the Claude response`

`Read the page` prefers the main article or main-content region and safely
falls back to copied page text. `Read the full page` deliberately includes
the complete page.

## Dictation and typing

Examples:

- `Start writing`
- `Pause writing`
- `Continue writing`
- `Stop writing`
- `Write this`
- `Type the following`

Speech Note performs dictation and reading while the dispatcher controls its
allowlisted actions.

## Window control

Examples:

- `Close this window`
- `Minimise window`
- `Maximise window`
- `Restore window`
- `Unmaximise window`

The focused-window helper refuses to control the desktop or Cinnamon panel.

## Codex and Claude agents

Examples:

- `Open Codex agent`
- `Focus Claude agent`
- `Minimise Codex`
- `Close Claude`
- `Message Codex`
- `Talk to Claude`
- `Search the web`

Agent messages pass through an allowlisted helper. It validates the target,
message size and expected tmux process before sending anything.

## Other commands

Examples:

- `Read today's date`
- `Stop`
- `Hey Jarvis` while speech is playing to interrupt and begin another command

## Source of truth

The registered intent inventory is defined in
[`__init__.py`](../ovos_skill_jarvis_dispatcher/__init__.py). Behaviour is
split across:

- [Browser commands](../ovos_skill_jarvis_dispatcher/browser.py)
- [Desktop commands](../ovos_skill_jarvis_dispatcher/desktop.py)
- [Dictation commands](../ovos_skill_jarvis_dispatcher/dictation.py)
- [Agent commands](../ovos_skill_jarvis_dispatcher/agents.py)
- [Controlled follow-ups](../ovos_skill_jarvis_dispatcher/conversation.py)
- [Wake-word interruption](../ovos_skill_jarvis_dispatcher/wakeword.py)

Run `python3 scripts/validate_refactor.py` after changing commands or
vocabulary.
