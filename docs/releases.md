# Release record

This is the one current ledger for release changes, verification and open
acceptance work. Durable design choices belong in
[`12-decisions.md`](12-decisions.md), reusable fixes in
[`troubleshooting.md`](troubleshooting.md), and completed investigation detail
under [`history/`](history/README.md). Other current documents link here rather
than repeating release narratives.

## 3.7.3

Status: **VERIFIED in code and automated tests; published with live visual
acceptance still recommended.**

Changes:

- the Default Apps selector keeps the click-open popover and roomy choices but
  is compact again, left-aligns the selected application and displays an
  explicit downward chevron;
- native and Flatpak ONLYOFFICE detection, recommendation and friendly Office
  routing remain covered by the preferred-app regression test;
- no voice, Qwen, Whisper, installer, application selection or model behaviour
  changed.

Release gates:

- [x] focused Default Apps and ONLYOFFICE tests pass;
- [ ] live compact selector, chevron and click-open acceptance passes;
- [x] public main, tag, archive and checksums identify the same release.

## 3.7.2

Status: **HISTORICAL — published and superseded by the 3.7.3 visual correction.**

Changes:

- `Stop the music/song/track` now uses resumable pause semantics for browser
  players; explicit `Stop media/playback/video` retains true-stop behaviour;
- `Start/Resume the music/song/track`, including `Start the song again`, maps
  to the existing allowlisted play action without weakening Qwen boundaries;
- `Stop writing` now inserts the promised trailing space when the wake phrase
  has already moved continuous dictation into its paused state, and rechecks
  that focus did not change before sending the key;
- the Default Apps controls use click-to-open popovers with spacious choices,
  and the reviewed office integration is labelled `ONLYOFFICE` when detected
  and enabled;
- `Minimize/Minimise everything` and `Hide everything` now use the native
  Show Desktop action instead of falling through to “Please repeat”;
- clear past-tense statements such as `I wrote this stuff` are rejected before
  Qwen is called, preventing accidental writing capture while retaining actual
  writing requests;
- AI support bundles and Control Centre Recent Logs redact OVOS session
  location coordinates as well as the existing identity/credential shapes.

Evidence:

- the newest live log showed correct Whisper transcription and exact native
  intent matches for `Resume the music` and `Stop the music`;
- resume worked after pause, while the next resume after true MPRIS stop sent
  no successful media action, isolating the failure to stop semantics rather
  than recognition or routing;
- a later live log showed three exact `Minimize everything` transcriptions
  falling through, while `Show desktop` matched natively, and showed `I wrote
  this stuff` being misclassified as `text.write`; both cases now have direct
  regressions;
- deterministic routing validates 98 intents and 2,024 unique vocabulary
  registrations, and the non-executing routing benchmark passes 364/364;
- focus-safety, profile and deployment checks pass; the actual GTK interaction
  remains a live laptop acceptance item.

Release gates:

- [x] focused command, dictation and Default Apps tests pass;
- [x] complete deterministic and deployment suites pass;
- [x] clean archive extraction and checksum pass;
- [ ] live Default Apps popover and ONLYOFFICE display acceptance passes;
- [ ] live `Stop music` → `Resume/Start music` acceptance passes;
- [ ] live continuous dictation → wake phrase → `Stop writing` leaves `. `;
- [ ] public main, tag, archive and checksums identify the same release.

## 3.7.1

Status: **HISTORICAL — published and superseded by the 3.7.2 corrective work.**

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
- [ ] live `Stop writing` trailing-space acceptance exposed the paused-state
  defect carried into 3.7.2;
- [x] public main, tag, archive and checksums identify the same release.

## Earlier releases

The detailed 3.7 gate is retained in
[`v3.7-release-checklist.md`](v3.7-release-checklist.md). Earlier development,
incident and compatibility records are indexed under
[`history/`](history/README.md).
