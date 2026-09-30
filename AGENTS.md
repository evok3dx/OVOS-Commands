# Jarvis contributor and AI-agent guide

This file applies to the whole repository and is the canonical instruction
file for human and AI contributors. `CLAUDE.md`, `GEMINI.md` and
`.github/copilot-instructions.md` are pointers back here; never copy the rules
into those files. Code and passing tests describe current behaviour;
`docs/12-decisions.md` records approved intent and security constraints. Do not
infer either from chat history or historical release notes.

## Mandatory reading order

Before proposing or changing code, read:

1. this file;
2. `docs/releases.md` for the current release delta and open verification;
3. `docs/12-decisions.md` for durable constraints;
4. `docs/troubleshooting.md` for current known problems and proven solutions;
5. the code, tests and manifest governing the affected feature.

Use `docs/history/` only for background. Historical observations never
override current code, tests, decisions or the current release record.

## Authoritative sources

- `ovos_skill_jarvis_dispatcher/action_registry.py`: allowed actions and Qwen
  exposure.
- `ovos_skill_jarvis_dispatcher/vocabulary.py`: deterministic spoken phrases.
- `ovos_skill_jarvis_dispatcher/capabilities.py` and `profile.py`: detected,
  enabled and default applications.
- `deployment-manifest.json`: packaged files.
- `compatibility.json` and `voice/reviewed-stack.json`: supported host and
  reviewed voice-stack versions.
- `scripts/install.sh`, `update.py` and `rollback.sh`: deployment truth.

The Control Centre command list is generated from the action registry and
registered vocabulary. Do not create another hand-maintained command list.

Browser, Notes, Mail, Calendar and Office are compatible application roles,
not executable aliases. Add a candidate through `profile.py`, detection and
the preferred-app regression together. Keep Linux's generic mail handler
labelled as the system default; keep concrete clients separately named. Never
admit every Utility-category desktop entry merely to expose one notes app.
Launch detected desktop entries through GIO so the desktop owns field codes,
Flatpak forwarding and activation. Never parse an `Exec=` string into a shell
command, and keep post-launch window verification on fixed reviewed classes.

## Command-system update map

Every spoken command change must be traced through this whole path:

1. `action_registry.py` defines the allowlisted action ID, user-facing label,
   examples, risk and whether Qwen may see it.
2. `vocabulary.py` defines deterministic phrases. Risky actions remain strict.
3. `custom_commands.py` maps built-in vocabulary entities to action IDs.
4. `__init__.py` registers the OVOS intent and handler; a focused module owns
   the implementation.
5. `router_catalog()` exposes only reviewed low-risk actions plus enabled app
   operations. Qwen returns an action ID only; it never returns executable
   text. Newly enabled apps and saved spoken names flow into this catalogue and
   Whisper hints through the existing capability profile.
6. The Control Centre Commands page derives its list from the registry and
   vocabulary. Update those sources; do not patch a second GUI command list.
7. Update routing, collision, inventory and failure-regression tests, then the
   current command reference and `docs/releases.md`.

If any one of these layers is missing, the command change is incomplete.

## Non-negotiable boundaries

- Never execute model output, arbitrary spoken shell text, arbitrary URLs or
  spoken filesystem paths.
- Qwen may return only an enabled, allowlisted action ID. Newly detected apps
  may gain only the reviewed application operations.
- Keep strict matching for destructive, privacy-sensitive and power actions.
- Recheck focused-window identity before typing or submitting text.
- Introduce no listening port. Preserve the existing local Ollama boundary.
- Keep Media and File Search as separate plugins; do not fold them into the
  dispatcher merely for convenience.
- Preserve user configuration, models, enabled apps, spoken names, personal
  commands, shortcuts and private helpers during updates.
- Keep observed laptop inventory separate from a proposed runtime. Record every
  intentional dependency change, freeze the complete closure and validate its
  actual wheel hashes. V4 dependency checks reject all conflicts; do not restore
  the historical NumPy exemption or edit upstream metadata to hide a failure.
- Keep future login enablement separate from current Run/Stop controls. Preserve
  explicit auto-start choices across updates, launch only the quiet tray at
  login, and restore enablement/files if a preference change fails. Only the
  explicit quiet voice-login launch requests the stopped voice units once.
  Tray login and voice login have independent preferences in General; a tray
  launch alone never starts voice. Retain legacy combined settings on migration. Leave
  running or muted services and manual tray opens alone; never poll-restart.
- Run normal build, install, update, test and repair work as the desktop user.
  Never run the repository, pip, tar extraction or a whole upstream installer
  with `sudo`, and never use a root-owned checkout or temporary directory.
- A protected polkit directory alone must not require administrator authentication
  for routine deployment. Check the exact five native worker identities through
  read-only system-manager properties, without sudo or password prompts. Proceed
  only if every worker is not-found/inactive with no fragment or drop-ins and all
  other native deployment paths/receipts are absent. A hidden rule is uninspected,
  not declared missing; stale rule review belongs to native isolation setup.
  Existing/loaded workers, visible rules, Ollama policy or unknown checks block.
- Use private user-owned staging under `~/.local/state/jarvis`; release builds
  use a private temporary path beside the output. No launcher may retain a
  staging, `/tmp`, root-temporary or deleted-interpreter shebang. Administrator
  access is only for a missing operating-system package or an explicitly
  bounded upstream system-preparation step, or explicitly reviewed V4 native
  isolation service data. Prepare the private candidate and test removal and
  failure recovery first. Owner-terminal native commands install/remove data;
  never execute generated review text as a root script. Worker Python remains
  the ordinary user with no effective capabilities and NoNewPrivileges. Only
  the exact account, five static unit names and start/stop/restart verbs may
  receive a polkit grant. Activation verifies only its exact public native rule
  with fixed native stat/checksum commands using cached owner authorisation;
  it must never request/read a password or other root file. A temporary-policy
  pass proves no actual-service, model or mediated egress enforcement.
- Do not publish machine names, usernames, paths, IP addresses, credentials,
  logs or private helper contents.
- Public dependency manifests contain reviewed installer pins and hashes only.
  Keep raw runtime captures, observed model digests and source-install indicators
  in private evidence outside Git. Packaging and release scans must reject
  `runtime-observed-*`, including untracked captures and backups.

## Change discipline

1. Start from the current tree and tests; do not rebuild from an old snapshot.
2. Make one bounded behaviour change and add its failure-regression test.
3. Update the action registry, vocabulary, Qwen candidates, GUI-derived command
   inventory and documentation together when a spoken command changes.
4. Preserve unknown configuration fields. Flag contradictions instead of
   guessing. Move clearly historical material to `docs/history/`.
5. Label claims **VERIFIED**, **PLANNED** or **HISTORICAL**. Never silently
   remove a decision, security requirement or unresolved issue.
6. Show meaningful proposed documentation deletions separately.
7. Do not push, tag, publish, install on a live machine or change repository
   settings without explicit approval immediately before that action.
8. Record each release once in `docs/releases.md`. Put reusable fixes in
   `docs/troubleshooting.md`, durable choices in `docs/12-decisions.md` and old
   investigation detail in `docs/history/`; link to them instead of repeating
   the same update narrative across multiple current documents.
9. A short operation lock must not be inherited by a long-lived subprocess or
   playback monitor. Explicitly close its descriptor in every background child
   and add a regression that acquires the lock while that child remains alive.

## Required validation

Run at least:

```bash
python3 scripts/validate_refactor.py
python3 scripts/test-v3-routing.py
python3 scripts/test-qwen-safe-workflows.py
python3 scripts/test-update-security.py
bash scripts/test-deployment.sh
```

Before a release, also run the non-executing routing benchmark, build the
archive and plugin wheels once, verify their checksums, extract the final
archive into a clean directory and rerun the complete suite from that copy.
Live microphone, wake-word, GUI and desktop focus behaviour must be reported
as live tests; never relabel offline simulation as live evidence.

## Release hygiene

- Keep the README concise and user-facing; put implementation detail in the
  linked focused documents.
- Keep one version across `pyproject.toml`, `compatibility.json` and
  `deployment-manifest.json`.
- Pin CI actions to immutable commits.
- Publish only the validated archive, checksum and independently versioned
  plugin wheels. Verify the public tag, commit and asset digests afterwards.
- Preserve OVOS configuration, models, application selection, defaults, spoken
  names, personal commands, shortcuts, listening sound and private unlisted
  helpers in both success and rollback tests.
