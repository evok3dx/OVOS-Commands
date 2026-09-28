# Jarvis contributor and AI-agent guide

This file applies to the whole repository. Code and passing tests describe
current behaviour; `docs/12-decisions.md` records approved intent and security
constraints. Do not infer either from chat history or historical release notes.

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
- Use private user-owned staging under `~/.local/state/jarvis`. No launcher may
  retain a staging-directory shebang. Administrator access is only for missing
  operating-system packages or an upstream system-preparation step.
- Do not publish machine names, usernames, paths, IP addresses, credentials,
  logs or private helper contents.

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
