# Jarvis command reference

The default wake phrase is `Hey Jarvis`. Fixed phrases run locally. V4 also has a
restricted local Qwen fallback for natural requests.

This is a practical command index. Pronunciation variants and recognition
corrections are maintained centrally in
[`vocabulary.py`](../ovos_skill_jarvis_dispatcher/vocabulary.py).

## Desktop applications

Supported applications include Brave, Firefox, Signal, Zoom, Terminal,
Standard Notes, ONLYOFFICE, Claude Desktop, ChatGPT Desktop, Hermes Desktop,
the default Mail application, Proton Mail, Proton Calendar and the system
Calendar when detected
and enabled.

Examples:

- `Open Firefox`
- `Open browser` (uses the preferred enabled browser)
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

`Message Claude` opens a fresh Claude Desktop chat and checks focus. Jarvis says
“Ready”; dictate one message and it sends it, then says “Message sent.”
`Message Claude agent` and `Message Codex agent` capture and read back the
message, then require **Send it** before submitting through the private
allowlisted helper. **Cancel**, timeout or an unrelated native command clears
the pending message. A confirmation is single-use; repeating it sends nothing.

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
reliable enough for that browser search command. The separate Media plugin
handles deliberate `Play {title}` requests with one bounded YouTube lookup.

## Media and local files

- `Play {title}` or `Put on {title}` searches for one YouTube video and opens
  the result in enabled Brave, with enabled Firefox as the fallback. Replace
  `{title}` with an actual song or video name.
- Longer alternatives include `Listen to {title}`, `Can you play {title}?`
  and `Could you please put on {title}?`. These use the same deliberate-title
  route and can help when speech recognition mishears the short word `Play`.
- `Play music` asks “What shall I play?”; say one song, artist or video title.
  The direct `Play {title}` form remains available.
- `Pause music`, `Pose music`, `Poze music` and `Stop the music` pause a
  compatible MPRIS player without discarding its current browser track.
- `Resume the music`, `Start the song` and `Start the song again` resume that
  paused player. `Stop media` remains the explicit full-stop command.
- `Next song` and `Previous track` require a real player queue.
- `Find {filename}` or `Look in my Documents for {query}` searches local
  filenames and shows a picker. Nothing opens until you select a result.
- `Search my files` or `Search my documents` asks one local follow-up when no
  query was spoken. The latter searches `~/Documents` only.

The Commands page shows the current installed patterns. File and title
templates are read-only; [details and limits](10-media-files.md).

Provider-backed browser and YouTube searches are submitted one at a time with
the conservative pacing described in the linked guide. Jarvis does not retry
provider blocks automatically. Local filename search and other commands are
not delayed.
Music acknowledges before lookup, then waits three seconds after finding a
result before opening it. Another request can open a new tab while an earlier
tab keeps playing; pause or close the earlier playback explicitly.

## Reading

Examples:

- `Read this`
- `Read the page`
- `Read the full page`
- `Read selected text`
- `Speak selected text`
- `Speak highlighted text`
- `Speak selected text at 2x`
- `Read this at double speed`
- `Read this at 2x`
- `Read this page at double speed`
- `Read this page at 2x`
- `Read window`
- `Read it back`
- `Read the latest response`
- `Read the Codex response`
- `Read the Claude response`

If speech recognition hears `Write this` when you intend `Read this`, use
`Speak selected text` in V4. It is a separate native reading phrase; the
existing writing command keeps its behaviour. Correctly transcribed reading
and writing stay distinct. Short-phrase acoustic accuracy still needs live
testing; Jarvis cannot recover the intended word from a wrong transcript alone.
Selected-text reading clears the temporary clipboard handoff and does not
restore its previous contents.

`Read the page` prefers the main article or main-content region and safely
falls back to copied page text. `Read the full page` deliberately includes
the complete page.

## Dictation and typing

Examples:

- `Start writing`
- `Pause writing`
- `Continue writing`
- `Stop writing`
- `Press space`
- `Write this`
- `Type the following`

Speech Note performs dictation and reading while the dispatcher controls its
allowlisted actions.
Generic writing and submission refuse terminal windows. Opening Terminal is a
separate action and does not grant permission to type commands into it.

Stopping continuous dictation keeps Speech Note's final full stop and adds one
trailing space, ready for the next sentence. This also applies when the wake
phrase has already paused Speech Note before `Stop writing` reaches Jarvis.
Jarvis rechecks the focused window before inserting it. `Press space` inserts
a single space separately without submitting the focused field.

One-shot writing types the captured words without Enter and removes only
Whisper's automatic final period. For a period in the same capture, say the
more distinctive phrase `insert a period` at the end. If Whisper has already
converted spoken “full stop” into ordinary punctuation, Jarvis cannot tell it
apart from automatic punctuation; use the separate `Full stop` command then.

Speech Note is optional. Open **Jarvis → Voice → Open Speech Note and setup
guide…** to inspect or open it, or to approve a per-user installation when it is
absent. The same bounded helper is available as `jarvis-speechnote-setup` in a
terminal. Existing Speech Note models, voices, settings and transformation
rules are preserved.

For continuous dictation, enable Speech Note's Rules feature and add one STT
**Replace (Regular expression)** rule. Use
`\bhey\s*,?\s*jarvis\b\s*\.?\s*` as the case-insensitive pattern and one space
as its replacement. This covers `Hey Jarvis` and `Hey, Jarvis`, with or without
a final full stop. If the wake phrase changes, update this rule too. Jarvis
shows the step but does not rewrite Speech Note's rule list: its public
integration API cannot merge rules safely.

## Hermes messages

`Message Hermes` focuses Hermes Desktop, starts a fresh chat with Ctrl+N, then
focuses the composer. Jarvis says “Ready”; dictate one message and it sends it,
then says “Message sent.” Say `cancel` to stop. An empty response or a native
media command is not sent as a message. If focus changes before submission,
Jarvis cancels the send. Other Hermes composer commands keep their shortcuts.

## Window control

Examples:

- `Close this window`
- `Minimise window`
- `Maximise window`
- `Restore window`
- `Minimize this app` or `Minimise this application`
- `Maximize this application` or `Maximise this app`
- `Restore this app`, `Restore this application` or `Unmaximise this app`
- `Show desktop`
- `Go to desktop`
- `Minimize all`
- `Minimize everything`, `Minimise everything` or `Hide everything`

Show-desktop and minimise-all phrases use Linux Mint's fixed `Super+D` shortcut. They do
not minimize windows one by one or accept a model-generated key sequence.
Individual window actions target the verified focused window.


### Keyboard actions

- "New line", "newline", "insert new line" and "add a new line" use the
  dedicated New Line action. They send Shift+Return to the verified focused
  window without submitting a message.
- "Full stop" or "period" inserts one literal `.` in the focused field without
  pressing Enter. "Insert a full stop" and "add a period" work too.
- "Press Enter", "Send it", "Send the message" and "Submit" send Return to
  the verified focused window and may submit.
- "Press space" sends one Space to the verified focused window.
- "Press Escape", "press Esc", "hit Escape" and "Escape key" send Escape
  to the focused application, for example to dismiss a search field or dialog
  when the application supports that key. This is separate from browser Back.
- Explicit Hermes new-line commands retain their existing Shift+Return action.
