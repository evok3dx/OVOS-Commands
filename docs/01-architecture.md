# Architecture · V3 candidate

**VERIFIED in source:** `deployment-manifest.json` inventories the Jarvis modules,
helpers, profiles and optional desktop files. `scripts/validate_refactor.py` checks
that inventory, imports the skill and checks vocabulary. OVOS invokes the skill's
reviewed intents; desktop actions use fixed integrations, discovered application
IDs and focused-window guards. The optional Qwen pipeline proposes only an
allowlisted action for the current request. Its result is data, never a shell
command. See `ovos_skill_jarvis_dispatcher/action_registry.py` and
`routing_runtime.py`.

The normal installer (`scripts/install.sh`) stages a release, backs up its managed
files, deploys within the desktop user's home and runs the doctor. The rollback
script restores the previous deployment. Fresh setup may invoke the reviewed
upstream OVOS installer with administrator access; updates keep installed OVOS
speech packages and host configuration in place. The tray and Control Centre
use system Python/GTK, separate from the OVOS virtualenv.

**PLANNED:** confirm the combined checkout with real speech on both Brain and
i7 laptop; consolidate repeated app definitions only after that baseline is
captured. Media providers are installed in OVOS, not managed by Jarvis's skill
manifest. The Brain's new provider stack is recorded in the
[living audit](v2.4-audit.md), with its limits.
