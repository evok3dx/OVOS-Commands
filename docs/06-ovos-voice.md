# OVOS voice and media on Brain

This page records the **24 September 2026 Brain snapshot** from the supplied
local progress notes and raw audio log. These versions describe an existing
working installation. They are not new-machine installer pins, and V3 updates
do not replace installed OVOS packages, voice models or personal configuration.

| Component | Reported Brain version or state |
|---|---|
| Core, Workshop, plugin manager | `3.7.0a1`, `9.8.7a1`, `2.12.4a1` |
| Audio, Dinkum listener | `2.2.8a1`, `0.10.5a1` |
| Silero VAD, PhōnNX/Bella | `0.1.3a2`, `1.93.0a1` |
| Scriptconv, ONNX Runtime, NumPy | `0.0.4a31`, `1.30.0`, `2.4.6` |
| Faster Whisper | Existing `small.en`; reviewed dynamic app-name prompt active on Brain |
| Local routing | Existing Ollama with reviewed Qwen 4B instruct; V3 setup requires the model on other PCs and asks before downloading it |

`compatibility.json` and `scripts/doctor.py` recognise the reported Brain alpha
versions. A separate dependency metadata warning concerning OpenWakeWord and
NumPy 2 remains visible; it is not a reason to downgrade the working voice
stack. Fresh installations still use the distinct reviewed baseline described
in [installer and updates](07-installer-updates.md).

## Media status

The Brain retained `ovos-audio` with Common Play/OCP and VLC. The standalone
`ovos-media` daemon was trialled and rolled back. The reported modern providers
included YouTube Music `0.0.1a3`, PyRadios `0.0.1a5`, SomaFM `0.0.1a5`, News
`0.0.1a6` and Local `0.0.1a5`; VLC's Python plugin was `0.2.1a1`. A successful
YouTube Music song and spoken stop were heard on Brain. Later requests failed
provider timeouts and Google bot checks, so playback remains best effort. News
was disabled in the Brain's effective media routing after it scored unrelated
music searches. Do not turn it on implicitly during a Jarvis upgrade.

**Open failure:** the supplied 24 September `ovos-audio` log shows two
`NPR News Now` requests rejected by `ovos_plugin_common_play.ocp.player.play()`
at 01:47:14 and 01:49:53. Each rejection caused the spoken `skill.error`.
At 01:46:44 a VLC callback tried to call `ocp_stop` on `None`; at 01:50:07
Common Play timed out after 300 seconds. The excerpt establishes the failure
path, but does not show who requeued the NPR item. The Brain's installed media
source and effective queue settings need inspection before a fix can be
claimed. The supplied stack traces name Common Play and VLC; they do not
establish Qwen or tray polling as the source of the repeated request.

The Brain notes also record local compatibility edits for the older audio
backend's `meta` field and for the YouTube extractor's Node and audio format
selection. They were made inside installed third-party packages; this
repository does not currently manage or reapply them. An upgrade that replaces
those packages needs its own exact-source check and reversible patch. The
reviewed [Whisper app-name patch](../extras/whisper-hints/README.md)
similarly refuses to modify an unknown installed plugin revision.

For the full chronology, retain the two supplied local progress notes and
chat exports with the machine records. This page records only release-relevant
verified state; [the living audit](v2.4-audit.md) tracks what remains open.
