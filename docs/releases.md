# Release record

This is the one current ledger for release changes, verification and open
acceptance work. Durable design choices belong in
[`12-decisions.md`](12-decisions.md), reusable fixes in
[`troubleshooting.md`](troubleshooting.md), and completed investigation detail
under [`history/`](history/README.md). Other current documents link here rather
than repeating release narratives.

## 3.9.0

Status: **VERIFIED in focused source tests; full release and live laptop
acceptance pending.**

Changes:

- focused `Read this` now keeps the temporary clipboard owner available for a
  bounded one-second hand-off after Speech Note accepts the request, then
  clears the clipboard. The previous clipboard value is never retained or
  restored;
- an update started in the Control Centre can be stopped safely. Closing the
  window during an update offers the same bounded termination instead of
  leaving an uncloseable `Installing update` state;
- the reviewed Common Play player gains the state-aware `can_stop()` required
  by the installed OVOS Workshop Stop pipeline. Installation is guarded by the
  exact reviewed Common Play version and source hash and is transactional;
- Media 0.3.1 reports when Play cannot find a browser media session. Brave and
  YouTube Music remain connected through MPRIS; the documented prevention for
  an inactive discarded tab is Brave's **Always keep these sites active**
  setting for `music.youtube.com` and `youtube.com`;
- the non-executing benchmark is now an exactly 350-case balanced suite. It
  covers every Qwen-exposed action in the reference profile, including normal
  window, application, tab, navigation, reading, writing, media, search and
  message variations, plus safe rejection cases.

Evidence:

- [x] focused clipboard hand-off and final-clear regression passes;
- [x] Control Centre update completion and cancellation regressions pass;
- [x] exact Common Play compatibility patch, idempotence and rejection tests pass;
- [x] Media missing-session feedback and 350-case routing policy tests pass;
- [x] complete source-tree deployment, preservation, failure and rollback suite passes;
- [ ] complete 350-case real-model benchmark passes on the laptop;
- [ ] live ONLYOFFICE selection, update cancellation, Stop and Brave playback acceptance passes;
- [x] final archive checksum, both plugin wheel checksums and clean-extraction suite pass;
- [ ] public main, tag, archive and checksums identify the same release.

## 3.8.2

Status: **VERIFIED in code, archive inspection and automated tests; publication
pending.**

Changes:

- packaging-only correction for 3.8.1 with a new, uncached release URL;
- excludes the temporary GitHub CLI program, licence and manual pages that
  made the first 3.8.1 asset exceed the updater's extraction-size limit;
- contains no credential files or user configuration. GitHub authentication
  was stored outside the repository and was removed after publication;
- retains the focused-reading, clipboard, dictation, Stop and Zoom fixes from
  3.8.1 without changing their behaviour.

Evidence:

- [x] archive entry count and total/largest extracted sizes are below updater limits;
- [x] archive contains no untracked tool directory or credential/config paths;
- [x] source-tree and clean-extraction validation passes;
- [ ] public main, tag, archive and checksums identify the same release.

## 3.8.1

Status: **HISTORICAL — published and superseded by the 3.8.2 packaging
correction; live laptop acceptance was pending.**

Changes:

- `Read this` copies only from the verified focused window instead of using a
  potentially stale X11 primary selection from another application;
- Jarvis never backs up or restores clipboard contents for reading. It clears
  the temporary text immediately after Speech Note accepts or rejects it;
- every temporary clipboard owner closes the reading lock descriptor, fixing
  the remaining normal-speed path that could falsely report reading startup;
- continuous dictation is considered active only after Speech Note reports its
  listening state, and a failed start is cancelled instead of being reported
  as successful;
- bare `Stop` is owned by an active reading, dictation or prompted-writing
  workflow and no longer also stops unrelated browser media;
- Zoom recognises reviewed native and Flatpak window classes, uses desktop
  discovery, and serialises concurrent open requests to prevent duplicates.

Evidence:

- [x] focused clipboard, lock-isolation and temporary-speed regressions pass;
- [x] dictation state and routing regressions pass;
- [x] full source-tree deployment, preservation, failure and rollback suite passes;
- [x] final archive checksum and clean-extraction suite pass;
- [ ] live ONLYOFFICE selection, writing/dictation and Zoom acceptance passes;
- [x] public main, tag, archive and checksums identify the same release.

## 3.8.0

Status: **HISTORICAL — published and superseded by the 3.8.1 focused-reading
and dictation correction.**

Changes:

- the live-accepted Default Apps control uses an ordinary GTK button and an
  explicit popover, avoiding the Linux Mint `Gtk.MenuButton` no-open failure;
- generic Mail is clearly labelled **System default mail**, while enabled
  Thunderbird, ElectronMail and Proton Mail retain their concrete names;
- detected Notes, Sticky Notes, Text Editor and Xed are eligible for the Notes
  role without widening that role to unrelated desktop utilities;
- ONLYOFFICE uses its reviewed desktop entry through GIO, including the
  Flatpak entry, and recognises fixed native/Flatpak X11 class variants;
- the temporary 2× completion monitor closes its inherited setup-lock file
  descriptor, so an accepted read cannot block every later `Read this` request;
- lock contention now says that reading is still starting rather than claiming
  playback is already active.

Evidence:

- [x] live Default Apps popover opens on the tested Linux Mint laptop;
- [x] focused default-role and reading-lock regressions pass;
- [x] 364/364 non-executing routing-policy cases pass;
- [x] full source-tree deployment, preservation, failure and rollback suite passes;
- [ ] live normal → 2× → normal reading sequence passes;
- [ ] live ONLYOFFICE Flatpak launch/focus acceptance passes;
- [x] final archive checksum and clean-extraction suite pass;
- [x] public main, tag, archive and checksums identify the same release.

## 3.7.3

Status: **HISTORICAL — published and superseded by the 3.8.0 live GTK and
reading correction.**

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
