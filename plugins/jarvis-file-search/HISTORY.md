# Release history

## 0.2.0

- Packages the clickable filename search as a complete OVOS skill release.
- Includes direct patterns for “Looking in my documents for Alex” and the
  observed transcription “Looking my documents for Alex”. These run before
  Qwen, whose 8-second model deadline was exceeded during the initial test.
- Adds an optional, version-checked installer for the local Qwen
  `files.search` action; the spoken query stays in the original transcript.
- Documents installation, configuration, safety boundaries, testing and the
  independent Media pipeline.
- Includes `COMMANDS.md` listing all native voice patterns; the separate
  tray Commands tab is outside this skill and is not modified.

## 0.1.9 and earlier

- Filename-only scanning with bounded entries and time, Documents-only scope,
  a Zenity results window and opening a selected file with `xdg-open`.
- Reuses the results window, speaks only “Searching” during successful search.
- Added common short commands and documentation-related filename patterns.
