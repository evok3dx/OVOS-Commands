# Jarvis Media skill

This source package is bundled with Jarvis V3. Use the main
[`scripts/install.sh`](../../scripts/install.sh) for a managed install, upgrade
or rollback. The separate installer described in the original package history
is retained there as historical context; it is not part of this directory.

The skill accepts a bounded `play {title}` request, finds one YouTube video ID
through `yt-dlp`, and opens a fixed watch URL in the configured Brave browser.
It also handles five approved MPRIS transport actions. The OVOS Media pipeline
runs before Qwen; only those fixed actions can be selected by Jarvis's router.
Real YouTube playback and spoken controls require checks on the target desktop.

See [Media and file search](../../docs/10-media-files.md) for commands and
limits, and [history](HISTORY.md) for the failures that shaped this package.
