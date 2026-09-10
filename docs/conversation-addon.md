# Optional local conversation add-on

The Jarvis command system does not require a language model. Wake-word detection, speech recognition, speech output, browser control, desktop control, dictation, agent messaging and command follow-ups remain part of the core voice-command system.

The optional conversation add-on handles general questions that do not match a command. It uses OVOS Persona with an OpenAI-compatible local endpoint such as Ollama.

## Profiles

| System | Recommended profile | Typical model class | Notes |
|---|---|---|---|
| 8 GB RAM | Command-only | None | Recommended. A local conversational model leaves too little memory for a desktop, OVOS and Whisper. |
| 16 GB RAM | Light conversation | 7B to 8B, Q4 | Use a 4,096-token context and short outputs. The current Qwen2 7.6B Q4_K_M model fits this profile. |
| 32 GB RAM | Standard conversation | 7B to 14B, Q4 or Q5 | Better quality with enough space for OVOS, Whisper and ordinary multitasking. |
| 64 GB RAM | Larger CPU model | 14B to 32B, Q4 | Capacity is sufficient, but CPU generation speed may still make 7B or 14B preferable for voice. |
| Dedicated GPU | Match model to VRAM | 7B, 14B or 32B quantised | VRAM and memory bandwidth matter more than system RAM for GPU inference. Leave headroom for context and runtime overhead. |

For voice use, responsiveness generally matters more than long-context benchmark quality. Start with a 7B or 8B Q4 model, a 4,096-token context and a maximum response of about 100 tokens.

## Command-only behaviour

Run:

```bash
python3 scripts/configure-command-only.py
systemctl --user restart ovos-core.service
```

This removes Persona pipelines from intent routing and disables Persona fallback. It does not uninstall Ollama or delete any model. Unrecognised requests fall through to the normal OVOS fallback instead of invoking a language model.

The dispatcher module named `conversation.py` remains installed. It implements controlled command follow-ups such as asking what to search for; it is unrelated to the optional language-model conversation layer.

## Enabling local conversation

Requirements:

- A running OpenAI-compatible local server, normally Ollama on `127.0.0.1:11434`.
- A locally installed model.
- `ovos-persona` and `ovos-openai-plugin` in the OVOS environment.

Example:

```bash
ollama list
JARVIS_MODEL=voice-assistant \
  python3 scripts/configure-conversation-addon.py
systemctl --user restart ovos-core.service
```

The configuration script writes a user-owned persona file with mode `0600`. It uses only the local loopback endpoint and does not contain an external API credential.

## Failure isolation

The command dispatcher uses the high-priority Adapt pipeline. Persona is a separate lower-priority fallback. If Ollama is stopped, unavailable or too slow, direct commands continue to work.

For a command-focused deployment, leave the add-on disabled. It can be enabled later without reinstalling the dispatcher.
