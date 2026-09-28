# Listener cue and volume guard

`ovos-dinkum-listener 0.10.5a1` normally lowers playback before requesting the
listening cue and can begin accepting microphone audio from the WAV's nominal
duration. That duration does not include command-line playback padding. A
fixed-delay Jarvis experiment consequently lowered a laptop's physical sink
while the cue stream was still active.

This dependency-free exact-source patch leaves Dinkum's upstream microphone
timing intact. The audio service's existing sound-completion response controls
only when background playback is lowered. A delayed response therefore cannot
clip the start of a prompted follow-up. A three-second missing-response fallback
still bounds volume handling; normal record-end restoration and a 15-second
restoration fail-safe remain.

Before each activation it also requests the current sink volume with a bounded
0.5-second query. That per-command value is the restore target. If no valid
response arrives, recording continues without ducking, preventing a stale
service-start value from leaving playback at the wrong level.

The installer accepts the reviewed upstream source and known Jarvis patches,
which converge to the same service guard. If the rejected confirmation gate is
present, it restores the reviewed upstream voice loop. It rejects unknown
source layouts, privately backs up both files, compiles both outputs before
writing and opens no port.

Fresh Jarvis setup recommends a 20% background-audio level and enables
Faster-Whisper's built-in VAD filter. Upgrades migrate only the exact earlier
Jarvis defaults. Explicit custom volume and VAD values remain untouched.
