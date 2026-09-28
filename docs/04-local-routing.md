# Local Qwen routing

**VERIFIED in code:** the reviewed `qwen3:4b-instruct-2507-q4_K_M`
model runs through the existing Ollama service on `127.0.0.1:11434`. The model
can select only actions allowed for the current request and enabled profile.
Jarvis checks the focused window, expiry, cancellation and single-use dispatch
before a desktop action. Text returned by the model is never run as shell or
used as free-form keystrokes. File search and Qwen-approved Media title
playback extract bounded queries from the original spoken request; the native
Media title pipeline still runs first. Safe writing/dictation, reading,
browser search, message starters and enabled-app operations remain available
as semantic fallbacks. Message starters open the existing second-turn capture;
the model never receives or submits its dictated content. Detected apps and
saved spoken names are supplied by the current profile, not a fixed phrase
list.

**V3 guided setup:** install and start Ollama first. `scripts/install.sh`
checks its local model list; if the reviewed model is missing, it asks to run
`ollama pull qwen3:4b-instruct-2507-q4_K_M` before any Jarvis files change.
In unattended installation, use `scripts/qwen-setup.py --prepare --yes` as an
explicit separate preparation step. The installer registers Qwen command and
chat stages plus a model-independent unmatched-command stage. Media runs
first; deterministic commands that Qwen declines receive “Please repeat”
before broad fallback skills such as DDG can claim them. Real questions still
continue to DDG/common-query and then local Qwen chat. Setup then checks the
model and private router settings. It refuses to overwrite a different selected
model. No cloud account, extra listening port or OVOS voice-stack upgrade is
needed. A missing Ollama service stops the guided installation with a clear
message.

**VERIFIED on the earlier reference system:** a small paired sample improved
from 3.25 to 1.46 seconds median for correct actions after the shorter response
format. **VERIFIED on the release laptop for the V3.5 compact-prompt
diagnostic:** seven actions completed without an eight-second timeout; the warm
median was 2.66 seconds. Ollama reported the model resident indefinitely and
every `load_duration` was zero. Warm singleton prompt evaluation was usually
below 0.4 seconds, while generation was the larger remaining variable. This is
a small latency diagnostic, not the required 360-case accuracy benchmark.

The first V3.5 singleton prompt incorrectly treated polite action requests such
as “Can I search through Brave?” as information-seeking questions. Rc2 now
distinguishes “Can I…”, “Could you…” and “Would you…” requests from genuine
questions. This correction retains the same candidate allowlist and output
validation and still requires a live model rerun. **PLANNED on the separate
five-year-old 16 GB i7:** check model load, RAM and an alternating spoken
command, question, command sequence. Do not infer its latency from either
faster machine.

After installation, `python3 scripts/qwen-smoke-test.py` runs the reviewed
writing, dictation, reading, browser-search, message and song-title phrase
matrix against the real local model. It prints the selected action and timing
but deliberately executes nothing. Profile-disabled private agents are shown
as skipped rather than treated as failures.

For broader release testing, `python3 scripts/routing-benchmark.py` generates
360 command variations across writing, continuous dictation, 1×/2× reading,
browser search, safe message starters, media, files and deliberately rejected
requests. It checks the request-specific allowlist and then the real local Qwen
model without dispatching any action. `--quick` runs a representative 40-case
sample; `--policy-only` checks every allowlist without invoking the model. The
default full run uses the live eight-second deadline and saves a timestamped
Markdown report under `~/Downloads/`. An interrupted run also saves its partial
results. The supplied 40-case V3.5 quick run is historical diagnostic evidence,
not a substitute for the complete run.

This benchmark starts from typed text, after speech recognition. It cannot
measure the microphone, wake word or Whisper accuracy. Live release acceptance
must still compare the listener's `Raw transcription` with the words actually
spoken. A router pass must never be recorded as a Whisper pass.

The exact reviewed tag is in [Ollama's model catalogue](https://ollama.com/library/qwen3%3A4b-instruct-2507-q4_K_M).
Ollama lists that download at about **2.5 GB**. Linux Mint on X11 and x86_64 is
the validated target; a 16 GB i7 is the **trial floor for V3**, not a tested
latency guarantee while Whisper, Bella and the model share memory. Check free
disk and RAM on that host before its live acceptance test.
