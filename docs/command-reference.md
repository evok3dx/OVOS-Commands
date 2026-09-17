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

Jarvis app-specific actions first focus a reviewed X11 window through
`jarvis-app-window`, then verify focus before sending a shortcut. If an app
opens normally but an action such as `New note` fails, test window discovery
before changing the shortcut. See
[`window-focus-and-app-integration.md`](window-focus-and-app-integration.md).

### Standard Notes

When the active capabilities map `notes` to Standard Notes:

- `New note`
- `Create a new note`
- `Create new note`
- `Make a new note`
- `Make new note`

Jarvis focuses or opens Standard Notes, verifies that it owns the active
window, and only then sends `Alt+Shift+N`.

- `Search notes` opens the universal Standard Notes search with
  `Ctrl+Shift+Colon`.
- `Search this note` uses focused-document search in the open note.
- `Search this node` is retained as an STT-tolerant pronunciation variant.

The helper accepts several reviewed Standard Notes X11 class spellings across
packaging variants. Those alternatives are matched independently; the `|`
separator is not part of a literal class name.

### Proton Mail

`Open mail` opens the operating system's default mail application. Branded
commands such as `Open Proton Mail` explicitly select Proton Mail.

- `New email`
- `Compose an email`
- `Search mail`
- `Find an email`

Proton actions verify that the configured Mail integration is Proton Mail and
that its window owns focus. `New email` sends `N`. Search sends `/`, asks for
the query, types it into the verified Proton Mail window, then sends `Enter`.

Proton uses the same generic app-focus helper as Standard Notes but retains its
own reviewed window signature. A Standard Notes-specific failure does not by
itself prove Proton Mail is broken.

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

Speech Note is optional. Run `jarvis-speechnote-setup` or select **Speech Note
setup** in the Jarvis tray to install it for the current user, inspect its
active models, or open its model browser. Existing Speech Note settings are
never overwritten.

## Window control

Examples:

- `Close this window`
- `Minimise window`
- `Maximise window`
- `Restore window`
