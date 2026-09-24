# Installer and updates

**VERIFIED in code:** `scripts/install.sh` runs static validation and a host
preflight before staging deployment. On an existing Jarvis/OVOS installation it
preserves the installed speech packages, downloaded models, OVOS configuration,
listen shortcut, sound and saved capabilities. It snapshots replaced managed
files under `~/.local/state/jarvis/backups/`, installs the manifest inventory,
and restores the previous deployment after an installation failure. Explicit
`bash scripts/rollback.sh` uses the same backup. User-owned custom settings and
unlisted private Brain helpers are outside the managed inventory.

On a new workstation, normal setup can offer the pinned official OVOS installer
and missing minimal desktop tools. That bootstrapping is the one administrator
access boundary. It then installs the pinned voice baseline in
`compatibility.json`; these pins describe **fresh installation**, not a demand
to downgrade an existing working stack. The reviewed Brain alpha-stack versions
in that file are a preserved-install diagnostic profile, not fresh-install pins.
The `ovos-ww-plugin-openwakeword` NumPy declaration remains a warning for the
Brain's NumPy 2/ONNX setup. Do not silence it by downgrading the live stack.

The previous standalone microphone autostart is retired on upgrade only if its
name and launch command match Jarvis's generated entry. It has been included in
the transaction backup and can be restored by rollback. The one tray icon now
shows Jarvis microphone and update indicators. See
[`deployment-manifest.json`](../deployment-manifest.json) for managed files and
[`scripts/test-deployment.sh`](../scripts/test-deployment.sh) for isolated fresh,
upgrade, failure and rollback checks.

`--check` changes no installed files. The static checks and isolated deployment
test do not certify live voice or external YouTube access. Re-run the check and
try wake word, a desktop command and spoken stop on each host after installation.
