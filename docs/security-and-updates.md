# Security and update policy

## Supported foundation

This release supports an x86_64 Linux desktop in an X11 session, with OVOS
installed in the user's `~/.venvs/ovos` virtual environment. Linux Mint is the
only machine-validated workstation target; Ubuntu and Debian are expected-
compatible families that still require `scripts/install.sh --check` and local
acceptance testing.

Wayland is not supported because the reviewed desktop controls use X11 tools.
Containerised OVOS is not the supported desktop-control deployment because a
container would require broad access to the host display, input, clipboard and
audio. Qubes OS remains suitable for separating risky workloads, but it is not
the default interactive Jarvis host.

## Privilege boundary

Jarvis, its setup, updates, health checks and support reports run as the
desktop user. On a clean laptop, the installer can invoke the reviewed official
OVOS installer and install missing command-line desktop-control prerequisites.
That initial preparation requests administrator access because OVOS and the
operating-system packages require it. It does not install desktop applications,
create users or edit sudo rules. Existing OVOS installations are not replaced.

The OVOS source is fetched from the official OpenVoiceOS repository at the
exact commit recorded in `compatibility.json`, verified before execution and
configured for a virtualenv install with telemetry, the LLM fallback and extra
community skills disabled. After preparation, Jarvis and its normal controls
remain within the desktop user account.

The local voice path is reproducible: wake word, VAD, Faster Whisper, PhōnNX,
Bella and the supporting pronunciation/runtime packages use the versions
recorded in `compatibility.json`. The installer deliberately omits unrelated
CUDA and agent packages; they are neither required for Bella on CPU
nor appropriate for a portable desktop installation.

Jarvis does not elevate the complete official OVOS installer. Its pinned
archive is verified, downloaded and extracted under private user-owned Jarvis
state, then launched as the desktop user. The upstream installer may request
administrator access for its own operating-system preparation. Ordinary
updates use the same user-owned state boundary and cannot leave root-owned
temporary files or staging-path launchers behind.

Claude Desktop and ChatGPT Desktop are launched only into ordinary chat. Jarvis
does not open Claude Code, Cowork, ChatGPT Codex or Work, approve their prompts,
or install MCP tools. Hermes remains the intentional local assistant. Private
agent infrastructure is outside normal setup and updates.

X11 applications in the same session can generally observe or inject desktop
input. The allowlists reduce what Jarvis itself can request, but they do not
turn X11 into a security boundary. Keep the OVOS message bus local to the
machine and do not expose it to an untrusted network.

## Release integrity

`scripts/build-release.sh` writes both the release archive and a `.sha256`
sidecar. The checksum detects accidental corruption only when it is obtained
through a trusted channel. It does not authenticate the publisher. A signed
release requires a separately protected signing identity; no signing key is
created or silently managed by this repository.

Before installing a downloaded archive:

```bash
version=4.0.0
sha256sum --check "ovos-commands-$version.tar.gz.sha256"
tar -tzf "ovos-commands-$version.tar.gz"
```

## V4 safeguards

**VERIFIED in source and isolated tests:** generic writing and submission
refuse terminal windows and recheck the focused target. Prompts to the
tool-capable private agent require readback and an exact, single-use `send it`.
Reading clears its temporary clipboard text after a bounded handoff and never
restores a previous clipboard value. These controls reduce accidental execution
and exposure while keeping everyday desktop commands available.

Support reports redact common credentials and machine/location identifiers;
archives are created privately and published only when complete. No report is
uploaded automatically. Update redirects must remain HTTPS on reviewed GitHub
hosts, alongside checksum and extraction checks. Source/history and candidate
artifact scans are part of release validation, not a guarantee that reports
contain no sensitive content.

The complete V4 runtime has exact versions and wheel/source hash identities.
Default staged installation enforces all wheel hashes and rejects dependency
conflicts with zero exemptions. The reviewed laptop installation and scoped
voice/desktop functions are exercised. Installation receipts record provenance;
they do not rehash every installed file on each run. Model identities retain
explicit verification limits; a mutable tag is not a frozen digest.

Optional [native service isolation](core-isolation.md) keeps workers as the
ordinary desktop user and separates Weather/Media and desktop launches from
restricted core/listener/audio. Scoped actual IPv4/IPv6 TCP/DNS probes and
Ollama denial/local inference pass. Broader mediated/inherited sockets and native
recovery remain unverified. The same-user bus, plugins and X11 session remain
trusted; no defence against a compromised desktop user is claimed. Installation
alone does not activate isolation. Existing native data blocks a full normal
update until its reviewed deactivation/removal path is completed.

Production signatures remain deferred for the controlled small-client deployment.
Hermes sandbox/tool permissions and maintainer-account protections require their
separate review. The stable release uses existing passed behaviour checks and
scans/verifies its exact public assets; it does not certify every outstanding
laptop acceptance path. See [release record](releases.md).

## Updating Jarvis and OVOS

The default update source is `evok3dx/OVOS-Commands`. If it moves later, an
installation can override the source in `~/.config/jarvis/update.json` as
`{"repository":"OWNER/REPOSITORY"}`. A silent monthly read-only timer records
whether a stable release is available. It never installs automatically and
shows no popup. The tray adds a red badge after a newer version is successfully
detected. Use `jarvis-update check`, review the result, then run
`jarvis-update install`. The updater downloads the archive and checksum over
HTTPS, verifies SHA-256, rejects unsafe archive paths and invokes the normal
transactional installer. `jarvis-update rollback` restores the previous Jarvis
deployment.

On an existing installation, the transaction updates release-managed Jarvis
code and helpers but preserves machine-owned OVOS configuration, selected
applications, personal commands, keyboard shortcuts, listening sound and
unlisted private helpers and downloaded models. Jarvis stages the reviewed
OVOS packages in a clean virtual environment and saves
the previous entire virtualenv for rollback. Fresh installations use the same
reviewed target; see [migration details](07-installer-updates.md).

This experimental repository may be private between announced update windows.
Scheduled checks fail quietly while it is private or the laptop is offline.
For an update window, make the repository public, publish a tested immutable
GitHub Release, ask the small user group to update, and make it private again
afterward. Because the public window may be shorter than one month, users
should select **Check for updates** in the tray when an update is announced.
After detection, selecting the version-labelled tray entry starts the same
manual installer and confirmation prompt. A normal push is never treated as a
client release.

OVOS and Jarvis updates are deliberately supervised rather than unattended:

1. Back up `~/.config/mycroft/mycroft.conf` and create a `jarvis-report`.
2. Run `python3 scripts/check_upstream.py` to see which reviewed projects moved.
3. Re-run the official OVOS virtualenv installer or its documented update flow.
4. Run `bash scripts/install.sh --check`, then install this Jarvis release.
5. Run `jarvis-health-check` and exercise critical voice commands.
6. Use `jarvis-update rollback` if the Jarvis deployment regresses. Restore the
   OVOS configuration backup separately if the upstream update changed it.

GitHub Actions are pinned to reviewed commit SHAs. For future releases, enable
GitHub release immutability only after every asset is attached to a draft;
immutability prevents later tag or asset replacement and supplies provenance
for the published release. The workflow tests this skill against current OVOS
Python APIs. It reports upstream movement but never updates a workstation or
dependency by itself.

## AI-assisted maintenance

`jarvis-report` produces a bounded, private diagnostic snapshot and embeds
instructions requesting a patch. It never uploads, applies or deploys that
patch. Review the archive before sharing and review any proposed patch before
running the normal validation and isolated deployment tests.
Home paths, usernames, common credential shapes and OVOS session location
coordinates are redacted from its optional logs. Control Centre Recent Logs
uses the same location boundary, but recognised utterances can still be
sensitive and must be reviewed before sharing.
