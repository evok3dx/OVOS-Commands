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
The reported versions and media caveats are in [OVOS voice and media](06-ovos-voice.md).
The `ovos-ww-plugin-openwakeword` NumPy declaration remains a warning for the
Brain's NumPy 2/ONNX setup. Do not silence it by downgrading the live stack.

**V3 local setup:** Ollama must already be installed and running. If its exact
reviewed Qwen model is missing, the installer asks to download it before any
Jarvis files change; declining stops installation. The saved router settings
are backed up before the installer adds the Media and Qwen pipeline stages.
On existing hosts, unrelated OVOS routing entries stay in place; an explicit
conflicting persona fallback or different configured model stops for review.
Media and File Search install from bundled source without resolving OVOS voice
dependencies. Missing `yt-dlp` is installed in the OVOS virtualenv; an existing
version is left alone. The third-party Whisper hint installer checks the
installed `small.en` plugin source and makes its own backup. Unknown revisions
are reported and left untouched; a `--no-restart` install cannot apply the
live-listener patch.
Before replacing an existing separately installed Media or File Search skill,
preflight checks that any recorded local installer source still exists. Without
that source, rollback cannot reinstall the previous skill, so V3 stops before
changing Jarvis and asks the owner to restore the original package.

The previous standalone microphone autostart is retired on upgrade only if its
name and launch command match Jarvis's generated entry. It has been included in
the transaction backup and can be restored by rollback. Brain's final snapshot
already has the old entry disabled and the combined icon active. The one tray
icon shows Jarvis microphone and update indicators. See
[`deployment-manifest.json`](../deployment-manifest.json) for managed files and
[`scripts/test-deployment.sh`](../scripts/test-deployment.sh) for isolated fresh,
upgrade, failure and rollback checks.

`--check` changes no installed files. The static checks and isolated deployment
test do not certify live voice or external YouTube access. Re-run the check and
try wake word, a desktop command and spoken stop on each host after installation.

The Control Centre's **Maintenance → Check for updates** checks the published
stable GitHub release. **Install available update** shows a confirmation once,
then passes that approval to the same `jarvis-update` installer used in a
terminal. The installer checks the release archive checksum before deploying;
its normal backup and rollback apply. The version comparison also recognises
an older V3 release candidate as older than V3 final. The GUI cannot fetch a
draft pull request or an unpublished release.
