# Historical V3 draft before final validation

**HISTORICAL:** This privacy-safe summary records the early V3 plan. It is not
installation guidance. Several original assumptions were superseded by the
tested V3 implementation.

## Early plan

- Combine service, microphone, and update state in one tray and Control Centre.
- Add bounded local Qwen routing for approved actions only.
- Add dynamic Faster-Whisper application-name hints.
- Preserve configuration, models, personal phrases, shortcuts, and private
  extensions during transactional updates.
- Package media and file-search integrations separately while installing them
  through the main release.
- Retain wake-word interruption during local Speech Note reading.
- Add normal and faster reading commands without allowing model-generated
  shell execution.

## Superseded assumptions

The first draft treated the local model, Whisper hints, and file search as
optional future work and assumed the existing voice environment would always
remain untouched. Cross-machine testing showed that a reproducible reviewed
voice-stack baseline, explicit compatibility pins, staged upgrades, and
rollback were required. Those changes were implemented and validated during
the later V3 release-candidate cycle.

The draft also predated the combined tray, improved installer recovery,
listener cue and volume guards, application defaults, search pacing, portable
export, and the final plugin packages.

For current behaviour, use the [project README](../../README.md), the
[decision log](../12-decisions.md), the [voice documentation](../06-ovos-voice.md),
and the [V3.6 release checklist](../v3.6-release-checklist.md).
