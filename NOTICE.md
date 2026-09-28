# Notices and acknowledgements

Jarvis is released under the Apache License 2.0. The complete licence text is
in `OVOS-LAUNCHER-LICENSE.txt`.

Thank you to the people and communities whose work makes this project
possible:

- **OpenVoiceOS contributors** for OVOS Core, Workshop, the plugin framework,
  skills and voice ecosystem. The unchanged launcher methods bundled in
  `_ovos_launcher.py` come from `ovos-skill-application-launcher`; their exact
  source revision and Apache-2.0 notice are recorded in `LAUNCHER.md`.
- **David Scripka and openWakeWord contributors** for the local wake-word
  engine and Hey Jarvis model used through the OVOS plugin.
- **SYSTRAN and faster-whisper contributors** for local speech recognition.
  Jarvis's compatibility-checked hint adapter retains the upstream
  Apache-2.0 text in `extras/whisper-hints/LICENSE.upstream`.
- **OpenAI's Whisper contributors** for the underlying speech-recognition
  model family.
- **Qwen contributors and the Ollama project** for the local, restricted
  natural-language fallback runtime.
- **TigreGotico and contributors** for phoonnx, together with the Kokoro voice
  ecosystem used for local speech output.
- **Michał K. and Speech Note contributors** for the optional local dictation
  and reading application.
- **yt-dlp, playerctl, Flatpak, freedesktop.org, Linux Mint and the wider
  free-software community** for the local desktop and media foundations.

These projects remain governed by their own licences and trademarks. Jarvis
does not relicense third-party packages or downloaded models. Exact versions,
source pins and hashes used by the installer are recorded in
`compatibility.json`, `voice/reviewed-stack.json` and
`docs/07-installer-updates.md`.
