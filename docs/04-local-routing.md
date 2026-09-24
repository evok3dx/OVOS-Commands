# Local Qwen routing

**VERIFIED in code:** the reviewed `qwen3:4b-instruct-2507-q4_K_M`
model runs through the existing Ollama service on `127.0.0.1:11434`. The model
can select only actions allowed for the current request and enabled profile.
Jarvis checks the focused window, expiry, cancellation and single-use dispatch
before a desktop action. Text returned by the model is never run as shell or
used as free-form keystrokes. File search extracts a bounded query from the
original spoken request; Media title playback uses a separate bounded native
pipeline before Qwen.

**V3 guided setup:** install and start Ollama first. `scripts/install.sh`
checks its local model list; if the reviewed model is missing, it asks to run
`ollama pull qwen3:4b-instruct-2507-q4_K_M` before any Jarvis files change.
In unattended installation, use `scripts/qwen-setup.py --prepare --yes` as an
explicit separate preparation step. The installer registers the two Qwen
pipeline stages, places Media before command routing, then checks the model
and private router settings. It refuses to overwrite a different selected
model. No cloud account, extra listening port or OVOS voice-stack upgrade is
needed. A missing Ollama service stops the guided installation with a clear
message.

**VERIFIED on Brain:** a small Ultra 9 paired sample improved from 3.25 to
1.46 seconds median for correct actions after the shorter prompt/response.
This is not a general accuracy benchmark. **PLANNED on the five-year-old 16 GB
i7:** check model load, RAM and an alternating spoken command, question,
command sequence. Keep the existing machine timeout if already configured;
change it only after measuring actual response time. The model may run on CPU,
but Ultra 9 timing cannot be assumed for the i7.

The exact reviewed tag is in [Ollama's model catalogue](https://ollama.com/library/qwen3%3A4b-instruct-2507-q4_K_M).
Ollama lists that download at about **2.5 GB**. Linux Mint on X11 and x86_64 is
the validated target; a 16 GB i7 is the **trial floor for V3**, not a tested
latency guarantee while Whisper, Bella and the model share memory. Check free
disk and RAM on that host before its live acceptance test.
