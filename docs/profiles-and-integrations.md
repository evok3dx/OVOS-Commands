# Profiles and application integrations

Profiles separate reusable voice commands from the choices made on a specific
machine. A command category such as `notes` is stable; the selected profile
maps it to an allowlisted integration such as `standard_notes`.

The profile cannot provide an arbitrary shell command. It may only select an
integration compiled into `profile.py`, and each category accepts only
explicitly compatible integrations.

## Included profiles

- `default.json`: command-only browser and terminal baseline.
- `brain.json`: the existing Brain mappings and optional conversation enabled.
- `personal.example.json`: example command-only personal mapping.

The deployment script installs `brain.json` unless `JARVIS_PROFILE` selects a
different file:

```bash
JARVIS_PROFILE=default bash scripts/deploy-modular-refactor.sh
```

The installed profile is stored at:

```text
~/.config/jarvis/profile.json
```

If it is absent or invalid, the dispatcher logs the error and uses the
previous Brain mappings. This makes the migration behaviour-preserving.

## Application-specific actions

Application-specific behaviour belongs in `integrations/`, not in the generic
desktop controller. Generic commands remain portable; profiles select only
compatible, compiled integrations and cannot supply arbitrary shell commands.

### Standard Notes

```text
new note
create a new note
create new note
make a new note
make new note
```

It focuses or opens the configured Notes application, verifies that the
profile maps Notes to Standard Notes, verifies that Standard Notes owns the
active window, then invokes the known `Alt+Shift+N` shortcut. Failures are
caught inside that action and do not affect other commands.

Standard Notes also supports two deliberately distinct searches:

- `search this note` uses `Ctrl+F` in the focused note;
- `search notes` opens the universal palette with `Ctrl+Shift+Colon`.

### Proton Mail

The Proton Mail integration uses documented shortcuts after focusing and
verifying the configured application:

- `N` creates a message;
- `/` focuses mailbox search;
- `Enter` executes the entered query.

Sending is intentionally not automated. It requires a separate confirmation
design.

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

Machine-specific choices belong in `profiles/*.json`. For example, the Brain
maps `notes` to `standard_notes`, `mail` to `proton_mail` and `calendar` to
`proton_calendar`. Another machine can choose a smaller command-only profile
without editing the reusable vocabulary or desktop controller.

Executable paths remain in allowlisted helpers. They are not accepted from a
spoken command or arbitrary profile value.

The `conversation` and `wake_phrase` values record installation choices for a
future bootstrap installer. The dispatcher does not directly reconfigure the
OVOS Persona or listener services from these values. This prevents deploying
an application profile from unexpectedly changing the machine's voice stack.

## Immediate command capture

If the first word of a command is clipped after the wake phrase, enable OVOS
`instant_listen` separately from profile deployment:

```bash
bash scripts/set-instant-listen.sh enable
jarvis-restart --full
```

The helper validates the existing JSON, creates a timestamped backup and
writes the update atomically. It supports `status` and `disable`. Keeping this
outside the deployment script makes the listener experiment independently
reversible if it captures wake-word or notification audio on a particular
microphone.
