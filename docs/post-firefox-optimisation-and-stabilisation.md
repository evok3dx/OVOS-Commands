# Post-Firefox OVOS Optimisation and Stabilisation

## Purpose and scope

This document records the work completed after Brave and Firefox voice control became functional. It covers startup performance, wake-word interruption, persona cleanup, restart tooling, audio errors, delayed barge-in, silence hallucinations, validation results, rollback requirements, and the next maintainability refactor.

It is intended to accompany the earlier Firefox implementation document in Git. It deliberately distinguishes project source from live configuration and temporary patches inside the Python virtual environment.

## Final operating model

The system now follows this pattern:

1. `Hey Jarvis` is detected by OpenWakeWord.
2. Current Jarvis speech is stopped immediately.
3. The acknowledgement beep plays at normal volume.
4. After a short delay, system output drops to 15% while the command is recorded.
5. Speech is transcribed and routed to an allowlisted command or the configured persona.
6. Original volume is restored as soon as recording ends.
7. Silence-only Whisper results are filtered before intent routing.

Only `Hey Jarvis` is considered reliable. Single-word `Jarvis` and `Jervis` were tested and removed because they were too short for dependable wake-word detection and increased false-positive risk.

## Files and components involved

### Project-controlled files

- `ovos_skill_jarvis_dispatcher/__init__.py`
  - Wake-word speech interruption.
  - Browser, application, dictation and agent commands.
  - Conversation state, retries and timeouts.
  - `can_stop()` and `stop()` behaviour.

- `jarvis-app-window`
  - Allowlisted application and window management.

- `jarvis-focused-navigation`
  - Focus-aware scrolling and browser navigation.

- `jarvis-restart`
  - Adaptive terminal progress display.
  - Core-only and full restart modes.

### Live machine configuration

- `~/.config/mycroft/mycroft.conf`
  - Wake-word configuration.
  - Listener and delayed barge-in settings.
  - Persona discovery policy.
  - TTS voice configuration.
  - Whisper hallucination filtering.

- `~/.config/mycroft/skills/ovos-skill-boot-finished.openvoiceos/settings.json`
  - Spoken readiness announcement retained.
  - Broken redundant ready sound disabled.

- `~/.config/ovos_persona/ovos-installer-llm.json`
  - Local OpenAI-compatible persona configuration.
  - Local Ollama endpoint and selected voice-assistant model.
  - Concise, action-safe system prompt.

### Runtime package patches

These currently live under `~/.venvs/ovos/lib/python3.11/site-packages/` and can be overwritten by upgrades:

- `ovos_core/skill_manager.py`
  - Bounded PHAL connectivity response wait.

- `ovos_utils/network_utils.py`
  - Bounded HTTP connectivity checks.

- `ovos_persona/__init__.py`
  - Compatibility implementation of `can_stop()`.

- `ovos_dinkum_listener/service.py`
  - Delayed and cancellation-safe fake barge-in.

These changes must be represented in Git as idempotent patch/install scripts, not by committing the virtual environment.

## Optimisation 1: adaptive restart helper

### Original problem

Restarting Jarvis provided little feedback. The terminal appeared to wait until the spoken `I am ready` announcement, and systemd reporting a service as running did not mean all skills were usable.

### First improvement

A `jarvis-restart` helper was created with a terminal progress bar. Readiness is determined from the Jarvis skill readiness event rather than merely from systemd's active state.

### Real ETA improvement

The bar was changed from a cosmetic timer to an adaptive estimate:

- Successful load duration is measured on every run.
- The most recent ten successful measurements are retained.
- Their rolling average supplies the next ETA.
- Failed and timed-out runs should not contaminate the history.
- Measurement continues indefinitely, while only the newest ten samples are used.
- Resource use is negligible: one small shell process during restart, journal polling, and a tiny history file.

### Restart modes

- `jarvis-restart`
  - Restarts only OVOS core when listener code or wake-word configuration has not changed.
  - Uses the core-only timing history.

- `jarvis-restart --full`
  - Restarts core and listener.
  - Required after listener, wake-word, microphone, VAD or barge-in changes.
  - Uses a separate full-restart timing history.

Keeping separate histories prevents slow full restarts from making the core-only ETA inaccurate.

## Optimisation 2: startup delay investigation

### Symptoms

Full readiness originally took roughly 158 to 160 seconds. The listener sometimes took more than two minutes to connect to the message bus even though the message bus process itself remained active.

### What the logs showed

- OVOS core and listener started immediately at the systemd level.
- Core loaded some early services and skills quickly.
- Listener connection and final skill readiness were delayed.
- The message bus logged WebSocket connections resetting without a closing handshake around restarts.
- These WebSocket messages were consequences of clients restarting and disconnecting, not proof that the message bus daemon had crashed.
- Core readiness included connectivity synchronization and direct HTTP fallback checks.

### Root causes addressed

#### Unbounded PHAL response wait

`ovos_core.skill_manager._sync_skill_loading_state()` waited for an `ovos.PHAL.internet_check` response without an explicit short timeout.

The runtime patch changed the request to use a three-second timeout:

```python
resp = self.bus.wait_for_response(
    Message("ovos.PHAL.internet_check"),
    timeout=3
)
```

#### Unbounded HTTP connectivity checks

When PHAL did not answer, `is_connected_http()` performed `requests.head()` calls without a timeout. A slow or unreachable endpoint could therefore stall startup.

The runtime patch added a three-second HTTP timeout:

```python
status = requests.head(host, timeout=3).status_code
```

### Result

Observed readiness fell to approximately 25 to 28 seconds, an improvement of roughly 83% from the original 158 to 160 seconds.

### Maintenance warning

These are direct runtime package patches. An OVOS or Python package upgrade may replace them. The Git repository should include:

- An idempotent patch script that validates exact source anchors.
- Automatic backups before mutation.
- A syntax check afterward.
- A verification command that confirms both timeouts remain present.
- Package versions against which the patches were tested.

## Optimisation 3: removal of the unused Model2Vec pipeline

### Problem

Core repeatedly logged:

```text
Failed to load pipeline plugin 'ovos-m2v-pipeline'
Converting a legacy pipeline requires scikit-learn and skops.
```

### Investigation

- Installed package: `ovos_m2v_pipeline==0.0.9`.
- Nothing declared it under `Required-by`.
- The active configuration did not reference it.
- Only historical `.pre-*` configuration backups referenced Model2Vec.

### Solution

The unused package was uninstalled instead of adding large dependencies solely to satisfy an inactive pipeline.

### Result

Post-uninstall restarts no longer produced the Model2Vec loading error. Earlier errors remained visible when broad journal windows included pre-uninstall restarts, so timestamps had to be compared carefully.

### Reinstallation note

Do not reinstall Model2Vec automatically. If it becomes necessary later, first add it deliberately to active intent-pipeline configuration and install compatible `scikit-learn` and `skops` versions.

## Stabilisation 1: persona discovery cleanup

### Existing persona

The intended persona is stored at:

```text
~/.config/ovos_persona/ovos-installer-llm.json
```

It already had a system prompt, used the local OpenAI-compatible endpoint at `127.0.0.1:11434/v1`, selected the `voice-assistant` model, and constrained ordinary answers to short natural speech. Secrets must remain redacted from Git.

### Problem

OVOS also discovered personas supplied by installed plugins:

- WikiHow
- Wikipedia
- Wolfram Alpha
- Remote Llama

Remote Llama lacked a configured system prompt and logged an error while defaulting to a generic assistant prompt. These plugin personas were unnecessary because the user-defined persona is authoritative.

### Solution

Persona configuration was set to ignore plugin-provided personas:

```json
{
  "intents": {
    "persona": {
      "ignore_plugin_personas": true
    }
  }
}
```

### Verification

On the successful restart, logs showed only:

```text
Found persona (user defined): OVOS Installer LLM
```

There were no later `Found persona (provided via plugin): Remote Llama` or missing-system-prompt errors.

Standalone WikiHow and Wikipedia skills still loaded. This is expected: standalone skills and personas are separate systems.

## Stabilisation 2: immediate wake-word interruption

### Required behaviour

The user wanted GPT-style interruption: saying `Hey Jarvis` while Jarvis is talking should immediately stop or pause current speech and begin listening.

### Why fake barge-in alone was insufficient

OVOS `fake_barge_in` lowers output volume while recording. It does not itself stop current TTS.

### Dispatcher solution

The Jarvis skill registered a handler for `recognizer_loop:wakeword` and emitted:

```python
Message("mycroft.audio.speech.stop")
```

The dispatcher also implements:

- `can_stop()` returning `True`.
- `stop()` to stop OVOS speech, cancel Speech Note activity, reset dictation state and deactivate the dispatcher.

### Persona compatibility problem

The installed `PersonaService` had session-stop functionality but did not implement the `can_stop()` interface required by the installed `ovos-workshop`. Stop capability checks could raise `NotImplementedError`.

### Persona compatibility workaround

A small runtime compatibility method was added to `ovos_persona/__init__.py`:

```python
def can_stop(self, message=None):
    return True
```

This workaround should be removed once the installed upstream package supplies a compatible implementation.

## Stabilisation 3: wake-word reliability

### Reliable configuration

`hey_jarvis` uses OpenWakeWord with a threshold of `0.65`.

The original threshold of `0.4` was too permissive and contributed to unexplained detections. Raising it reduced false activation.

### Short aliases rejected

Attempts were made to support standalone `Jarvis` and `Jervis` through Vosk. Testing showed they were too short and did not work reliably. The `jarvis_aliases` hotword entry was removed from the live configuration.

Do not document or test those aliases as supported wake words. The supported wake phrase is:

```text
Hey Jarvis
```

### Current relevant listener configuration

```json
{
  "hotwords": {
    "hey_jarvis": {
      "module": "ovos-ww-plugin-openwakeword",
      "listen": true,
      "threshold": 0.65
    }
  },
  "listener": {
    "wake_word": "hey_jarvis",
    "instant_listen": true,
    "fake_barge_in": true,
    "barge_in_volume": 15,
    "barge_in_delay": 0.25
  }
}
```

## Stabilisation 4: broken boot-ready sound

### Symptom

Around the spoken `I am ready` announcement, `ovos-audio` repeatedly logged:

```text
FileNotFoundError: None does not exist
```

Kokoro TTS nevertheless generated and played valid WAV files. The custom `jarvis-ready.wav` also played successfully.

### Root cause

The boot-finished skill defaults both of these settings to true:

- `speak_ready`
- `ready_sound`

Its `handle_ready()` method called `self.acknowledge()` for `ready_sound`, but no valid acknowledgement sound was configured. That redundant call produced the missing-file exception. It was unrelated to Kokoro.

### Solution

The boot-finished skill settings were changed to:

```json
{
  "__mycroft_skill_firstrun": false,
  "ready_sound": false,
  "speak_ready": true
}
```

### Result

- `I am ready` remained enabled.
- The custom Jarvis notification WAV remained enabled.
- The redundant missing acknowledgement sound was disabled.
- The `FileNotFoundError` disappeared.

## Stabilisation 5: delayed fake barge-in

### Initial tradeoff

Enabling fake barge-in at 15% reduced the acknowledgement beep as soon as recording began. Disabling it restored the beep but removed protection against the system's own output being captured by the microphone.

`listener.mute_during_output` was deliberately rejected because it would prevent the listener hearing `Hey Jarvis` while Jarvis was speaking, defeating true interruption.

### Solution

`ovos_dinkum_listener/service.py` was patched to delay the fake barge-in volume reduction by 0.25 seconds:

1. Wake-word event triggers the normal-volume acknowledgement beep.
2. A daemon `Timer` waits 0.25 seconds.
3. Volume drops to 15% during command recording.
4. Recording completion cancels any pending timer.
5. A generation counter prevents an obsolete timer from affecting a newer recording.
6. Original volume is restored when recording ends.

### Race-safety requirements

The patch added:

- `Timer` to the threading imports.
- `_barge_in_timer`.
- `_barge_in_generation`.
- `_barge_in_lock`.
- `_apply_fake_barge_in(generation)`.

The cancellation and generation checks are important. A simple delayed timer could otherwise lower volume after a very short recording had already ended, leaving system volume stuck at 15%.

### Validation

Logs confirmed the patched function was active:

```text
_apply_fake_barge_in ... lowering volume to: 15
_record_end_signal ... restoring volume to: 50
```

The normal output volume on this machine was 50% during the test. The beep remained audible before the reduction.

## Stabilisation 6: television audio and self-listening investigation

### Observed event

During one restart, the listener transcribed:

```text
Alright, what do you want?
```

The persona answered in two streamed speech segments:

```text
I just want to help you.
What can I do for you?
```

The boot-ready announcement happened independently between the persona's two output segments.

### Investigation result

The phrase `Alright, what do you want?` did not exist in the Jarvis dispatcher or relevant OVOS package source. It therefore entered through microphone audio rather than a hard-coded wake response. The television was on during the incident and is the likely source.

### Protection retained

Delayed fake barge-in was retained as a low-cost mitigation against television or system output entering the command recording. It does not replace the OpenWakeWord threshold or explicit speech-stop handler.

## Stabilisation 7: silence and Whisper hallucinations

### Symptoms

When `Hey Jarvis` was followed by silence, the STT server sometimes returned punctuation with confidence `1.0`:

```text
Raw transcription: [('.', 1.0)]
```

Before filtering, OVOS normalised this to an empty parsed utterance, passed it into intent and translation pipelines, and produced unwanted responses such as:

- `Please rephrase your request.`
- `Sorry, I didn't catch that.`
- `I don't understand.`

It also logged failed translation attempts for an empty string.

### Configuration-based solution

The Dinkum listener already supports hallucination filtering. Rather than adding another runtime code patch, the live configuration enables it and extends the list:

```json
{
  "filter_hallucinations": true,
  "hallucination_list": [
    "thanks for watching!",
    "thank you for watching!",
    "so",
    "beep!",
    ".",
    "..",
    "...",
    "!",
    "?",
    "until soon enough.",
    "until soon enough"
  ]
}
```

The final two entries were added after silence produced `Until soon enough.` during testing.

### Validation

After adding punctuation entries:

- Raw `.` remained visible in listener logs, as expected.
- It was not emitted as `Parsing utterance`.
- No persona or translation response followed it.
- The listener logged `Empty transcription, either recorded silence or STT failed!` internally.

That remaining line is diagnostic rather than a functional failure. New recurring silence hallucinations can be added to the exact filter list, but broad filtering should be avoided because it could suppress valid short commands.

## Confirmed functional tests

The following were confirmed working during this phase:

- `Hey Jarvis` wake phrase.
- Immediate TTS interruption handler.
- Full-volume acknowledgement beep before delayed reduction.
- Volume reduction to 15% during recording.
- Restoration to the prior 50% volume after recording.
- `Open Firefox`.
- `Close Firefox`.
- `What's the time?`.
- Spoken `I am ready` notification.
- No `FileNotFoundError` after disabling the redundant boot-ready sound.
- Punctuation-only transcription filtered before intent parsing.

Previously confirmed and still requiring regression coverage after structural changes:

- Firefox and Brave search prompts.
- New-tab search behaviour when a browser is already open.
- `Write this` and `Send it`.
- Speech Note start, pause, continue and stop.
- Browser navigation and close-tab versus close-window separation.

## Warnings observed but not treated as active faults

### Old plugin entry points

Several packages warn that old entry-point names should migrate to newer OPM namespaces. They currently load successfully. Track upstream updates rather than patching every warning locally.

### Shutdown event-removal warnings

Core may log `Failed to remove event` while unloading skills. These occurred during orderly restarts and did not prevent the new service instance from loading.

### WebSocket reset messages

The message bus may report connections reset without a closing handshake while core or listener processes restart. The bus daemon remained active. Treat these as restart noise unless they occur continuously during normal operation.

### Unauthenticated Hugging Face requests

The system warns that Hugging Face downloads are unauthenticated. This affects download rate limits and model-fetch speed, not normal inference once models are cached. Do not add a token unless remote model downloads require it.

### Translation-server errors for empty text

These were downstream consequences of punctuation-only STT reaching the intent pipeline. The hallucination filter addresses the source. If they recur with a filtered transcript, inspect the exact raw and parsed utterances before changing translation plugins.

## Why these solutions were chosen

- Prefer bounded waits over assuming external services always answer.
- Remove unused broken components instead of installing dependencies for them.
- Keep one authoritative persona instead of allowing silent fallback to plugin personas.
- Preserve wake-word detection during output, so do not mute the microphone globally.
- Stop TTS explicitly on wake-word detection.
- Delay volume reduction rather than sacrificing the acknowledgement beep.
- Use timer cancellation and generation guards for concurrency safety.
- Use built-in configuration filters before patching runtime code.
- Add only observed STT hallucinations and aliases, not broad fuzzy rules.
- Validate behaviour from chronological logs rather than mixing events from multiple restarts.

## Git repository recommendations

### Suggested layout

```text
docs/
├── firefox-voice-control.md
├── post-firefox-optimisation.md
└── acceptance-tests.md

config/
├── mycroft.listener.example.json
├── boot-finished.settings.example.json
└── persona.example.json

scripts/
├── install.sh
├── verify.sh
├── rollback.sh
├── install-runtime-patches.sh
└── jarvis-restart

patches/
├── ovos-core-connectivity-timeouts.patch
├── ovos-utils-http-timeout.patch
├── ovos-persona-can-stop.patch
└── ovos-dinkum-delayed-barge-in.patch

bin/
├── jarvis-app-window
└── jarvis-focused-navigation

ovos_skill_jarvis_dispatcher/
└── ...
```

### Installer requirements

The installer should:

1. Verify expected source anchors and installed package versions.
2. Refuse to patch if an anchor is missing or appears more than once.
3. Back up each target with a timestamp.
4. Apply configuration through parsed JSON, never text concatenation.
5. Avoid overwriting unrelated user configuration.
6. Never copy API keys or tokens into Git-managed example files.
7. Compile changed Python files with `python -m py_compile`.
8. Validate JSON with `jq` or Python.
9. Restart only the services affected by the change.
10. Print the backup paths and verification result.

### Verification script requirements

The verification script should check:

- Relevant systemd services are active.
- `hey_jarvis` loads with OpenWakeWord threshold `0.65`.
- Unsupported short aliases are absent.
- Jarvis dispatcher reports ready.
- Persona discovery finds only `OVOS Installer LLM`.
- No Model2Vec pipeline is configured or installed unintentionally.
- PHAL and HTTP timeout patches are present.
- Persona `can_stop()` compatibility exists where required.
- Delayed barge-in code is present and compiles.
- Boot-ready sound is disabled while spoken readiness remains enabled.
- Hallucination filters contain the tested silence outputs.
- Helper scripts exist and are executable.

### Rollback strategy

Rollback must be granular. It should allow restoring:

- Jarvis dispatcher source.
- Each runtime package patch independently.
- `mycroft.conf` from its matching backup.
- Boot-finished skill settings.
- Restart helper.

Do not use destructive Git resets or delete all timestamped backups automatically. Restore an explicitly selected backup and syntax-check it before restarting services.

### Files that must not be committed

- Live persona API keys.
- Complete unreviewed `mycroft.conf`.
- The entire Python virtual environment.
- TTS cache files.
- Wake-word or utterance recordings.
- Raw journals containing private spoken content.
- Adaptive timing history.
- Timestamped backups.

Suggested ignore rules:

```gitignore
*.before-*
*.pre-*
*.backup
*.bak
__pycache__/
*.pyc
*.wav
load-times*
restart-history*
```

## Next structural improvement: dispatcher modularisation

The dispatcher has grown to roughly 2,000 lines in one `__init__.py`. The next change should be a behaviour-preserving refactor, not another feature expansion.

Suggested structure:

```text
ovos_skill_jarvis_dispatcher/
├── __init__.py
├── browser.py
├── desktop.py
├── dictation.py
├── agents.py
├── conversation.py
├── wakeword.py
├── vocabulary.py
└── helpers.py
```

Goals:

- Keep `__init__.py` focused on skill lifecycle and intent registration.
- Put Brave and Firefox behind one shared browser implementation.
- Separate command phrases from execution logic.
- Keep allowlists explicit for state-changing actions.
- Isolate conversation stages, retries and timers.
- Prevent browser, dictation and agent conversations from sharing accidental state.
- Make intent conflicts such as `close up` easy to detect automatically.
- Add unit tests without needing to restart the full voice stack.

Before refactoring:

1. Preserve the currently working source and its checksum.
2. Extract a complete vocabulary and intent inventory.
3. Record the current acceptance-test results.
4. Commit the known-good monolithic version as a rollback point.

During refactoring:

- Move one responsibility at a time.
- Do not rename spoken commands or change response text unnecessarily.
- Run syntax and import tests after each move.
- Run core-only restarts for dispatcher-only changes.
- Run a full restart only when listener behaviour changes.

## Acceptance checklist before declaring this phase stable

- [ ] `Hey Jarvis` reliably wakes the system.
- [ ] Saying `Hey Jarvis` during long TTS stops speech immediately.
- [ ] Acknowledgement beep remains at normal volume.
- [ ] Output drops to 15% only after the beep.
- [ ] Original volume is restored after every recording.
- [ ] Silence punctuation does not reach `Parsing utterance`.
- [ ] `Until soon enough` no longer reaches intent parsing when produced by silence.
- [ ] No missing-ready-sound exception occurs.
- [ ] No Model2Vec load error occurs after uninstall.
- [ ] Only the intended user persona is discovered.
- [ ] Core readiness remains near the 25-to-28-second baseline.
- [ ] Firefox and Brave browser regression tests pass.
- [ ] Dictation and Speech Note regression tests pass.
- [ ] Installation and rollback scripts work on copies before touching live files.

## Current status

The major startup, persona, audio and wake-interruption problems are resolved. The system starts in roughly half a minute instead of approximately two and a half minutes, uses only the intended persona, announces readiness without a missing-file exception, preserves a full-volume wake beep, reduces output while recording, and filters known silence hallucinations before intent routing.

The remaining work is primarily engineering hygiene:

1. Complete the final silence-hallucination retest.
2. Capture all live changes as reproducible Git-managed patches and configuration examples.
3. Commit the known-good monolithic dispatcher.
4. Refactor the dispatcher into focused modules with no behavioural changes.
5. Add automated conflict, syntax and acceptance tests.
