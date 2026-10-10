# Installer, updates and rollback

This page describes the current V4 deployment contract. Historical release
trials and their failures are retained under [`docs/history/`](history/README.md).

The 4.0.1 [guided isolation installer](core-isolation.md#guided-installer-401)
offers recommended protection on first installation, preserves existing choices,
and coordinates isolated upgrades without manual policy removal. It uses a
dedicated local Ollama and bounded administrator approval for native data only.
Older 4.0.0 updaters may still refuse active isolation; use the verified new
archive's installer as the desktop user for that first migration.

## Supported target

The reviewed desktop target is Linux Mint 22.3 on X11 and x86_64. The managed
voice runtime requires CPython 3.11.16, as recorded in
[`runtime-linux-x86_64-py311.json`](../voice/runtime-linux-x86_64-py311.json).
Package-level Python 3.10–3.13 checks do not establish installer compatibility.
Keep at least 8 GiB free on the staging/rollback filesystem, with additional
space for voice and Qwen models in their respective storage locations.
Ubuntu and Debian are compatible families, but require local acceptance testing.
Wayland and containerised desktop control are not supported.

For native isolation, use Mint 22.x with Polkit's JavaScript rules backend and
systemd network filtering. Mint 21.3's Polkit 0.105 cannot load the current
isolation permission rule. Creating `rules.d` alone does not enable that backend.
Use the [supported Mint upgrade](https://linuxmint-user-guide.readthedocs.io/en/latest/upgrade-to-mint-22.html)
instead of replacing the OS authorisation daemon or granting broad service control.

Run the read-only preflight before installation:

```bash
bash scripts/install.sh --check
```

The check validates the host, required desktop tools, selected applications,
OVOS APIs, voice entry points and the current capability profile. It changes no
installed file.

## Fresh installation

### Preparing Python

If CPython 3.11.16 is missing, use a separate user-managed installation. Install
`uv` through its [official instructions](https://docs.astral.sh/uv/getting-started/installation/),
then run as the desktop user:

```bash
UV_PYTHON_INSTALL_DIR="$HOME/.local/share/jarvis/python" \
  uv python install --no-bin cpython@3.11.16
```

This keeps OS Python and its aliases unchanged. Jarvis detects that fixed
private interpreter location when preparing an absent OVOS baseline. See
[uv's Python guide](https://docs.astral.sh/uv/guides/install-python/) for the
separate interpreter download. An existing OVOS environment with a different
Python version needs reviewed migration; do not delete it to force setup.

A fresh setup performs these bounded steps:

1. Check the host and offer missing system prerequisites.
2. Prepare the reviewed OVOS virtual environment and validate every launcher.
3. Prepare OpenWakeWord, Faster-Whisper `small.en`, Bella and the reviewed local
   Qwen model before switching environments.
4. Offer **Recommended**, **All** or **Custom** detected applications.
5. Install the dispatcher plus the separate Media and File Search skills.
6. Install the combined tray, Control Centre, menu entry and user services.
7. Start the services and run the health check.

Missing operating-system tools, system preparation explicitly requested by the
official OVOS installer, and selected native isolation service data are the
bounded administrator operations.
Jarvis 4.4.4 prepares an absent OVOS baseline using the already available
CPython 3.11.16 interpreter. It creates only a user virtual environment, a
loopback messagebus configuration and six fixed user service files. Existing
or partial service/configuration data requires review and is never overwritten.
Baseline preparation does not start or enable services; the staged installer
then installs the complete hash-verified runtime before normal activation.
It does not run the whole upstream installer as root or replace system Python.

The installation child keeps its controlling terminal, so an interactive OS
package prompt can work without reading passwords in Python. Noninteractive
updates need their OS prerequisites prepared in a terminal first. Isolation
compatibility and interpreter checks run before model preparation and the
native installation transaction; unsupported isolation is never downgraded.

**HISTORICAL 4.4.1 limitations:** automatic fresh OVOS setup invoked a
root-requiring upstream entry point as an ordinary user; its detached managed
child also could not obtain a new sudo password from the terminal. The revised
user baseline and terminal handoff address those separate failures. A failed
first installation can recover with genuinely absent user units, while unknown
unit state or surviving processes still blocks recovery.

The reviewed package set is recorded in
[`voice/reviewed-stack.json`](../voice/reviewed-stack.json). Exact voice pins,
source commits and hashes are in [`compatibility.json`](../compatibility.json).
Conflicting legacy YouTube providers are deliberately excluded; Jarvis Media
uses a bounded YouTube lookup and an enabled browser instead.

V4 uses the separately distributed, code-pinned runtime bundle. It verifies the
complete archive and all 296 wheel hashes, checks dependency closure, installs
into a private stage with `--no-index --no-deps --require-hashes`, and verifies
parity before switching. Bad or missing bytes stop without index fallback.
`--runtime-bundle PATH` accepts a saved verified ZIP; `--runtime-wheelhouse PATH`
accepts the complete reviewed wheels. `--runtime-source-build` is an explicit
investigation mode, not the normal hash-enforced release path. Python, OS tools
and uncached voice/Qwen models remain separate requirements; this is not a
complete offline fresh-machine installer.

General has independent **Start app minimised at login** and **Start voice
services at login** choices. Dashboard Run/Stop affects the current session.
Updates preserve both choices; opening the tray alone does not start voice.

Selected isolation is prepared and activated by the guided installer. A private
transaction permits only that installation/recovery while keeping native IP
policy in place. Rollback and uninstall outside that coordinator retain their
native-data guard; use reviewed removal first. Never bypass a remaining journal
or policy check.

## Upgrading an isolated installation

1. Download the new stable archive and checksum and verify SHA-256.
2. Extract into a new user-owned directory and run its `scripts/install.sh`
   as the desktop user. Keep the existing application selection unless you
   explicitly want to review it.
3. Existing isolation and microphone/startup preferences are preserved. A first
   migration from the older five-worker policy to the dedicated model asks for
   bounded administrator approval. Unchanged native data needs no new approval.
4. Wait for the private model and voice readiness and the final confirmation.
   An interrupted transaction must recover before another installation.

For recovery, use the verified new source outside the managed deployment:

```bash
python3 scripts/isolation_install.py -- --recover
```

Run without sudo. Changed source/native data blocks recovery for review. Do not
remove the journal, reset unrelated policy or assume installation proves actual
network denial. The [manual review guide](core-isolation.md) retains the older
4.0.0 removal procedure for rollback/uninstall and separately reviewed repairs.

## What an update owns

The release manages Jarvis code, its two bundled skills, generated helpers,
user-service templates, the tray and Control Centre. It does not own personal
desktop applications or Speech Note.

Updates preserve:

- OVOS configuration and downloaded models;
- selected apps, defaults and spoken names;
- personal commands and keyboard shortcuts;
- wake, microphone, voice and listening-sound choices;
- existing Speech Note models and settings;
- unlisted private helpers.

An existing application mode and checkbox map are copied exactly unless the
user explicitly chooses a new mode. `all-detected` remains a live policy;
Custom remains a fixed allowlist. Unknown intent-pipeline layouts, custom wake
models or conflicting local-model settings stop for review instead of being
silently replaced.

## Transaction and rollback

Installation and downloaded updates stage files under the user's private
Jarvis state directory. A clean
OVOS environment is built separately and validated for exact versions,
dependencies, entry points, Adapt compatibility, ONNX wake loading, Bella and
permanent launcher paths. The live environment changes only after these checks
pass.

Before replacement, Jarvis retains the managed files and complete previous
OVOS virtual environment under `~/.local/state/jarvis/backups/`. Any failure
after mutation restores both. A successful update still retains the backup:

```bash
jarvis-health-check
jarvis-update rollback
```

Rollback refuses to overwrite files edited after the update without review.
Installer tests inject failures before and after the environment switch to
verify restoration.

## Stable release updates

The tray and Control Centre query the repository's latest stable GitHub
Release. They show the installed version, latest version and publication date.
Nothing installs automatically.

```bash
jarvis-update check
jarvis-update install
```

The updater downloads the matching archive and checksum over HTTPS, verifies
SHA-256, and rejects unsupported archive layouts, links, traversal, duplicates,
overlong paths, excessive entry counts and excessive sizes. It then invokes the
same transactional installer. SHA-256 detects corruption; publisher
authentication still depends on obtaining the release through a trusted GitHub
channel. See [Security and updates](security-and-updates.md).

When an update is started from the Control Centre, the successful transaction
starts a fixed user-space relaunch helper, closes the old window, waits for its
process to exit and opens the newly installed Control Centre on the Updates
page. The combined tray is also restarted idempotently by the installer. While
that exact update is active, **Stop update** performs bounded process-group
termination; closing the window offers the same recovery after confirmation.

## Speech Note and live acceptance

Jarvis preserves Speech Note rather than editing its opaque rules. The Voice
page explains the optional additive regex that removes the wake phrase during
continuous dictation. If the wake phrase changes, that rule must change too.

Automated tests do not prove microphone, speaker, GPU or third-party website
behavior. After installing, verify the wake word and hotkey, volume restoration,
one desktop command, writing, normal and 2× reading, media, and service
autostart. Use `jarvis-report` for a bounded diagnostic bundle if a check fails.

## Uninstall

The Control Centre exposes the guarded uninstaller. Jarvis components, the
Qwen model, retained settings/history and the complete OVOS environment are
separate explicit choices. Speech Note and unrelated desktop applications are
never silently removed.
