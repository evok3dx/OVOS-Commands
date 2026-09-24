# Historical README · 2.3.1

**HISTORICAL:** captured from Git `3afc733` before the V3 rewrite. Paths, tray menus and version numbers here describe the earlier release, not current behaviour. Internal links were adjusted for this archive location.

# OVOS Commands

> [!WARNING]
> **Experimental software.** This project is tested for a small, known group
> of Linux Mint workstations. Review the limitations and run the preflight
> check before installing it on another machine.

Allowlisted voice control for the Linux Mint Jarvis workstation. Routine
commands run locally and do not require a language model.

Repository: [evok3dx/OVOS-Commands](https://github.com/evok3dx/OVOS-Commands)

The repository may be private between announced update windows. Existing
installations continue to work while it is private, but anonymous update
checks and downloads are available only while it is public.

## Current source status

This tree is version `v2.3.1`. Check GitHub Releases for the latest published
version; the `main` branch can contain newer validated fixes before a new
release is published.
Do not infer a published release from the name of a local extracted/downloaded
folder.

On 16 September 2026, cross-machine testing between the Brain and a second
Linux Mint laptop identified and fixed a generic X11 window-discovery bug:
portable application definitions may contain several reviewed window-class
alternatives separated by `|`, and `jarvis-app-window` must test each literal
candidate independently. Treating the full `|`-joined value as one literal
string caused an already-open Standard Notes window to be reported as missing.

The validated diagnosis and portability rules are documented in
[`docs/window-focus-and-app-integration.md`](../window-focus-and-app-integration.md).

## Quick start

Download the `ovos-commands-2.3.1.tar.gz` archive and matching `.sha256` file
from the [latest GitHub release](https://github.com/evok3dx/OVOS-Commands/releases/latest),
then verify and install it:

```bash
cd ~/Downloads
sha256sum --check ovos-commands-2.3.1.tar.gz.sha256
install_dir="$(mktemp -d "$HOME/Downloads/ovos-2.3.1-install.XXXXXX")"
tar -xzf ovos-commands-2.3.1.tar.gz -C "$install_dir"
cd "$install_dir/ovos-commands-2.3.1"
bash scripts/install.sh --check
bash scripts/install.sh
```

From a trusted Git checkout, the equivalent development flow is:

```bash
python3 scripts/validate_refactor.py
bash scripts/install.sh --check
bash scripts/install.sh
```

On a clean Linux Mint laptop, the installer first offers to prepare the
reviewed official OVOS virtualenv baseline and any missing minimal desktop-
control prerequisites. That one-time preparation uses administrator access;
it installs OVOS and command-line dependencies, not desktop applications.
Minimal systems also receive Git because the official OVOS installer requires
it for its version label and intent cache.
OVOS is installed with telemetry, its LLM fallback and extra community skills
disabled. Existing OVOS installations are left alone.

After preparation, the installer validates the complete inventory, backs up
every replaced component under
`~/.local/state/jarvis/backups/`, deploys one coherent version and restarts
Jarvis once. A failed transaction restores the previous deployment. It works
from a Git checkout or an extracted release archive. Jarvis installation,
configuration, updates and daily operation remain user-space.

An update replaces only release-managed Jarvis code and the helpers listed in
`deployment-manifest.json`. It preserves the machine's OVOS configuration,
application selection, personal commands, keyboard shortcuts, listening sound
and any private helpers that are not part of the release. An existing voice
stack and its downloaded models are also left untouched. Complete voice and
desktop configuration is performed only for a fresh installation.
Desktop GTK tools always use Mint's `/usr/bin/python3`, so installation and
tray setup remain reliable even when the OVOS virtual environment is active.

The installer also prepares the reviewed, fully local voice stack used by the
Brain: OpenWakeWord for the trained **Hey Jarvis** model, Silero VAD, Faster
Whisper `small.en`, and PhōnNX/Kokoro **Bella**. Exact working component
versions are centralised in `compatibility.json`. The first install downloads
the speech models into the user's caches and may take several minutes; it does
not use `sudo`. The short listening beep is shipped inside this release, so it
does not depend on a file hidden inside a particular OVOS virtualenv.

First setup offers one simple choice:

1. all detected supported applications;
2. core voice controls only;
3. a custom selection from detected supported applications.

The app-control selection never installs applications; it only enables apps
that are already present. Reopen the same selection later from the tray or
with `jarvis-setup`. Legacy `--profile` support exists only to migrate an older
deployment.

After Jarvis is installed, setup may separately offer **Speech Note** as an
optional local dictation and reading add-on. It is opt-in, defaults to no, and
uses Flatpak's per-user installation without `sudo`. If Speech Note is already
present, Jarvis preserves its models and settings and connects automatically.
New installations require a one-time model and voice choice in Speech Note;
those downloads are deliberately not guessed or started automatically. The
same guided setup remains available from the Jarvis tray.

`bash scripts/install.sh --check` remains a read-only diagnostic for machines
whose prerequisites already exist. On a clean laptop, run the normal installer
first so it can offer the reviewed setup.

Restore the most recent deployment with:

```bash
jarvis-update rollback
```

The former `scripts/deploy-modular-refactor.sh` entry point remains as a thin
compatibility wrapper. New documentation and automation use `scripts/install.sh`.

## Post-install application validation

For product-specific actions, confirm the capability mapping and window focus
before debugging shortcuts or OVOS intent routing.

```bash
cat ~/.config/jarvis/capabilities.json
```

Then inspect the real X11 identity of the application:

```bash
wmctrl -lx
ACTIVE="$(xdotool getactivewindow)"
xprop -id "$ACTIVE" WM_CLASS
```

For Standard Notes, the validated laptop reported:

```text
WM_CLASS(STRING) = "standard notes", "Standard Notes"
```

Test Jarvis focus directly:

```bash
~/.local/bin/jarvis-app-window focus standard_notes
echo "exit=$?"
```

Only after focus succeeds should you test application-specific actions such as
`New note` or `Search notes`. A bare `xdotool key ...` command targets whatever
window currently owns focus, often the terminal, so it is not a valid app test
unless the intended application is actually active.

See [`docs/window-focus-and-app-integration.md`](../window-focus-and-app-integration.md)
for the complete Brain/laptop comparison and troubleshooting procedure.

## Capabilities

- Brave and Firefox search, navigation and semantic page reading
- YouTube search and Shorts navigation without unstable result auto-selection
- Open, focus, minimise, maximise and close controls across enabled apps
- Clipboard, text editing, Enter, Tab and Shift+Tab controls
- OS-default Mail, explicit Proton Mail and copied-link Zoom integrations
- Claude Desktop, ChatGPT Desktop and Hermes Desktop controls
- Explicit Claude and ChatGPT website commands using the default browser
- Speech Note dictation and local text-to-speech
- System microphone, speaker, Jarvis-listener and media controls
- State-aware Caps Lock
- Safe personal phrase editor with no arbitrary command execution

See the [command reference](../command-reference.md) for spoken forms.

## Universal reading

`Read page`, `Read full page`, `Read window`, `Read app`, `Read screen` and
`Read content` all use the same local reader. Claude and Hermes are never asked
to interpret the screen.

- Brave and Firefox prefer semantic main-content extraction.
- GTK, Qt and Electron apps use AT-SPI accessibility first.
- Claude and Hermes launch with renderer accessibility enabled.
- Clipboard copying is a compatibility fallback.
- Terminal uses terminal-safe copy shortcuts.
- Menus, toolbars, buttons and status UI are excluded where accessibility
  metadata permits.

Speech Note performs local playback. OVOS listening is muted during playback
to prevent self-triggering and restored when reading ends or is interrupted.

## Architecture

| Layer | Responsibility |
|---|---|
| Standard modules | Portable browser, window, text, reading and system actions |
| Integrations | Guarded product-specific behaviour |
| Capabilities | Detected and user-approved application mappings |
| Personal phrases | Alternative wording for existing approved actions |
| Helpers | Fixed, allowlisted local automation |

Core modules live in `ovos_skill_jarvis_dispatcher/`. Product-specific actions
live in `ovos_skill_jarvis_dispatcher/integrations/`. Desktop automation is
restricted to reviewed helpers in `system_helpers/`.

`deployment-manifest.json` is the canonical file inventory shared by
installation and validation. Intent names and vocabulary totals remain
explicit regression tripwires in `scripts/validate_refactor.py`.

Hermes launches through `hermes-secure-launch`, uses the rootless Podman socket
and retains the configured `/srv/agent-inbox/hermes:/workspace:rw` boundary.
The launcher watcher restores the secure desktop entry if a Hermes update
regenerates it.

## Desktop controls

The canonical installer adds the Jarvis tray automatically when GTK 3 is
available. It provides application setup, optional Speech Note setup, health
check, support report, update check, safe restarts, start/stop and logs. No
tray package installation is attempted if GTK is unavailable; all functions
remain accessible from the terminal.

The canonical installer adds both tray icons automatically: the voice-system
status/control tray and the separate green/red listener microphone toggle.
The status tray also provides a simple **Wake phrase…** editor for one-to-four
word phrases. Changes remain in the user's OVOS configuration, are backed up,
and restart only the listener. The trained **Hey Jarvis** preset uses
OpenWakeWord; arbitrary custom phrases use local Vosk matching. The tray also
provides **Keyboard shortcuts…**. Windows/Super+L starts one manual
`ovos-listen` session and Shift+Windows/Super+L toggles continuous wake-word
listening, matching the validated Brain controls. Both can be changed or
disabled. Ctrl+Alt+L remains available for screen lock with the defaults, and
rollback restores any Cinnamon bindings Jarvis replaced. The command editor
remains optional:

```bash
bash scripts/install-command-editor.sh
```

The command editor maps personal wording only to approved actions. The OVOS
tray controls service status and safe restarts. The microphone indicator
controls only `ovos-listener.service`.

### Tray menu

| Menu item | What it does |
|---|---|
| **Setup…** | Detect and select the applications Jarvis may control. |
| **Commands…** | Edit personal phrases for approved actions. Shown only when the optional command editor is installed. |
| **Wake phrase…** | Change the wake phrase. The trained **Hey Jarvis** preset uses OpenWakeWord; other phrases use local Vosk matching. |
| **Keyboard shortcuts…** | Change or disable the manual-listen and continuous-listening shortcuts. |
| **Speech Note setup…** | Inspect or install the optional local reading and dictation application. Existing settings and models are preserved. |
| **Run health check** | Validate the host, configured apps, OVOS services, voice packages and Jarvis installation. |
| **Create AI support report** | Save a privacy-filtered diagnostic archive in `~/Downloads`. Nothing is uploaded. |
| **Check for updates** | Check the configured GitHub release. If a newer release was already detected, this opens its supervised installer. |
| **Restart Jarvis commands** | Restart only `ovos-core.service`, which reloads Jarvis command code. |
| **Restart full voice system** | Restart audio, listener and core services in dependency order. |
| **Start/Stop voice system** | Start or stop the three managed OVOS voice services. |
| **View recent logs** | Follow the latest 200 core, listener and audio log lines in a terminal. |
| **About…** | Show the installed Jarvis version and the OVOS/plugin versions in its active virtual environment. |
| **Close tray icon** | Close only the status icon. The voice services keep running. |

The tray icon reports `ready`, `starting`, `stopped` or `failed`. A small red
badge means that a newer Jarvis release was detected. See the
[troubleshooting guide](../troubleshooting.md) for the shortest safe checks
when a command or service is not behaving as expected.

Wake-word capture tuning remains independent and reversible:

```bash
bash scripts/set-instant-listen.sh status
bash scripts/set-instant-listen.sh disable
jarvis-restart --full
```

## Development and releases

```bash
python3 scripts/validate_refactor.py
bash scripts/test-window-matching.sh
bash scripts/test-focused-navigation.sh
bash scripts/test-deployment.sh
bash scripts/build-release.sh
```

Before publishing a desktop-integration change, test both an existing
known-good machine and any machine that motivated a new window-class variant.
For each affected app, capture `wmctrl -lx`, confirm `WM_CLASS`, run
`jarvis-app-window focus <integration>`, and only then test the product-specific
shortcut and spoken intent.

CI validates Python 3.10 through 3.13, checks every shell entry point and
builds a clean release archive. Archives exclude Git metadata, caches, logs,
local configuration and previous builds. Each archive has a `.sha256` sidecar
for corruption detection; that checksum is not a publisher signature.

A silent monthly timer checks the configured GitHub release source without
changing the workstation. There are no automatic popups. When a newer release
is found, the tray gains a small red badge and its menu reports the version.
Installation remains manual through `jarvis-update install`, verifies SHA-256,
uses the transactional installer and retains rollback. Checks fail quietly
while the repository is private or the laptop is offline. A separate GitHub
workflow checks current OVOS APIs without changing any workstation.

During an announced public update window, users can select **Check for
updates** in the tray. After detection, the same menu entry changes to the
available version; selecting it opens the supervised installer and confirmation
prompt.

Publishing ordinary commits never updates clients. A client sees an update
only after a higher semantic version is published as a GitHub Release with the
matching versioned archive and checksum assets. Test the exact archive and
checksum before publishing, and never replace assets attached to an existing
version. After the small user group has updated, the repository may be made
private again.

See the [maintenance guide](../maintenance.md) before changing inventory or
deployment, the
[window focus/integration guide](../window-focus-and-app-integration.md) for
cross-machine GUI diagnosis, the
[troubleshooting guide](../troubleshooting.md) for normal operational checks,
and the
[repository audit](../repository-audit.md) for the v21 cleanup decisions.
Earlier implementation reports are retained under
[`docs/history/`](../history/README.md) as historical records only.
The [security and update policy](../security-and-updates.md) defines the
supported platform, privilege boundary, checksum limits and supervised OVOS
update procedure.

## AI-assisted diagnosis

Create a privacy-first handoff that a coding AI can inspect without a custom
prompt:

```bash
jarvis-report --issue "Describe what failed"
```

The resulting archive contains a safe source snapshot, versions, validation,
service state, integrity hashes and its own AI instructions. It excludes raw
logs, audio, transcripts, clipboard contents and messages by default, and it is
never uploaded automatically. See [AI-assisted maintenance](../ai-maintenance.md).

## Repository map

| Path | Purpose |
|---|---|
| `ovos_skill_jarvis_dispatcher/` | Modular OVOS skill |
| `system_helpers/` | Allowlisted local automation |
| `profiles/` | Legacy migration mappings |
| `command_editor/` | Safe GTK personal-phrase editor |
| `tray/`, `mic/` and `voice/` | Status controls and packaged listening sound |
| `scripts/` | Install, rollback, validation, packaging and optional setup |
| `docs/` | Current guides and archived implementation records |

## Validated baseline

- 21 Python modules
- 90 intents
- 1,705 Brain-compatibility vocabulary registrations
- 4 deployment profiles
- 16 runtime helpers
- 6 managed user-systemd units
- The reviewed Brain intent-pipeline order, verified against installed plugins

Normal capability files omit private agent vocabulary, so their registration
count is intentionally smaller. The larger count is a migration regression
fixture for the previously customised Brain profile; private agent vocabulary
is not enabled or installed by normal setup.
