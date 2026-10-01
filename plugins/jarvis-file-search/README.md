# Jarvis File Search 0.3.0

Search local **filenames** by voice and open a result from a clickable list.
The skill reads directory entries and filesystem metadata; it does not inspect
document contents, copy files to Hermes or submit filenames to a remote service.

## Install on the OVOS computer

File Search 0.3.0 is included as a separate plugin in Jarvis V4. Install or
update through the [managed Jarvis installer](../../docs/07-installer-updates.md).
The current tree has no standalone `install.py`; old patch-installer instructions
belong to the historical plugin releases.

Jarvis already owns the reviewed `files.search` action and derives the Control
Centre's read-only phrase list from the installed intent templates. No manual
Qwen or GUI source patch is needed. Wait for Jarvis's readiness indication before
using newly installed intents; Qwen fallback can time out while native patterns
remain available.

## Voice examples

- “Find Alex”
- “Look in my Documents for Alex”
- “Looking in my Documents for Alex”
- “Looking my Documents for Alex”
- “Can you search my files for Alex documentation?”
- “Find the Hermes documentation”
- “Search my files” (asks what file to search for)
- “Search my documents” (asks what document to search for, then searches
  `~/Documents` only)

“My Documents” searches `~/Documents` only. Other searches cover
`~/Documents`, `~/Downloads` and `~/Desktop` by default. An expression like
“Alex documentation” requires both words in the filename. The search says
“Searching” and shows names and folders. Double-click a result or select it
and press **Open**. Another search closes the previous results window. The
file itself is opened only after a user selects it.

## Configure folders

In the installed skill's OVOS settings, you may set:

```json
{
  "folders": ["~/Documents", "~/Downloads"],
  "max_results": 20,
  "max_entries": 50000,
  "timeout_seconds": 8.0
}
```

The exact settings location depends on your OVOS installation. The results
list needs `zenity`, `xdg-open` and a working desktop session. Hidden paths,
symlinks and compiled Python files are skipped. A scan may stop at the entry
or time limit; increase those settings if you need a larger scan.

## Check the installation

Say “Looking in my Documents for Alex”. Expect “Searching” and a results
window, even if no file matches. Use **Maintenance → Recent logs** or the
[service troubleshooting guide](../../docs/troubleshooting.md) for the route and
errors. Native isolation uses system worker units; ordinary installations use
OVOS user services, so select the journal belonging to the current deployment.

The native intent appears as `jarvis-file-search.local:search.documents`;
Qwen handling appears as `Qwen router: handler_invoked files.search`. Only
the latter depends on Qwen responding inside OVOS's timeout.

Run the included local tests with `python3 -m unittest discover -s tests -v`.
See `COMMANDS.md` for the native voice patterns. The tray shows these
installed patterns in a read-only File Search section. See
`ARCHITECTURE.md` for Qwen, Whisper and Media integration, and
`HISTORY.md` for the changes in this release.
