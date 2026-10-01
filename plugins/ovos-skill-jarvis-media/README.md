# Jarvis Media skill 0.3.5

This source package is included in Jarvis 4.0.0. Use the main
[`scripts/install.sh`](../../scripts/install.sh) for a managed install, upgrade
or rollback. The separate installer described in the original package history
is retained there as historical context; it is not part of this directory.

The skill accepts a bounded `play {title}` request, finds one YouTube video ID
through `yt-dlp`, and opens a fixed watch URL in enabled Brave. If Brave is
unavailable or cannot be launched, enabled Firefox is the bounded fallback.
After accepting a real title, it queues “Let me spin that track.” once before
starting the lookup worker, without waiting for speech to finish. A validated
result waits three seconds before Brave opens, regardless of lookup duration.
Stop or a replacement title cancels that wait. Provider/network
response time remains variable; no playback-time guarantee is made.
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
site inactivity confirmation or revive a discarded tab blindly. Browser/site
settings cannot guarantee that an idle media session stays resumable.

See [Media and file search](../../docs/10-media-files.md) for commands and
limits, and [history](HISTORY.md) for the failures that shaped this package.

V4 Media 0.3.5 supports a separately isolated helper over the existing local
bus. Direct titles require actual helper readiness and respect the owner's
original disabled-skill choice. Qwen remains available for semantic fallback.
The shared 11-second gap and 0.5–1 second pre-delay limit bursts. A pending title
acknowledges once, waits cancellably and is replaced by a newer title; Stop
cancels it. Provider errors are never retried automatically. Timings do not
guarantee avoidance of provider alerts.

Remote matches carry the fixed Media owner in match data while leaving the
unloaded local skill inactive. The framework completion carries the fixed
intent name so accepted requests do not leave a false five-minute watchdog.

Opening a new result does not close or stop an earlier music tab. Concurrent
playback is a known follow-up; pause/close the earlier tab explicitly. Longer
`Put on {title}` wording uses the existing deliberate-title route.
