# Security and update policy

Jarvis keeps Recent Activity in a bounded in-memory session list.
It contains reviewed action identifiers and results, never dictated text,
search queries, window titles or clipboard contents. Appearance settings apply
only to Jarvis and are included in private settings exports. Maintenance's
Isolation status inspects native policy; it does not claim actual network
verification. Explicit [GUI checks](core-isolation.md#control-centre-status-and-checks)
report current-worker/model results and their limits. See the
[release record](releases.md) for validation status.

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
create users or edit sudo rules. Machine-owned settings and models are preserved; the managed OVOS environment
is staged and replaced only after validation.

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

Optional native isolation has a separate, explicit administrator boundary for
reviewed service and policy data only. Worker Python still runs as the desktop
user. An older installed updater can block deployment until its reviewed
[upgrade procedure](07-installer-updates.md#upgrading-an-isolated-installation)
is completed; never run the installer or generated Python with sudo.

The 4.0.1 [guided isolation installer](core-isolation.md#guided-installer-401)
recommends isolation for first installs and preserves existing choices. It adds
one dedicated, ordinary-user Ollama on `127.0.0.1:11435`, disables cloud features
and applies the reviewed kernel IP policy. General Ollama is unchanged. Model
calls never fall back between instances. Upgrades retain native policy and use a
process-bound recovery journal; unchanged native data requires no new approval.
Supplied live recovery/migration and readiness passed. **VERIFIED post-release
on 1 October 2026:** the dedicated daemon generates locally and denies tested
external IPv4/IPv6 TCP connections, with unchanged daemon identity and successful
outside controls before/after. The voice-worker collector independently passes
IPv4/IPv6 TCP and direct DNS/UDP tests while preserving local connections.
See the [scoped live evidence](releases.md); fresh installation and broader
mediated/inherited paths remain unverified.

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
version=4.4.0
sha256sum --check "ovos-commands-$version.tar.gz.sha256"
tar -tzf "ovos-commands-$version.tar.gz"
```

## V4 safeguards

**VERIFIED in source and isolated tests:** generic writing and submission
refuse terminal windows and recheck the focused target. Prompts to the
tool-capable private agent require readback and an exact, single-use `send it`.
Reading never restores a previous clipboard value. The 4.4.1 clipboard
supervisor gives its foreground owner an independent
15-second lifetime and a one-second forced termination backstop. Before ending
it, normal cleanup or expiry explicitly clears only the verified owner window
and process, with an atomic ownership check. This addresses Cinnamon's cache
restoration while preserving later user copies, including identical text.
**VERIFIED:** normal cleanup passed on the tested Cinnamon desktop; independent
expiry and later-copy preservation passed process fixtures. Native/release
validation remains pending. Earlier owner-release-only trials failed live cleanup. Other applications or
clipboard-history extensions can retain separate copies; this is not secure
erasure of their history. Verification status is in the [release record](releases.md).
These controls reduce accidental execution
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
alone is not evidence of network enforcement. The guided 4.0.1 installer
preserves existing isolation or activates the selected reviewed policy; its
managed transaction retains native policy during upgrades. Older 4.0.0
installers still require the reviewed manual upgrade procedure.

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

This repository and its retained Git history are public. Source, documentation,
tags and published assets must therefore be suitable for public sharing.
Private diagnostics and helper contents belong outside Git. A normal push does
not update a client: the stable release and explicit installer remain separate.
Scheduled checks fail quietly when the laptop is offline or the repository is
unavailable. Publishing source does not publish an authenticated connector's
credentials; release workflows use a temporary job token, not a password stored
in the repository. Scans reduce accidental disclosure but are not a guarantee
that all history is free of sensitive material.

OVOS and Jarvis updates are deliberately supervised rather than unattended:

1. Back up `~/.config/mycroft/mycroft.conf` and create a `jarvis-report`.
2. Run `python3 scripts/check_upstream.py` to see which reviewed projects moved.
3. Maintainers review upstream changes, resolve the complete closure and verify
   exact wheel hashes before publishing another managed runtime. Do not update
   the frozen V4 environment independently with pip or an upstream installer.
4. Run `bash scripts/install.sh --check`, then install the published Jarvis
   release and its verified runtime through the normal managed transaction.
5. Run `jarvis-health-check` and exercise critical voice commands.
6. Use `jarvis-update rollback` if the managed deployment regresses. It retains
   the previous virtual environment as well as managed Jarvis files.

GitHub Actions are pinned to reviewed commit SHAs. For future releases, enable
GitHub release immutability only after every asset is attached to a draft;
immutability prevents later tag or asset replacement and supplies provenance
for the published release. The workflow tests this skill against current OVOS
Python APIs. It reports upstream movement but never updates a workstation or
dependency by itself.

## AI-assisted maintenance

### Application logging in 4.3

Live installation requires the coordinated service restart so an older running
worker cannot keep logging after the upgrade. The short-lived activity and
diagnostic readers also discard upstream output and relay only validated data.

**VERIFIED automated; owner laptop acceptance pending:** General provides
**No logs** by default and **Diagnostics for 5 minutes**. The managed OVOS
core, listener, audio, Weather, Media and bus suppress raw Python log messages
and direct stdout/stderr, including inherited playback output. Diagnostics
retain only component, severity, fixed event type, reviewed source label, line number,
allowlisted reason code and relative capture time in
bounded process memory. They contain no recognised speech, dictated text,
messages, queries, raw exception text or traceback. Capture stops and clears
automatically after five minutes even when the GUI is closed; a reboot,
expired control or invalid state defaults to No logs. Repeated selection
does not extend a running capture. No logs also clears the capture.

Current readiness uses private, overwritten process state identified by boot,
invocation and PID. It remains available when logging is off. Existing
release readiness markers remain only as a migration/recovery fallback.
Recent Activity stores fixed action labels in memory and displays the last
five minutes, independently of No logs or diagnostic mode. Restarting command
handling clears its activity session. **Dashboard → Refresh** requests the
current feed; it is not a transcript or a complete audit trail.
**Maintenance → Recent logs** and optional support-report diagnostics use the
bounded technical capture, not that activity list or historical raw journals.

In 4.4, reviewed logging sites map to fixed labels for Music stages and failures,
reading/application/browser/Qwen failures, empty transcription and Weather
stages. Only exact templates or reviewed failure sites are classified. The two
argument checks accept fixed Weather stage names or reading exit codes, never
user text. Labels come from constants, and relative time comes from the local
capture clock. Unknown informational traffic is omitted; unknown warnings and
errors retain only source and severity. IPC rejects additional fields, unknown
reasons and invalid times. Legacy fixed-field rows remain readable.

Recent Logs lists collector availability before event detail. A missing reply
can mean stopped, disabled or unavailable; it is not automatically a failure.
Ordinary deployments capture Media/Weather inside core rather than requiring
standalone collectors. A responding collector and a finished Weather stage do
not establish successful execution. Original exception messages are deliberately
unavailable. Use Dashboard state or a targeted private check when fixed reasons
are insufficient; empty output alone is not a health result.

This policy does not erase historical journals, old OVOS files, exported
reports or backups. Systemd can retain service lifecycle/exit records. Ollama,
Speech Note, audio/model caches and other applications have separate storage
and logging behaviour. The general Ollama instance and global journal policy
are unchanged. Do not describe this as system-wide zero retention.

`jarvis-report` produces a bounded, private diagnostic snapshot and embeds
instructions requesting a patch. It never uploads, applies or deploys that
patch. Review the archive before sharing and review any proposed patch before
running the normal validation and isolated deployment tests.
Home paths, usernames, common credential shapes and OVOS session location
coordinates are redacted from report fields. In the 4.3 candidate, optional
diagnostics and Control Centre Recent Logs use the bounded technical feed
above; raw historical journals are not collected. Previously exported reports
and pre-4.3 logs can still contain recognised utterances and need review.
