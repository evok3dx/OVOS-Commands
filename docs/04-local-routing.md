# Optional local Qwen routing

**VERIFIED in code:** `routing_model.py` uses the reviewed
`qwen3:4b-instruct-2507-q4_K_M` model through Ollama on `127.0.0.1:11434`.
The response is restricted to the current request's allowed actions; focus,
expiry, cancellation and single-use dispatch apply in the skill. An unrecognised
or disabled app cannot be opened merely because a model named it. Jarvis works
without this model. `scripts/qwen-setup.py` checks the local service, exact model
and both routing stages before it can enable the private router setting. It
preserves other saved settings and refuses to change an existing different model.
It never installs a model automatically or changes system services.

**VERIFIED on Brain by the 24 September local report:** the Ultra 9 with its
existing Intel Arc Vulkan setup returned the correct action at a median 1.46 s
in a small paired sample, versus 3.25 s before a compact-response change.
Live fallback was later repaired for the core's canonical utterance event and
reported working for app commands. This is not a full accuracy or reliability
benchmark. Model residency is requested but can be evicted by memory pressure.

**PLANNED on i7:** run `python3 scripts/qwen-setup.py`, inspect free RAM and
Ollama availability, download the same 4B model only if desired, then check
alternating command/question/command speech with the existing eight-second
limit. Start on CPU; record actual latency before considering acceleration,
smaller models or changed timeout. The i7's 32 GB RAM supports a reasonable
trial, but Ultra 9 timings cannot be transferred to it. No additional network
port or remote provider is required.

The exact reviewed model is listed on
[Ollama's model page](https://ollama.com/library/qwen3%3A4b-instruct-2507-q4_K_M).
