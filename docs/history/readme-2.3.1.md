# Historical README · 2.3.1

**HISTORICAL:** This is a privacy-safe summary of the README at Git commit
`3afc733`. It records the earlier release direction without retaining local
paths, workstation details, raw diagnostics, or obsolete operational
instructions. Current behaviour is defined by the repository code, tests, and
the current documentation index.

## What 2.3.1 established

- A user-space Linux Mint voice-command deployment with an allowlisted action
  boundary and no arbitrary spoken shell execution.
- Local wake-word, speech-to-text, text-to-speech, application, browser,
  reading, media, and desktop controls.
- Capability-based application selection that only enabled detected software.
- Preservation of OVOS configuration, downloaded models, shortcuts, personal
  phrases, and private extensions during managed updates.
- Manifest-driven installation with validation, backup, failure recovery, and
  rollback.
- Guarded window-focus checks before product-specific keyboard automation.
- Optional Speech Note integration for local dictation and reading.
- A tray interface for setup, status, maintenance, and microphone controls.

## Superseded behaviour

Version 2.3.1 still used separate tray indicators, older dependency pins, and
earlier installer and application-selection flows. Those details are retained
as historical context only and must not be used as current setup guidance.

The V3 series consolidated the tray, expanded transactional deployment,
introduced bounded local-model routing, improved privacy and export controls,
and reorganised the documentation. See the [project README](../../README.md),
the [decision log](../12-decisions.md), and the
[V3.6 release checklist](../v3.6-release-checklist.md) for the current record.

## Durable decisions carried forward

- Code and passing tests describe verified behaviour.
- Documentation distinguishes `VERIFIED`, `PLANNED`, and `HISTORICAL` claims.
- User data and machine-specific settings are preserved unless the user
  explicitly requests otherwise.
- Risky actions require strict matching and focused-window verification.
- No update may introduce a listening port or arbitrary command execution.
- Meaningful security or design requirements are not silently removed.
