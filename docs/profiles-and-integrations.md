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
desktop controller. The first integration is Standard Notes:

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

The `conversation` and `wake_phrase` values record installation choices for a
future bootstrap installer. The dispatcher does not directly reconfigure the
OVOS Persona or listener services from these values. This prevents deploying
an application profile from unexpectedly changing the machine's voice stack.
