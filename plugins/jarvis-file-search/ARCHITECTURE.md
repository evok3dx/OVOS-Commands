# Integration and design

## File search

Whisper (or another STT plugin) turns speech into text. OVOS first tries the
skill's Padatious patterns for recognised search phrases. The skill searches
configured folders by filename and presents the result list. It reads
filesystem directory entries and metadata only. A selected result opens through
the desktop's default application.

For an unfamiliar phrase, the optional Qwen dispatcher may select the
approved `files.search` action. It receives the **original transcript**, then
extracts a bounded filename query and emits `jarvis.file.search` with `query`
and `documents_only`. The same skill performs the search. Qwen cannot supply a
shell command or read a file through this action. Qwen may time out, so the
native phrases are the reliable path for frequent requests.

## Is adding a plugin to Qwen automatic?

No. OVOS discovers the skill's `opm.skill` entry point, but Qwen has an
explicit action catalogue, candidate filter, prompt and approved dispatcher.
Installing an OVOS skill cannot modify that catalogue automatically. The
0.2.0 installer automates the **reviewed local edit** for this particular
dispatcher version and verifies hashes first. It also adds the skill's phrases
to the tray Commands tab. A changed dispatcher requires a
new review and compatible update. `--no-qwen` skips the edit while keeping
native search available. Whisper needs no file-search patch: the failed
transcript was already correctly recognised.

## How is Media different?

The separate Jarvis Media plugin has its own OVOS pipeline and handles
recognised title requests such as “Play Get Lucky” before the Qwen fallback.
The Media installer places that pipeline before Qwen and integrates fixed
transport actions with the dispatcher. Qwen can select existing approved
play, pause, stop, next and previous actions; that integration was explicitly
configured by the Media installer. The presence of an OVOS plugin alone does
not add an action to Qwen. File Search 0.2.0 changes no Media files.

Qwen's browser YouTube search action is separate: it opens a search prompt.
Spoken title playback uses the Media pipeline. File Search does not turn
Qwen into a general filesystem or browser controller.

## Boundaries

- Direct search and Qwen search call the same bounded filename scanner.
- Documents-only requests use `~/Documents`; other requests use configured
  folders. Missing folders are skipped.
- Hidden files, symlinks and compiled Python files are ignored.
- Query words must all appear in a filename. A Word or PDF file is not parsed.
- The result window replaces its previous instance; a file opens only after
  selection in that window.
- The Qwen integration changes only three reviewed dispatcher source files.
  It does not change Whisper, Media, OVOS settings or unrelated commands.
- Insert New Line belongs to Jarvis core; the File Search installer applies
  only its own action edits and preserves the core command.
- The tray displays the skill's installed voice patterns read-only. Personal
  fixed phrases cannot provide a filename slot, so `files.search` is not
  offered in the personal-phrase action list.
