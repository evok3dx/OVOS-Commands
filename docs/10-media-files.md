# Media and local file search

**VERIFIED in V3 source:** `plugins/ovos-skill-jarvis-media` and
`plugins/jarvis-file-search` are bundled first-party OVOS skill packages. The
installer registers their skill entry points in the same OVOS environment as
Jarvis. The Media pipeline is placed immediately before the Qwen command
pipeline; the file-search skill has native intent templates and a separate
allowlisted `files.search` router action.

| Say | Route | Result and limit |
|---|---|---|
| “Play {title}” or “Put on {title}” | Media title pipeline | Find the first YouTube result with `yt-dlp` and open its video URL in the installed Brave launcher. Search result does not guarantee playable audio. |
| “Pause music”, “next track”, “stop media” | Native Jarvis Media intent | Send only the five approved controls to the Media skill; prefer an active Brave player through MPRIS. Next and previous need a real queue. |
| “Find {filename}”, “Look in my Documents for {query}” | File Search native intent or guarded Qwen action | Search local filenames in Documents, Downloads and Desktop, or Documents alone when requested. Show a local result picker; a file opens only after user selection. No document contents are indexed or sent to a remote model. |

The Control Centre's **Apps & Commands** page embeds the existing Commands
editor. It reads fixed action names from the current Jarvis profile, 45 native
file-search patterns from the installed skill, and seven title examples from
the installed Media package. The variable `{query}` and `{title}` patterns are
read-only. Personal phrases can be added to approved fixed actions, including
New Line, but cannot fabricate a file-search query.

File Search requires `zenity` and `xdg-open`; Media uses `playerctl` and
`yt-dlp`. The installer offers missing system prerequisites at its one-time
administrator boundary, and installs `yt-dlp` in the OVOS virtualenv only when
absent. Existing voice packages and personal settings are preserved. An update
backs up the Jarvis source and records managed package versions for rollback.

**Brain evidence:** the 24 September final archive contains the earlier
integrated Brave media implementation and file-search 0.1.9. The attached
reviewed release packages supply the plugin and file-search 0.2.0. Offline
plugin tests and the V3 phrase/pipeline tests pass; the owner subsequently
confirmed both plugins work. The older snapshot cannot document that later
installation or establish behavior on another computer.

For implementation details see the bundled plugin
[Media package](../plugins/ovos-skill-jarvis-media/pyproject.toml),
[File Search guide](../plugins/jarvis-file-search/README.md), and
[installer](07-installer-updates.md).
The original Media [issue history](../plugins/ovos-skill-jarvis-media/HISTORY.md)
and File Search [release history](../plugins/jarvis-file-search/HISTORY.md)
are retained for context.
