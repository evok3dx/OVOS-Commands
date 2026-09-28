# Reviewed Whisper app-name hints

**VERIFIED:** this is the reviewed local plugin patch used on the reference
system with `ovos-stt-plugin-fasterwhisper 0.4.0`. It adds bounded enabled-app
names to the existing `small.en` initial prompt. It changes no model, voice,
app permissions or profile file. The reference audit
records a quiet-room false transcription of “Pause music”; command phrases are
therefore not used as recognition hints. This avoids biasing silence toward a
real executable command. The record predates this narrower prompt, so the live
release test remains required. Do not add commands to the prompt without
measured evidence. Listener activation and a brief voice check were reported;
an unhinted accuracy baseline has not been measured.

Inspect first with `python3 extras/whisper-hints/install.py --check`. If the
installed plugin has different methods or an existing unknown edit, the patch
refuses to write. The V3 guided installer applies it when the source matches and
the listener is running. Installing it is a **live-machine change** requiring
that machine's own checked backup, listener restart and speech check. Run the
script as the desktop user only, from this release's checkout, after reviewing
its printed target. A future plugin reinstall may overwrite the patch.

`python3 extras/whisper-hints/test_update.py` runs 17 offline tests. The
`reviewed-plugin-0.4.0.py` fixture comes from the Apache-licensed upstream
project; the bundled `LICENSE.upstream` preserves its licence.
