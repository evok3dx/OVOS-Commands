# Installer and updates

**VERIFIED in code:** `scripts/install.sh` runs static validation and a host
preflight before staging deployment. V3.1 copies the normal
`~/.venvs/ovos` virtualenv, installs the Brain-tested core and voice versions in
that copy, and switches environments only after the staged version passes its
version and Bella checks. The previous entire virtualenv and managed Jarvis
files are saved under `~/.local/state/jarvis/backups/`. Failed installation
restores both; `bash scripts/rollback.sh` can restore them explicitly.
Downloaded models, OVOS configuration, shortcuts, sounds, saved capabilities
and unlisted private Brain helpers remain on the host.

On a new workstation, normal setup can offer the pinned official OVOS installer
and missing minimal desktop tools. That bootstrapping is the one administrator
access boundary. It stages the same reviewed Brain-compatible core and voice
versions from `compatibility.json`. The virtualenv must use Python 3.11 or newer
because the reviewed PhōnNX source requires it; existing custom OVOS Python
paths need separate review. The 110-package Brain inventory also includes
optional skills and media providers, which are not all installed by Jarvis.
The reported versions and media caveats are in [OVOS voice and media](06-ovos-voice.md).
The `ovos-ww-plugin-openwakeword` NumPy declaration remains a warning for the
Brain's NumPy 2/ONNX setup. The installer places Brain's exact NumPy version
last without dependency resolution; doctor continues to report the metadata
conflict. We have not reproduced an actual full package installation here, so
the first laptop test must check wake, transcription and Bella before calling
the migration verified on a second machine.

**V3.1 local setup:** Ollama must already be installed and running. If its exact
reviewed Qwen model is missing, the installer asks to download it before any
Jarvis files change; declining stops installation. The saved router settings
are backed up before the installer adds the Media and Qwen pipeline stages.
On existing hosts, unrelated OVOS routing entries stay in place; an explicit
conflicting persona fallback or different configured model stops for review.
Media and File Search install from bundled source without resolving OVOS voice
dependencies. Missing `yt-dlp` is installed in the OVOS virtualenv; an existing
version is left alone. The third-party Whisper hint installer checks the
installed `small.en` plugin source and makes its own backup. Unknown revisions
are reported and left untouched; a `--no-restart` install cannot change the
OVOS stack or apply the live-listener patch.
Before replacing an existing separately installed Media or File Search skill,
preflight checks that any recorded local installer source still exists. Without
that source, rollback cannot reinstall the previous skill, so installation stops before
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
try wake word, 1× and 2× reading, a desktop command and spoken stop after
installation. The laptop trial also checks Firefox search, volume and the
single “I am ready” announcement. Report failures before updating Brain.

The Control Centre's **Maintenance → Check for updates** checks the published
stable GitHub release. **Install available update** shows a confirmation once,
then passes that approval to the same `jarvis-update` installer used in a
terminal. The installer checks the release archive checksum before deploying;
its normal backup and rollback apply. The version comparison also recognises
an older V3 release candidate as older than V3 final. The GUI cannot fetch a
draft pull request or an unpublished release.
