# Architecture

**VERIFIED in source:** `deployment-manifest.json` inventories the Jarvis modules,
helpers, profiles and optional desktop files. `scripts/validate_refactor.py` checks
that inventory, imports the skill and checks vocabulary. OVOS invokes the skill's
reviewed intents; desktop actions use fixed integrations, discovered application
IDs and focused-window guards. The local Qwen pipeline proposes only an
allowlisted action for the current request. Its result is data, never a shell
command. See `ovos_skill_jarvis_dispatcher/action_registry.py` and
`routing_runtime.py`.

The normal installer (`scripts/install.sh`) stages a release, backs up its managed
files, deploys within the desktop user's home and runs the doctor. The rollback
script restores the previous deployment. Fresh setup may invoke the reviewed
upstream OVOS installer for bounded system preparation; updates stage the full
hash-verified runtime and preserve host configuration and models. An exact
verified runtime can be reused. The tray and Control Centre
use system Python/GTK, separate from the OVOS virtualenv.

**VERIFIED in the 3.6 laptop trial:** wake word, hotkey, local speech, bounded
Qwen routing, writing, reading, volume restoration, Media, File Search and the
combined tray/Control Centre all crossed their real desktop boundary. Jarvis
bundles Media and File Search as separate skills; unrelated OCP providers stay
host-owned. Earlier comparison evidence remains in the
[historical audit](history/v2.4-audit.md).

**VERIFIED V4 design:** optional native isolation runs core, listener and audio
as the ordinary user with external IP access denied. Weather and Media use
separate online workers; desktop launches retain the user's ordinary session.
The selected guided install activates reviewed native policy and uses a
dedicated Jarvis Ollama, leaving general Ollama unchanged. Installation or a
configured-policy indicator alone does not prove actual network denial. The
same-user bus and X11 session remain trusted.
See [security](security-and-updates.md) and [release evidence](releases.md).

Dashboard and tray use one shared status/control path, including actual
isolated-worker mapping. No logs and temporary technical diagnostics keep
readiness outside historical logs; Recent Activity is a separate, bounded list
of reviewed action labels. See [maintenance](maintenance.md) and the
[logging policy](security-and-updates.md#application-logging-in-43).
