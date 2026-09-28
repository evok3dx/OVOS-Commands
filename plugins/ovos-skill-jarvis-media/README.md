# Jarvis Media skill 0.3.1

This source package is bundled with Jarvis V3. Use the main
[`scripts/install.sh`](../../scripts/install.sh) for a managed install, upgrade
or rollback. The separate installer described in the original package history
is retained there as historical context; it is not part of this directory.

The skill accepts a bounded `play {title}` request, finds one YouTube video ID
through `yt-dlp`, and opens a fixed watch URL in enabled Brave. If Brave is
unavailable or cannot be launched, enabled Firefox is the bounded fallback.
After accepting a real title, it says “Let me spin that track.” once, waits for
that short acknowledgement, then starts the bounded lookup without an added
pre-search pause. A validated result waits 1.5 seconds before Brave opens.
Empty input does not enter this path. A generic “play music” request is handled
by the dispatcher as a bounded two-turn interaction: Jarvis asks what to play,
then passes only that one reply to this plugin as title data. Jarvis does not
retry provider blocks or try to imitate human browsing.
It also handles five approved MPRIS transport actions. The OVOS Media pipeline
runs before Qwen; only those fixed actions can be selected by Jarvis's router.
Real YouTube playback and spoken controls require checks on the target desktop.
If Brave no longer exposes a resumable media session, a spoken resume now says
“Open the music tab once” instead of failing silently. Brave's documented
Memory Saver exception remains the preventive fix; Jarvis does not click a
site inactivity confirmation or revive a discarded tab blindly.

See [Media and file search](../../docs/10-media-files.md) for commands and
limits, and [history](HISTORY.md) for the failures that shaped this package.
