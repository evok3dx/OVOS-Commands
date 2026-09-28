# Notices and acknowledgements

Jarvis is released under the [Apache License 2.0](LICENSE).

Thank you to the people and communities whose work makes this project
possible:

- [OpenVoiceOS](https://github.com/OpenVoiceOS) contributors for OVOS Core,
  Workshop, the plugin framework, skills and voice ecosystem (primarily
  Apache-2.0). The launcher methods retained from
  [`ovos-skill-application-launcher`](https://github.com/OpenVoiceOS/ovos-skill-application-launcher)
  are identified in [LAUNCHER.md](LAUNCHER.md).
- David Scripka and the
  [openWakeWord](https://github.com/dscripka/openWakeWord) contributors for the
  local wake-word engine and Hey Jarvis model (Apache-2.0).
- SYSTRAN and the
  [faster-whisper](https://github.com/SYSTRAN/faster-whisper) contributors for
  local speech recognition (MIT). The compatibility-checked adapter retains
  its upstream notice in `extras/whisper-hints/LICENSE.upstream`.
- OpenAI's [Whisper](https://github.com/openai/whisper) contributors for the
  underlying speech-recognition model family (MIT).
- The [Qwen](https://github.com/QwenLM/Qwen3) contributors and
  [Ollama](https://github.com/ollama/ollama) project for the local restricted
  language-model runtime. The reviewed Qwen3 4B Instruct model is distributed
  under Apache-2.0; Ollama is MIT-licensed.
- TigreGotico and [PhōnNX](https://github.com/TigreGotico/phoonnx)
  contributors, together with the Kokoro voice ecosystem used for local speech
  output (Apache-2.0 for PhōnNX).
- Michał K. and [Speech Note](https://github.com/mkiol/dsnote) contributors for
  the optional local dictation and reading application (MPL-2.0).
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) and
  [playerctl](https://github.com/altdesktop/playerctl) contributors for bounded
  media discovery and player control, plus Flatpak, freedesktop.org, Linux
  Mint and the wider free-software community.

These projects retain their own licences, copyright notices and trademarks.
Jarvis does not relicense third-party packages or downloaded models. Exact
versions, source pins and hashes used by the installer are recorded in
`compatibility.json`, `voice/reviewed-stack.json` and
`docs/07-installer-updates.md`.
