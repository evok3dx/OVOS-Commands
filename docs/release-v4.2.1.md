# Jarvis 4.2.1

## Changes

- Fix the GUI lock conflict during isolated updates and recovery.
- Add a reviewed one-time repair for existing 4.0.1 and 4.2.0 GUI updaters.

## Verification

The regression reproduces the old failure and checks the repaired update path,
duplicate-update protection and recovery. Clean-archive checks pass.
Settings, isolation, the reviewed runtime, Media and File Search are retained.
Live desktop upgrade acceptance remains separate.

See the [release record](releases.md) and [upgrade guidance](troubleshooting.md#isolated-gui-update-lock-conflict).
