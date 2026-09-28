# Release record

This is the one current ledger for release changes, verification and open
acceptance work. Durable design choices belong in
[`12-decisions.md`](12-decisions.md), reusable fixes in
[`troubleshooting.md`](troubleshooting.md), and completed investigation detail
under [`history/`](history/README.md). Other current documents link here rather
than repeating release narratives.

## 3.7.1

Status: **VERIFIED in code and automated tests; live upgrade acceptance remains
required before publication.**

Changes:

- stopping active continuous dictation preserves Speech Note's final full stop
  and adds one trailing space;
- `Press space` inserts one space in the verified focused application;
- `Show desktop`, `Go to desktop` and `Minimize all` use the fixed Linux Mint
  `Super+D` shortcut;
- live evidence added `Send the message` and `Submit` as strict Enter aliases,
  while a bounded Whisper `Send it` cue addresses repeated `Standard`/`Present`
  substitutions without making those ordinary words executable;
- contributor instructions now require the complete deterministic/Qwen/GUI
  command-update path and explicitly prohibit root-owned staging;
- Claude, Copilot and Gemini instruction adapters point to the canonical
  `AGENTS.md` instead of duplicating policy.

Release gates:

- [x] **VERIFIED:** repository and focused command tests pass: 98 intents and
  2,010 unique vocabulary registrations;
- [x] **VERIFIED:** 360-case non-executing routing policy benchmark passes;
- [x] **VERIFIED:** fresh install, upgrade preservation, failure recovery,
  staged-stack migration and rollback pass;
- [x] **VERIFIED:** final archive checksum and complete clean-extraction suite
  pass;
- [ ] live `Stop writing`, `Press space` and `Show desktop` acceptance passes;
- [ ] public main, tag, archive and checksums identify the same release.

## Earlier releases

The detailed 3.7 gate is retained in
[`v3.7-release-checklist.md`](v3.7-release-checklist.md). Earlier development,
incident and compatibility records are indexed under
[`history/`](history/README.md).
