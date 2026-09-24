# Jarvis File Search 0.2.0

Search local **filenames** by voice and open a result from a clickable list.
The skill reads directory entries and filesystem metadata; it does not inspect
document contents, copy files to Hermes or submit filenames to a remote service.

## Install on the OVOS computer

Extract this release. Run from its extracted directory as your normal user:

```bash
~/.venvs/ovos/bin/python install.py --check
~/.venvs/ovos/bin/python install.py
```

The second command installs the skill into the OVOS Python environment,
configures the reviewed `files.search` action in the local Qwen dispatcher,
adds the skill's phrases to the tray Commands tab, and restarts `ovos-core.service`.
Only the File Search edits are applied;
Insert New Line remains owned by Jarvis core. It requires no administrator access.
The installer compares each Qwen and tray GUI file against reviewed snapshots.
It stops **before installing anything** if a file has changed. Use `--no-qwen`
to skip Qwen integration or `--no-gui` to leave the tray GUI alone.

An existing Qwen patch is kept in place. Changed Qwen and GUI files are backed up at
`~/.local/state/jarvis/backups/`. If a restart fails, the installer restores
the dispatcher and GUI files it changed; the skill package may remain at 0.2.0.
The reviewed GUI Insert New Line alignment is recognised and retained when
the Qwen action is already present. Close and reopen the tray Commands tab to
see the installed File Search voice phrases.

Wait until OVOS announces it is ready before testing: Padatious may compile
the updated voice patterns in the background. A slow Qwen response can time
out, but native search phrases still work.

## Voice examples

- “Find Alex”
- “Look in my Documents for Alex”
- “Looking in my Documents for Alex”
- “Looking my Documents for Alex”
- “Can you search my files for Alex documentation?”
- “Find the Hermes documentation”
- “Look for a file” (asks what filename to search)

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
window, even if no file matches. For the route and any errors, run:

```bash
journalctl --user -u ovos-core.service -u ovos-listener.service \
  --since '3 minutes ago' --no-pager -o cat |
rg -i 'raw transcription|parsing utterance|file search found|files.search|qwen router|match call timed out|unavailable'
```

The native intent appears as `jarvis-file-search.local:search.documents`;
Qwen handling appears as `Qwen router: handler_invoked files.search`. Only
the latter depends on Qwen responding inside OVOS's timeout.

Run the included local tests with `python3 -m unittest discover -s tests -v`.
See `COMMANDS.md` for all 45 native voice patterns. The tray shows these
installed patterns in a read-only File Search section. See
`ARCHITECTURE.md` for Qwen, Whisper and Media integration, and
`HISTORY.md` for the changes in this release.
