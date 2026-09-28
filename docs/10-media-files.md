# Media and local file search

**VERIFIED in V3 source:** `plugins/ovos-skill-jarvis-media` and
`plugins/jarvis-file-search` are bundled first-party OVOS skill packages. The
installer registers their skill entry points in the same OVOS environment as
Jarvis. The deliberate-title Media pipeline runs immediately after native
Adapt commands and before Padatious and Qwen; the file-search skill has native
intent templates and a separate
allowlisted `files.search` router action.

| Say | Route | Result and limit |
|---|---|---|
| “Play {title}” or “Put on {title}” | Media title pipeline | Find the first YouTube result with `yt-dlp` and open its video URL in the installed Brave launcher. Search result does not guarantee playable audio. |
| “Play music” → “What shall I play?” | Native two-turn Media prompt | Collect one bounded title, then send it as data to the same Media event. Silence retries once; cancel exits without a search. |
| A natural title-only request approved by Qwen | Guarded Qwen Media action | Pass only the extracted title to the same Media event. Questions, negation, compound desktop instructions, generic music requests and one-word guesses are rejected. |
| “Pause music”, “stop the music”, “resume the music”, “start the song again”, “next track”, “stop media” | Native Jarvis Media intent | Music/song/track stop wording pauses the active MPRIS player so browser playback can resume; explicit `stop media/playback/video` performs a true stop. Accent variants `pose/poze music` require the full phrase. Next and previous need a real queue. |
| “Find {filename}”, “Look in my Documents for {query}” | File Search native intent or guarded Qwen action | Search local filenames in Documents, Downloads and Desktop, or Documents alone when requested. Show a local result picker; a file opens only after user selection. No document contents are indexed or sent to a remote model. |

The Control Centre's **Apps & Commands** page embeds the existing Commands
editor. It reads fixed action names from the current Jarvis profile, 45 native
file-search patterns from the installed skill, and eight title examples from
the installed Media package. The variable `{query}` and `{title}` patterns are
read-only. Personal phrases can be added to approved fixed actions, including
New Line, but cannot fabricate a file-search query.

File Search requires `zenity` and `xdg-open`; Media uses `playerctl` and
`yt-dlp`. The installer offers missing system prerequisites at its one-time
administrator boundary, and installs `yt-dlp` in the OVOS virtualenv only when
absent. Existing voice packages and personal settings are preserved. An update
backs up the Jarvis source and records managed package versions for rollback.

Browser searches and Media's YouTube title lookup use one shared local pacing
guard: one reservation at a time and at least 12 seconds between submissions.
Browser and visible YouTube searches retain their short pre-submit pacing. A
Media title request says “Let me spin that track” immediately, starts its
bounded lookup after the acknowledgement without an artificial pre-search
pause, then waits 1.5 seconds after a valid result before the browser opens.
Enabled Brave is first and enabled Firefox is the bounded fallback. Visible Brave, Firefox and
YouTube searches type the query at 55 ms per character, pause briefly, recheck
the focused window, and only then press Enter. Media title lookup remains a
bounded background lookup before opening its first result in the selected
browser. Jarvis does not automatically
retry blocked requests, rotate networks, bypass a CAPTCHA or imitate browsing
activity. A local cooldown asks the user to wait; an explicit YouTube/429 bot
challenge is reported and left for the user. Local filename search is not
delayed because it never contacts a provider.

**reference system evidence:** the 24 September final archive contains the earlier
integrated Brave media implementation and file-search 0.1.9. The attached
reviewed release packages supply Media 0.3.0 and File Search 0.3.0. Offline
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
