# Jarvis command reference

The wake phrase is `Hey Jarvis`. Commands are handled locally by the
dispatcher and do not require Ollama or Qwen.

This is a practical command index. Pronunciation variants and recognition
corrections are maintained centrally in
[`vocabulary.py`](../ovos_skill_jarvis_dispatcher/vocabulary.py).

## Desktop applications

Supported applications include Brave, Firefox, Signal, Zoom, Terminal,
Standard Notes, ONLYOFFICE, Claude Desktop, ChatGPT Desktop, Hermes Desktop,
the default Mail application, Proton Mail and Proton Calendar when detected
and enabled.

Examples:

- `Open Firefox`
- `Show Standard Notes`
- `Focus Proton Mail`
- `Minimise Zoom`
- `Maximise ChatGPT`
- `Close Signal`

Open, launch, start, focus, show, switch, minimise, maximise, hide, close, quit
and exit variants are supported where applicable.

### Standard Notes

When the active capabilities map `notes` to Standard Notes:

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

`Open mail` opens the operating system's default mail application. Branded
commands such as `Open Proton Mail` explicitly select Proton Mail.

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

### Claude Desktop and ChatGPT Desktop

Claude wording controls the ordinary graphical chat application:

- `Open Claude`
- `Focus Claude`
- `Message Claude`

`Message Claude` focuses or opens Claude Desktop, verifies that its window owns
focus, then asks what to send and types the response into its chat.

- `New Claude chat`: open a fresh Claude Desktop conversation.
- `Open Claude website` or `Open Claude online`: open `claude.ai` in the
  operating system's default browser.

ChatGPT accepts the same application verbs with `ChatGPT`, `GPT`, `Chat G P T`
or `chat`:

- `Open ChatGPT`
- `Focus GPT`
- `Minimise chat`
- `Maximise ChatGPT`
- `Close GPT`

Website wording remains explicit:

- `Open the ChatGPT website`
- `Open GPT website`
- `Open ChatGPT online`

Recognition-tolerant `cloud`, `clawed` and `called` forms are registered for
Claude. Jarvis does not open or operate Claude Code, Cowork, ChatGPT Codex or
Work. Custom agent infrastructure is not part of normal setup or vocabulary.

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

### YouTube

- `Search YouTube`
- `YouTube search`
- `Open YouTube Shorts`
- `Go to YouTube reels`

If the visible browser tab is already YouTube, search focuses that tab's search
field instead of opening another page. Otherwise Jarvis opens YouTube in the
preferred supported browser. With several YouTube tabs open, Jarvis uses only
the currently visible tab and does not guess which background tab is intended.

Commands to play the first or second result are deliberately excluded. Search
results and keyboard focus can change, so automatic selection would not be
reliable enough for the allowlisted command layer.

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

## Other commands

Examples:

- `Read today's date`
- `Mute mic` / `Mute microphone`
- `Mute system` / `Mute everything`
- `Mute Jarvis` / `Stop Jarvis listening`
- `Stop`
- `Hey Jarvis` while speech is playing to interrupt and begin another command

## Keyboard, media and Hermes

Universal focused-app controls:

- `Press Enter` / `Press Return` / `Press Send`
- `Caps Lock on` / `Caps Lock off`

Caps Lock is state-aware: saying the requested state twice does not toggle it
back. Full-system mute affects both speaker and microphone and must be reversed
from the keyboard or Cinnamon sound settings.

Cinnamon media controls:

- `Play media` / `Resume playback`
- `Pause media` / `Pause playback`
- `Stop media` / `Stop playback`
- `Next track` / `Skip track`
- `Previous track` / `Back track`

Hermes Desktop controls:

- `Open Hermes` / `Focus Hermes` / `Minimise Hermes` / `Close Hermes`

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

Hermes is focused and verified before its shortcut is sent. Direct message
commands focus the composer, clear any existing text, ask what to send, verify
that the same Hermes window still owns focus, type the response and press Enter.
They do not repeat the dictated content or require a second confirmation.
Recognition-tolerant `Hermas` and `Omos` forms are included because they were
observed in Whisper output; the broad phrase `from me` is deliberately not an
alias. Media uses state-specific `playerctl` actions; bare `play`, `pause` and
`stop` are not registered because they would collide with other voice flows.

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
- [Controlled follow-ups](../ovos_skill_jarvis_dispatcher/conversation.py)
- [Personal phrase validation](../ovos_skill_jarvis_dispatcher/custom_commands.py)
- [System microphone control](../ovos_skill_jarvis_dispatcher/system_audio.py)
- [Keyboard and media controls](../ovos_skill_jarvis_dispatcher/system_controls.py)
- [Wake-word interruption](../ovos_skill_jarvis_dispatcher/wakeword.py)
- [Focused editing and navigation](../ovos_skill_jarvis_dispatcher/text_editing.py)
- [Application integrations](../ovos_skill_jarvis_dispatcher/integrations/)

Run `python3 scripts/validate_refactor.py` after changing commands or
vocabulary.
