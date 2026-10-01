# Local Qwen routing

**VERIFIED in code:** the reviewed `qwen3:4b-instruct-2507-q4_K_M`
model uses general Ollama on `127.0.0.1:11434` when isolation is declined.
The 4.0.1 [guided isolation installer](core-isolation.md#guided-installer-401)
selects a dedicated instance on `127.0.0.1:11435` for isolated installations;
there is no fallback between these two fixed endpoints. The model
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

**V4 guided setup:** install and start Ollama first. `scripts/install.sh`
checks its local model list; if the reviewed model is missing, it asks to run
`ollama pull qwen3:4b-instruct-2507-q4_K_M` before any Jarvis files change.
In unattended installation, use `scripts/qwen-setup.py --prepare --yes` as an
explicit separate preparation step. The installer registers Qwen command and
chat stages plus a model-independent unmatched-command stage. Media runs
first; deterministic commands that Qwen declines receive “Please repeat”
before broad fallback skills such as DDG can claim them. In unrestricted mode,
questions can continue to enabled DDG/common-query and local Qwen chat. Native
isolation disables unreviewed online skills in core; Weather and Media have
separate helpers, while Wikipedia/WikiHow and named-city time support remain
future work. Setup then checks the
model and private router settings. It refuses to overwrite a different selected
model. No cloud account is needed. Selected isolation uses only the fixed dedicated
loopback port described above. The managed V4
runtime remains hash-verified. A missing Ollama service stops setup with a clear
message.

**VERIFIED on the earlier reference system:** a small paired sample improved
from 3.25 to 1.46 seconds median for correct actions after the shorter response
format. **VERIFIED on the release laptop for the V3.5 compact-prompt
diagnostic:** seven actions completed without an eight-second timeout; the warm
median was 2.66 seconds. Ollama reported the model resident indefinitely and
every `load_duration` was zero. Warm singleton prompt evaluation was usually
below 0.4 seconds, while generation was the larger remaining variable. This is
a small latency diagnostic, not the required 350-case accuracy benchmark.

## Performance context

These figures explain why Jarvis keeps deterministic commands ahead of model
and screen-agent routing. They are deliberately scoped rather than presented as
one interchangeable benchmark:

| System and evidence | Observed timing | What the figure includes |
| --- | ---: | --- |
| Jarvis native route, supplied live laptop trace on 2026-09-28 | 27 ms | End of raw transcription to the matched native intent. It excludes listening, speech recognition and the application action. |
| Jarvis local Qwen, V3.5 compact-prompt laptop diagnostic | 2.66 s warm median | Seven typed post-STT action requests. It is not an end-to-end voice result or a substitute for the pending 350-case run. |
| Alexa Plus, one independent 2026 compound smart-home test | under 3 s | One reviewer timed a multi-device request; this is an observation, not a vendor latency guarantee. |
| Google Gemini for Home, the same independent test | about 10 s | The same compound request; some simpler commands in that review also approached ten seconds. |
| Agent S2 with Claude 3.7 on OSWorld-Human | 690 s average task runtime; 38.6 s average agent step | A research agent repeatedly observing, planning, grounding and reflecting over desktop tasks. The corresponding human runs were 128-183 seconds. This is not a current Claude product SLA. |
| Microsoft Copilot computer use | no comparable published timing | Microsoft documents iterative browser/desktop clicking and typing plus background task monitoring, but does not publish a directly comparable completion-time guarantee. |

The smart-speaker observation comes from [The Verge's 2026 Google Home and
Alexa Plus comparison](https://www.theverge.com/tech/959503/google-home-speaker-review-gemini-for-home).
The desktop-agent values come from the peer-reviewed
[OSWorld-Human efficiency study](https://arxiv.org/abs/2506.16042) and its
[reproducibility repository](https://github.com/WukLab/osworld-human).
Microsoft's current scope is described in its
[Copilot Studio computer-use documentation](https://learn.microsoft.com/en-us/microsoft-copilot-studio/computer-use)
and [Copilot Tasks documentation](https://support.microsoft.com/en-us/microsoft-copilot/using-copilot-tasks).

This is architecture context, not an assertion that unlike tasks are directly
equivalent. A fixed local command should be faster than a general visual agent:
Jarvis selects one reviewed action and dispatches it, while a screen agent may
need several screenshot, reasoning, action and verification cycles. The full
spoken path must still be measured separately from post-transcription routing.

The first V3.5 singleton prompt incorrectly treated polite action requests such
as “Can I search through Brave?” as information-seeking questions. Rc2 now
distinguishes “Can I…”, “Could you…” and “Would you…” requests from genuine
questions. This historical correction retains the same candidate allowlist and
output validation; full live model coverage remains unverified. **PLANNED on the separate
five-year-old 16 GB i7:** check model load, RAM and an alternating spoken
command, question, command sequence. Do not infer its latency from either
faster machine.

After installation, `python3 scripts/qwen-smoke-test.py` runs the reviewed
writing, dictation, reading, browser-search, message and song-title phrase
matrix against the real local model. It prints the selected action and timing
but deliberately executes nothing. Profile-disabled private agents are shown
as skipped rather than treated as failures.

For broader release testing, `python3 scripts/routing-benchmark.py` generates
exactly 350 natural variations covering every action exposed to Qwen by the
reference profile: writing and dictation, 1×/2× reading, focused-window
controls, browser navigation and tabs, browser and local search, media,
message starters, information requests, and open/focus/minimise/maximise for
every reviewed application. Six compound, destructive or secret-sharing
requests must be rejected. It checks the request-specific allowlist and then
the real local Qwen model without dispatching any action. Restricted native
commands such as app close, clipboard editing and keystrokes remain exact and
are tested separately rather than being exposed to Qwen for a benchmark score.
`--quick` runs a representative 40-case sample; `--policy-only` checks every
allowlist without invoking the model. The default full run uses the live
eight-second deadline and saves a timestamped Markdown report under
`~/Downloads/`. An interrupted run also saves its partial results. The supplied
40-case V3.5 quick run is historical diagnostic evidence, not a substitute for
the complete run.

This benchmark starts from typed text, after speech recognition. It cannot
measure the microphone, wake word or Whisper accuracy. Live release acceptance
must still compare the listener's `Raw transcription` with the words actually
spoken. A router pass must never be recorded as a Whisper pass.

Clear past-tense descriptions such as `I wrote this stuff` are rejected before
the model is called. This preserves natural requests such as `Could you write
this for me?` while preventing a statement from opening second-turn writing.

The exact reviewed tag is in [Ollama's model catalogue](https://ollama.com/library/qwen3%3A4b-instruct-2507-q4_K_M).
Ollama lists that download at about **2.5 GB**. Linux Mint on X11 and x86_64 is
the validated target; a 16 GB i7 is the **trial floor for V3**, not a tested
latency guarantee while Whisper, Bella and the model share memory. Check free
disk and RAM on that host before its live acceptance test.
