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

### Standard Notes

When the active profile maps `notes` to Standard Notes:

- `New note`
- `Create a new note`
- `Create new note`
- `Make a new note`
- `Make new note`

Jarvis focuses or opens Standard Notes, verifies that it owns the active
window, and only then sends `Alt+Shift+N`.

- `Search notes` opens the universal Standard Notes search.
- `Search this note` uses focused-document search in the open note.
- `Search this node` is retained as an STT-tolerant pronunciation variant.

### Proton Mail

- `New email`
- `Compose an email`
- `Search mail`
- `Find an email`

Proton actions verify that the configured Mail integration is Proton Mail and
that its window owns focus. Search opens the field before asking for the query.

### Zoom

- Copy a genuine Zoom invitation link.
- Say `Join meeting` or `Join copied Zoom meeting`.

The integration accepts only `zoom.us` and its subdomains, extracts the meeting
number and encoded password locally, and passes a `zoommtg` URI to the locally
registered Zoom handler. Meeting links and passwords are not spoken or
deliberately logged.

### Claude Desktop and Claude agent

Ordinary Claude wording controls the graphical Claude Desktop application:

- `Open Claude`
- `Focus Claude`
- `Message Claude`

`Message Claude` focuses or opens Claude Desktop, verifies that its window owns
focus, then asks what to send and types the response into its chat.

The isolated terminal agent remains explicit:

- `Open Claude agent`
- `Focus Claude agent`
- `Message Claude agent`

This prevents an ordinary request for Claude from being routed to the local
coding and task agent.

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

## Focused editing and field navigation

Examples:

- `Select all`
- `Delete selected text`
- `Clear text` (requires confirmation)
- `Undo` / `Redo`
- `Copy text` / `Cut text` / `Paste text`
- `Save document`
- `Press Tab` / `Next field` / `Next box`
- `Press Shift Tab` / `Previous field` / `Previous box`
- `Search this page` / `Search this document`

Search opens the application's search field first, then asks what to search
for, verifies the original window still owns focus and enters the response.
Terminal uses its compatible copy, select and search shortcuts; unsafe editing
operations are refused there.

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
- `Mute mic` / `Mute microphone`
- `Mute Jarvis` / `Stop Jarvis listening`
- `Stop`
- `Hey Jarvis` while speech is playing to interrupt and begin another command

## Personal command phrases

Choose **Commands…** from the OVOS tray to view approved actions and all their
existing built-in phrases. A personal phrase can be added to the selected
action and activated with **Save & Reload**.

Built-ins are read-only. Personal phrases cannot run arbitrary applications,
hotkeys or shell commands; they can only call actions already implemented and
allowlisted by Jarvis.

## Source of truth

The registered intent inventory is defined in
[`__init__.py`](../ovos_skill_jarvis_dispatcher/__init__.py). Behaviour is
split across:

- [Browser commands](../ovos_skill_jarvis_dispatcher/browser.py)
- [Desktop commands](../ovos_skill_jarvis_dispatcher/desktop.py)
- [Dictation commands](../ovos_skill_jarvis_dispatcher/dictation.py)
- [Agent commands](../ovos_skill_jarvis_dispatcher/agents.py)
- [Controlled follow-ups](../ovos_skill_jarvis_dispatcher/conversation.py)
- [Personal phrase validation](../ovos_skill_jarvis_dispatcher/custom_commands.py)
- [System microphone control](../ovos_skill_jarvis_dispatcher/system_audio.py)
- [Wake-word interruption](../ovos_skill_jarvis_dispatcher/wakeword.py)
- [Focused editing and navigation](../ovos_skill_jarvis_dispatcher/text_editing.py)
- [Application integrations](../ovos_skill_jarvis_dispatcher/integrations/)

Run `python3 scripts/validate_refactor.py` after changing commands or
vocabulary.
