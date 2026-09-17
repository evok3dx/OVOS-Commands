# Capabilities and application integrations

The private `~/.config/jarvis/capabilities.json` file separates reusable voice
commands from applications detected and approved on one machine. A category
such as `notes` maps only to a reviewed integration such as `standard_notes`.

The file cannot provide an arbitrary shell command. It may only select an
integration compiled into `profile.py`, and each category accepts only
explicitly compatible integrations.

## Setup choices

- `All detected`: enables every reviewed integration found locally.
- `Core only`: enables universal system, media, reading and focused-window controls.
- `Custom`: shows only detected reviewed applications for selection.

The OVOS bootstrap may install OVOS and minimal command-line system
prerequisites, but application selection never installs the selected desktop
applications. Speech Note is the one separate, explicitly labelled optional
add-on and is installed per-user only after confirmation. The tray opens the
same application-selection window later. Non-interactive deployment can select
explicitly:

```bash
bash scripts/install.sh --mode all
bash scripts/install.sh --mode core
bash scripts/install.sh --mode custom --apps firefox,hermes_desktop
```

The installed profile is stored at:

```text
~/.config/jarvis/capabilities.json
```

If it is absent or invalid, the dispatcher fails closed to core controls. Older
`profile.json` files are migrated once. An existing named Brain profile may
preserve its already-provisioned private agent extension, but normal setup can
never enable or provision agents, users, sudo rules or privileged helpers.

When diagnosing a machine, inspect `capabilities.json` first. If it exists, it
takes precedence over the legacy `profile.json` path.

## Application-specific actions

Application-specific behaviour belongs in `integrations/`, not in the generic
desktop controller. Generic commands remain portable; capabilities select only
compatible, compiled integrations and cannot supply arbitrary shell commands.

Before an integration sends a keyboard shortcut, Jarvis first resolves and
focuses the reviewed application through `~/.local/bin/jarvis-app-window`.
Product-specific shortcuts must not be used as a substitute for reliable window
discovery.

### Standard Notes

```text
new note
create a new note
create new note
make a new note
make new note
```

It focuses or opens the configured Notes application, verifies that the
capability file maps Notes to Standard Notes, verifies that Standard Notes owns
the active window, then invokes the known `Alt+Shift+N` shortcut. Failures are
caught inside that action and do not affect other commands.

Detection and launching share the same reviewed forms: the `standard-notes`
commands, the official Flatpak ID, matching desktop launchers, and Standard
Notes AppImages in `~/Apps` or `~/Applications`. Profile files still cannot
provide an arbitrary executable path.

Standard Notes also supports two deliberately distinct searches:

- `search this note` uses `Ctrl+F` in the focused note;
- `search notes` opens the universal palette with `Ctrl+Shift+Colon`.

Standard Notes packaging can expose more than one reviewed X11 class spelling.
`jarvis-app-window` therefore supports a `|`-separated list of fixed literal
window signatures and checks each candidate independently. Do not replace that
logic with one literal comparison against the entire `|`-joined string.

The exact Brain/laptop failure that motivated this rule, plus the validated
troubleshooting sequence, is documented in
[`window-focus-and-app-integration.md`](window-focus-and-app-integration.md).

### Default Mail and Proton Mail

`Open mail` follows the operating system's registered `mailto` application.
`Open Proton Mail` targets Proton explicitly. Jarvis validates the desktop
association and launches it through the desktop entry without executing a
profile-supplied command.

The Proton Mail integration uses documented shortcuts after focusing and
verifying the configured application:

- `N` creates a message;
- `/` focuses mailbox search;
- `Enter` executes the entered query.

Sending is intentionally not automated. It requires a separate confirmation
design.

Proton Mail shares the generic app-focus helper with Standard Notes and other
desktop integrations, but it keeps its own allowlisted window signatures. A
failure in one application does not prove another application is broken.

### Zoom

The Zoom integration does not automate screen coordinates. It validates a
copied `zoom.us` invitation, extracts the meeting number and optional encoded
password locally, and invokes the registered `zoommtg` URI handler. Invalid or
missing clipboard links are refused.

Zoom microphone and video shortcuts are toggles. They must not be exposed as
state-specific commands such as `mute microphone` or `disable video` until the
integration can verify current state, because toggling an already-muted device
would produce the opposite result.

## Custom and personal mappings

Machine-specific choices belong in `capabilities.json`. `profiles/*.json` are
retained only for tested migration of older releases.

Executable paths remain in allowlisted helpers. They are not accepted from a
spoken command or arbitrary profile value.

The `conversation`, `wake_phrase`, `listen_shortcut` and
`microphone_shortcut` values record the reviewed installation choices. The
transactional installer applies the wake phrase and both Cinnamon shortcuts;
the dispatcher itself never rewrites OVOS or desktop settings while handling
a spoken command. Defaults match the validated Brain: Super+L starts one
manual command and Shift+Super+L stops or starts wake-word listening.

## Immediate command capture

The reviewed local stack matches the validated Brain with `instant_listen`
enabled, a 0.25-second barge-in delay and fake barge-in enabled. If a particular
microphone produces accidental follow-up capture, disable `instant_listen`
separately from profile deployment:

```bash
bash scripts/set-instant-listen.sh disable
jarvis-restart --full
```

The helper validates the existing JSON, creates a timestamped backup and
writes the update atomically. It supports `status` and `disable`. Keeping this
outside the deployment script makes the listener experiment independently
reversible if it captures wake-word or notification audio on a particular
microphone.
