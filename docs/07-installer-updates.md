# Installer and updates

**VERIFIED in code:** `scripts/install.sh` runs static validation and a host
preflight before staging deployment. The 3.1.1 candidate creates a clean
virtualenv and installs 107 reviewed distributions from
[`voice/reviewed-stack.json`](../voice/reviewed-stack.json). It does
not copy packages from the old environment. The local dispatcher, Media and
File Search remain separate packages and install from this release. The live
environment is replaced only after exact-version, dependency, entry-point,
launcher, Adapt, ONNX and Bella checks pass. The previous entire virtualenv and
managed Jarvis files are saved under `~/.local/state/jarvis/backups/`. Failed
installation restores both; `bash scripts/rollback.sh` can restore them.
Downloaded models, OVOS configuration, shortcuts, sounds, saved capabilities
and unlisted private host helpers remain on the host.
An existing application's saved checkbox map is copied exactly, including an
older `all-detected` configuration. That mode is a live policy: profile loading
rescans and enables every reviewed local detection, so its GUI checkboxes can
expand without the installer rewriting the saved file. Choose `custom` mode
for a fixed allowlist. Updates preserve either policy.

**3.1.1 candidate, not released:** The 3.1 laptop trial exposed four
installer gaps: inherited `PIP_CONSTRAINT` could block the staged core,
pip-generated launchers still named the deleted staging directory, and the
default OpenWakeWord plugin selected TFLite despite NumPy 2. Most importantly,
copying the existing virtualenv retained old packages that conflict with the
new bus, Workshop and configuration APIs. The local patch
removes that constraint only for its reviewed staged install, retargets
launchers atomically (including copied older staging paths), and probes the
installed Hey Jarvis ONNX model before using it. It builds from a clean
environment and treats every dependency error as fatal except the documented
OpenWakeWord/NumPy metadata mismatch, which must pass a real ONNX load probe.
Fresh setup stores that
model's final virtualenv path. Upgrade migrates only the recognisable released
default to threshold `0.4`, pre-wake VAD off and the verified ONNX path.
Custom phrases, models and non-default thresholds stop for review. It waits
for core/listener readiness before considering the rollback transaction
successful. Offline tests cover an injected failure and full restoration;
the complete package resolver and spoken wake remain unverified on the laptop.
The first clean rc3 resolver run stopped safely before the virtualenv swap
because the two legacy YouTube packages require incompatible `tutubo` major
versions. Rc4 excludes both and must run the resolver again to expose any
later conflict.
The privileged official-installer scratch directory is created only for
one-time setup and removed by its exit trap. The staged launcher check
rejects a shebang pointing into that temporary directory instead of
installing it as a lasting entry point.

The candidate pins the coherent distribution set established from the final
reference snapshot, including Adapt, PHAL, skills, media providers and pipeline
plugins. It deliberately excludes the mutually incompatible legacy YouTube
Music provider and OCP YouTube plugin; the bundled Jarvis Media skill opens its
reviewed result in Brave and does not use either package.
The laptop's older versions and different pipeline are recorded in the
[3.1.1 trial checklist](v3.1.1-checklist.md). Saved app choices remain in
place; package matching alone does not prove a successful local response.
For a **fresh** installation, the candidate now starts with the recorded
reference system pipeline order (no persona or OCP stage), then adds Jarvis Media,
Qwen and the narrow unmatched-command stage. Upgrade recognises and replaces the older released persona/OCP
layout. An unknown custom pipeline stage stops installation for review instead
of being removed.

On a new workstation, normal setup can offer the pinned official OVOS installer
and missing minimal desktop tools. That bootstrapping is the one administrator
access boundary. It stages the same reviewed reference system-compatible core and voice
versions from `voice/reviewed-stack.json`. The virtualenv must use Python 3.11 or newer
because the reviewed PhōnNX source requires it; existing custom OVOS Python
paths need separate review. The snapshot records 110 distributions. The older
Jarvis dispatcher is installed from this release, and the two conflicting
legacy YouTube routes are excluded, leaving 107 packages in the staged stack.
The reported versions and media caveats
are in [OVOS voice and media](06-ovos-voice.md).
The `ovos-ww-plugin-openwakeword` NumPy declaration remains a warning for the
reference system's NumPy 2/ONNX setup. The installer places reference system's exact NumPy version
last without dependency resolution; doctor continues to report the metadata
conflict. We have not reproduced an actual full package installation here, so
the first laptop test must check wake, transcription and Bella before calling
the migration verified on a second machine.
During the first 3.1.1 candidate trial, the installer requested openWakeWord's
default TFLite model list and mistakenly expected an ONNX path; it rolled the
failed install back. The revised candidate explicitly requests the ONNX list,
checks the installed file and loads it before replacing the live virtualenv.
Model download and wake verification failures stop staging. A resumed laptop
trial must still confirm the actual configured listener and spoken wake.

**V3.1 local setup:** Ollama must already be installed and running. If its exact
reviewed Qwen model is missing, the installer asks to download it before any
Jarvis files change; declining stops installation. The saved router settings
are backed up before the installer adds the Media, Qwen and deterministic
unmatched-command pipeline stages.
On existing hosts, an unknown routing stage, explicit conflicting persona
fallback or different configured model stops for review.
Media and File Search install from bundled source without resolving OVOS voice
dependencies. Missing `yt-dlp` is installed in the OVOS virtualenv; an existing
version is left alone. The third-party Whisper hint installer checks the
installed `small.en` plugin source and makes its own backup. Unknown revisions
are reported and left untouched; a `--no-restart` install cannot change the
OVOS stack or apply the live-listener patch.
The same transaction applies an exact-source Dinkum 0.10.5a1 service guard and
keeps the reviewed upstream confirmation loop. Cue completion controls only
when background playback is lowered; microphone capture follows upstream timing
and cannot be delayed by an audio-service response. Normal record-end restores
immediately; a missing cue response falls back after three seconds and stalled
STT triggers the 15-second restoration fail-safe. Fresh setup recommends 20%
and enables Faster-Whisper VAD. Upgrade migration changes only the exact former
Jarvis 15% default and an absent VAD choice; custom values remain untouched.
Unknown listener source stops installation before service restart. An installed
rejected confirmation gate is restored to the exact reviewed upstream source,
with both files covered by the main rollback transaction.
The current guard snapshots current volume
for each command with a bounded query and skips ducking when no trustworthy
restore target is available; it never substitutes the service-start value.
Before replacing an existing separately installed Media or File Search skill,
preflight checks that any recorded local installer source still exists. Without
that source, rollback cannot reinstall the previous skill, so installation stops before
changing Jarvis and asks the owner to restore the original package.

The previous standalone microphone autostart is retired on upgrade only if its
name and launch command match Jarvis's generated entry. It has been included in
the transaction backup and can be restored by rollback. reference system's final snapshot
already has the old entry disabled and the combined icon active. The one tray
icon shows Jarvis microphone and update indicators. See
[`deployment-manifest.json`](../deployment-manifest.json) for managed files and
[`scripts/test-deployment.sh`](../scripts/test-deployment.sh) for isolated fresh,
upgrade, failure and rollback checks.

**V3.2 candidate:** installation enables the existing official `ovos.service`
user target so OVOS starts at login, then starts the combined tray after a
short desktop-session delay. It also installs one **Jarvis OVOS** Start Menu
shortcut that opens the existing Control Centre. Opening that shortcut also
restores the combined tray if the user previously chose **Quit tray**; the
tray's local file lock prevents a duplicate icon. These files and the previous
service-enable state are transaction backups and rollback restores them. No
new daemon or port is added. The install summary points Speech Note users to
the Voice-page wake-filter guide; the installer never rewrites Speech Note's
opaque rules, models or voice settings.

Fresh setup now defaults to **Recommended detected applications** instead of
the live `all-detected` policy. The terminal and GTK setup both offer
Recommended, All and Custom choices. Recommended enables only installed
everyday apps from the curated set, including detected Standard Notes, Proton
Mail, Proton Calendar and System Calendar; private Codex/Claude agents appear only
when their two fixed helpers exist. An upgrade preserves the existing mode,
checkbox map, spoken names and personal commands rather than replacing them.
An interactive upgrade offers to review that choice; a legacy empty
`core-only` profile defaults to review. Unattended upgrades still preserve it.

`--check` changes no installed files. The static checks and isolated deployment
test do not certify live voice or external YouTube access. Re-run the check and
try wake word, 1× and 2× reading, a desktop command and spoken stop after
installation. The laptop trial also checks Firefox search, volume and the
single “I am ready” announcement. Report failures before updating reference system.

The Control Centre's final **Updates → Check now** tab checks the published
stable GitHub release. When one is recorded, Overview and Updates show the
installed version, latest version and release date, and the green **Update
Available (version)** button shows a confirmation once,
then passes that approval to the same `jarvis-update` installer used in a
terminal. The installer checks the release archive checksum before deploying;
its normal backup and rollback apply. The version comparison also recognises
an older V3 release candidate as older than V3 final. The GUI cannot fetch a
draft pull request or an unpublished release.

**V3.5 candidate:** the update refresh no longer calls an unimported helper;
the displayed status is read through the same tested `update_status()` path as
the periodic Overview refresh. Maintenance now exposes the guarded uninstaller.
Its Qwen model, settings/history and complete OVOS removal choices are separate
and explicit. The bundled uninstall test verifies that Speech Note is retained.
Benchmark reports default to `~/Downloads`, not a hidden state directory.
