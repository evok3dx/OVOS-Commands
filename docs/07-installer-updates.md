# Installer, updates and rollback

This page describes the current 3.7.3 deployment contract. Historical release
trials and their failures are retained under [`docs/history/`](history/README.md).

## Supported target

The fully tested desktop target is Linux Mint on X11, x86_64 and Python 3.11.
Ubuntu and Debian are compatible families, but require local acceptance testing.
Wayland and containerised desktop control are not supported.

Run the read-only preflight before installation:

```bash
bash scripts/install.sh --check
```

The check validates the host, required desktop tools, selected applications,
OVOS APIs, voice entry points and the current capability profile. It changes no
installed file.

## Fresh installation

A fresh setup performs these bounded steps:

1. Check the host and offer missing system prerequisites.
2. Prepare the reviewed OVOS virtual environment and validate every launcher.
3. Prepare OpenWakeWord, Faster-Whisper `small.en`, Bella and the reviewed local
   Qwen model before switching environments.
4. Offer **Recommended**, **All** or **Custom** detected applications.
5. Install the dispatcher plus the separate Media and File Search skills.
6. Install the combined tray, Control Centre, menu entry and user services.
7. Start the services and run the health check.

Missing operating-system tools and any system preparation explicitly requested
by the official OVOS installer are the only one-time administrator boundary.
Jarvis downloads and extracts the pinned upstream installer in private
user-owned state and launches it as the desktop user; only the upstream system
step may elevate. Normal installation, updates and daily use remain user-space.

The reviewed package set is recorded in
[`voice/reviewed-stack.json`](../voice/reviewed-stack.json). Exact voice pins,
source commits and hashes are in [`compatibility.json`](../compatibility.json).
Conflicting legacy YouTube providers are deliberately excluded; Jarvis Media
uses a bounded YouTube lookup and an enabled browser instead.

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
page. The combined tray is also restarted idempotently by the installer.

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
