# OVOS voice stack

This page records the voice-stack boundary for V4. It contains
portable behaviour and reviewed versions, not workstation logs or private
machine configuration.

## Reviewed local stack

| Component | Reviewed state |
|---|---|
| OVOS Core / Workshop / plugin manager | `3.7.0a1` / `9.8.7a1` / `2.12.4a1` |
| Audio / Dinkum listener | `2.2.8a1` / `0.10.5a1` |
| Faster-Whisper | `small.en`, local CPU int8 baseline |
| VAD | Silero `0.1.3a2` |
| Speech output | phoonnx `1.93.0a1`, reviewed Bella voice |
| Wake word | OpenWakeWord ONNX, explicit Hey Jarvis model |
| NumPy | `2.4.6`; ONNX-only downstream wake plugin, zero dependency exemptions |
| Natural-language fallback | local Qwen 4B instruct through Ollama |

The complete package set and exact hashes live in `compatibility.json` and
`voice/reviewed-stack.json`. The installer stages this set in a clean
virtualenv, validates entry points and launchers, then switches atomically.
Existing models and machine configuration remain outside that switch.

## OpenWakeWord review, 27 September 2026

The upstream `openWakeWord` stable release remains `0.6.0`, already the engine
pin in `compatibility.json`. The stable OVOS plugin release is `0.4.1`; the
reviewed stack uses the later tested `0.4.5a2` build with an explicit ONNX
model path. Upstream continues to document ONNX support, so no demonstrably
better replacement was adopted for 3.6.

Sources: [openWakeWord releases](https://github.com/dscripka/openWakeWord/releases),
[openWakeWord on PyPI](https://pypi.org/project/openwakeword/), and
[OVOS OpenWakeWord plugin](https://github.com/OpenVoiceOS/ovos-ww-plugin-openwakeword).

The captured pre-V4 runtime used NumPy `2.4.6`, conflicting with the plugin's
`numpy<2` declaration. V4 retains NumPy 2 with the separately versioned
`0.4.5a2+jarvis.1` ONNX-only plugin. It rejects TFLite, selects ONNX model paths
and loads preinstalled models without runtime downloads. The upstream license,
source hash and patch provenance are retained. Full dependency checks and real
plugin inference on silent frames pass with network connections forbidden and
no TFLite import. The historical exception is removed from validation. Scoped
laptop voice operation is exercised; full acoustic/model-file assurance remains
explicitly unverified. See the
[release record](releases.md).

The reviewed OpenWakeWord model recognises one trained phrase: **Hey Jarvis**.
The GUI retains the existing option to replace that one active phrase with a
short local Vosk phrase. It does not claim that such a replacement is an
OpenWakeWord model. OVOS can load multiple compatible trained models, but a
free-text phrase does not create one; 3.7 therefore does not add an untested
multiple-wake-word selector. Multiple choices belong there only after each
model has independent false-positive and latency evidence.

## Microphone and listening cue

Fresh installations use the reviewed SoundDevice path with ALSA fallback.
Any explicit microphone module or device is machine-owned and preserved.
Service readiness alone is not accepted as proof of capture; the release
procedure includes wake-word and manual-listen tests.

Jarvis plays the listening cue at the user's current volume. Cue completion
controls only when background playback is ducked; it never delays microphone
capture. The listener takes a fresh volume snapshot for each activation,
restores it at record end and has a bounded emergency restore. The portable
default is 20%, adjustable from the Voice page. Existing custom values remain
untouched.

Empty/noisy captures are silent. A real `Pause music` request remains valid;
Jarvis does not solve false speech by blacklisting useful commands. The
managed Faster-Whisper setup enables its supported VAD filter and keeps cue
audio outside transcription.

## Whisper hints

The hint adapter supplies enabled application names and a short reviewed cue
set to `small.en`. The `Send it` cue is retained because live logs showed
repeated `Standard`/`Present` substitutions; those unsafe ordinary-word aliases
are not registered. The adapter patches only a recognised plugin source revision and
fails closed on an unfamiliar revision. Names are sanitised and bounded by
count and byte length. Saving app choices or personal spoken names updates the
next request without sending data elsewhere.

## Speech Note

Jarvis uses Speech Note's supported local actions for one-shot writing,
continuous dictation and reading. It preserves the user's normal reading
speed; an explicit 2× request is a temporary transaction and restores the
exact prior setting. Lock contention, empty selection and startup failure have
different results. The short transaction lock covers setup and recovery only;
the background playback monitor closes its copy so a completed 2× launch
cannot block later normal reading requests.

The 4.4.1 clipboard safeguard keeps the same handoff, but bounds the
temporary X11 owner independently of the reading shell. Normal cleanup or
expiry explicitly clears only that owner's verified X11 window/process before
ending it. The check and clear are atomic, preserving a newer copy even when
its text is identical. No previous clipboard value is restored. Foreground
`xclip -quiet` is required because silent mode forks. The helper uses the
desktop's X11 and XRes libraries; unavailable identity checks reject the
reader handoff. Normal cleanup passed on the tested Cinnamon desktop; expiry
and later-copy checks passed process fixtures. See the [release record](releases.md)
for failed early trials and remaining native/release validation.

Speech Note's transformation-rule list is opaque and machine-owned. Setup
therefore explains one additive regular-expression rule for filtering the
wake phrase during continuous dictation instead of rewriting existing rules.

## Evidence status

- **VERIFIED:** clean-stack staging, ONNX load, model preparation, launcher
  relocation, rollback, microphone preservation, cue/volume guard, Whisper
  hint transactions and reading-speed restoration pass isolated tests.
- **VERIFIED live:** wake, manual listen, cue, speech output, volume restore
  and ordinary commands worked in the recorded acceptance trial.
- **PLANNED compatibility evidence:** latency on an older 16 GB computer and a
  complete login-autostart cycle remain useful post-release checks.

Historical failures and their durable fixes are summarised in
[the 3.1.1 incident record](history/v3.1.1-checklist.md). Raw machine logs are not
published in this repository.
