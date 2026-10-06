# Release record

This is the one current ledger for release changes, verification and open
acceptance work. Durable design choices belong in
[`12-decisions.md`](12-decisions.md), reusable fixes in
[`troubleshooting.md`](troubleshooting.md), and completed investigation detail
under [`history/`](history/README.md). Other current documents link here rather
than repeating release narratives.

## 4.2.1 (published stable, 6 October 2026 UTC)

The GUI holds a separate update lock, leaving the installer free to acquire
the service-control lock for Stop and recovery. Duplicate GUI updates remain
blocked, and the existing transaction guard still blocks unsafe starts.
A one-time, hash-checked repair supports the installed 4.0.1 and 4.2.0 GUI
updaters. It saves a private backup, refuses unreviewed source and pending
recovery, and leaves settings, services and isolation policy unchanged.

**VERIFIED at `1505ff7635e233f833d1f0fd1189c137da8c72ea`:**
[all six validation jobs](https://github.com/evok3dx/OVOS-Commands/actions/runs/37399328256)
pass Python 3.10–3.13, GTK, security scans, deployment/recovery and 350/350
clean-copy policy cases. The
[migration regression](https://github.com/evok3dx/OVOS-Commands/actions/runs/37399328201)
reproduces the old failure in both released updaters and passes after repair,
including duplicate-update protection, pending-recovery refusal and private
backups. [Final packaging](https://github.com/evok3dx/OVOS-Commands/actions/runs/37399328273)
passes clean-archive checks and all 296 runtime identities/hashes with zero
exemptions. This is automated process/transaction evidence, not a live Brain
GUI upgrade; that acceptance remains pending.
The reviewed runtime, Media and File Search remain unchanged.

**VERIFIED publication:** [run 37399767585](https://github.com/evok3dx/OVOS-Commands/actions/runs/37399767585)
published [Jarvis 4.2.1](https://github.com/evok3dx/OVOS-Commands/releases/tag/v4.2.1)
as the latest stable release. All 11 public assets were downloaded again and
verified against SHA256SUMS. The `v4.2.1` tag points to the validated source
above; main was advanced to it before this documentation-only record.
Code archive SHA-256:
`315a098b72fc4ec004841fa4f062aa2f1baaca989bb9739e4f3a8f226dfe8d62`.

## 4.2.0 (published stable, 6 October 2026)

The native Dashboard places system status and Run/Stop/Restart on the left,
with Speech, Listener and Commands on the right. General offers app-scoped
Light/Dark appearance, preserving independent login choices. Subtle Unchained
branding and bounded session activity contain no transcripts or search text.

Standard Notes recognises reviewed complete WM_CLASS pairs, preserves its
focus checks and existing shortcuts, and gives short failure feedback.
ElectronMail appears under Mail even when its desktop metadata omits Email;
it is excluded from Office. New report/review folders use readable timestamps;
existing candidate paths and internal security tokens remain unchanged.
Maintenance shows inspected core/private-model policy separately from network
verification, with an explicit read-only check also available from the CLI.
Unsupported dedicated-model IPv6 probes remain NOT TESTED, never a pass.

**VERIFIED automated checks:** all six validation jobs at
`b834e6d76b277da57fd5a9aced45d09fc57f0306`
([37397054542](https://github.com/evok3dx/OVOS-Commands/actions/runs/37397054542))
pass Python 3.10–3.13, real GTK controls/colours, source/history/archive scans,
deployment/recovery and 350/350 clean-copy policy cases. Packaging
([37397054297](https://github.com/evok3dx/OVOS-Commands/actions/runs/37397054297))
rechecks all 296 dependency identities/hashes with zero exemptions and validates
the three current first-party wheels and exact public assets. Light/Dark GTK
renders were inspected. Final documentation/archive validation passed;
live laptop GUI/Notes acceptance remains separate.
The reviewed runtime, Media 0.3.5 pacing and File Search 0.3.0 are unchanged.
See the [4.2 plan](v4.2-plan.md),
[short release notes](release-v4.2.0.md) and [security policy](security-and-updates.md).

**VERIFIED publication:** [run 37397660718](https://github.com/evok3dx/OVOS-Commands/actions/runs/37397660718)
published [Jarvis 4.2](https://github.com/evok3dx/OVOS-Commands/releases/tag/v4.2.0)
as the latest stable release. All 11 public assets were downloaded again and
verified against SHA256SUMS. The `v4.2.0` tag points to the validated source
above; main was advanced to that source before this documentation-only record.
Code archive SHA-256:
`3f164e8d74f1987105f9d6b9f46de58c6f684decd4bcf6170b4bb1c5f7136bf5`.

**VERIFIED source limitation in 4.2.0 after publication:** an isolated update launched
from the Control Centre holds the control lock while the installer needs that
lock to stop services. The supplied update failure is consistent with this
conflict. Use the [terminal recovery/update procedure](troubleshooting.md#isolated-gui-update-lock-conflict);
4.2.1 corrects the conflict, with a one-time repair for older GUIs. Do not disable isolation
or delete the recovery journal to bypass the guard.

## 4.0.1 (published stable, 1 October 2026)

Guided optional isolation is recommended for new installs and preserves existing
choices. It uses a dedicated ordinary-user Ollama with a private, hash-checked
Qwen copy and no fallback to general Ollama. Weather/Media remain separately
online. General Ollama is unchanged. Native changes need bounded administrator
approval; normal upgrades retain existing policy and settings.

The process-bound installer now recovers isolated upgrades, handles actual
Python `-I` worker startup and restores exact source after package rebuilds.
Saved isolation choices are exported privately; explicit model removal targets
only the verified private copy. Media remains 0.3.5 and File Search 0.3.0.

**VERIFIED:** all six CI jobs at `b536f0a895b1afdbd45d6d1457a4a72a91ed3bc9`
([36934036944](https://github.com/evok3dx/OVOS-Commands/actions/runs/36934036944))
pass Python 3.10–3.13, GTK, source/history/archive scans, clean-copy deployment
and recovery, 350/350 policy cases and all 296 dependencies with zero exemptions.
Supplied live output confirms interrupted recovery, legacy migration, private
model inventory, voice readiness and a health check with zero failures/warnings.

**HISTORICAL owner release decision:** the working update was published for the
controlled small-client deployment with dedicated-daemon generation/IPv4/IPv6
egress and fresh-install coverage accepted for later testing.

**VERIFIED post-release live checks, 1 October 2026:** supplied private reports
confirm local generation by the dedicated Ollama, unchanged daemon identity,
and denied external IPv4/IPv6 TCP attempts with functioning outside controls
before and after each attempt. The current-source actual core/listener/audio
collector passes external IPv4/IPv6 TCP and direct DNS/UDP comparisons for all
three workers while preserving messagebus/model loopback connections. These
close the dedicated-generation and tested direct-network gates. Raw reports
remain private. Fresh installation/login, mediated or inherited sockets and
broader acceptance remain unverified; no complete-security claim is made.
No new production behaviour was added after the exercised build. Existing V4
limits, signing and complete fresh-machine offline setup remain unchanged.
See [installation](07-installer-updates.md), [security](security-and-updates.md)
and the [resolved trial history](history/v4.0.1-recovery.md).

**VERIFIED publication:** [run 36934709323](https://github.com/evok3dx/OVOS-Commands/actions/runs/36934709323)
passed packaging and publication. All 11 public assets were downloaded again
and verified against SHA256SUMS; the stable `v4.0.1` tag points to
`26d634c2c7b0812609f76a7016ce6d83d6b3ca1f`. Final source validation
[36934709441](https://github.com/evok3dx/OVOS-Commands/actions/runs/36934709441)
passed all six jobs. Code archive SHA-256:
`f36c92a9a7491b34b23902a1d115157ec11b8618892589b184410a3d9b54fdf8`.
The retained runtime and production behaviour are unchanged.

## 4.0.0 (published stable, 1 October 2026)

V4 includes the complete reviewed, hash-verified 296-package runtime with zero
dependency exemptions, retained NumPy 2 and the ONNX-only wake plugin. Local
voice/Qwen remain on the reviewed stack. Native service isolation, separate
Weather/Media workers, guarded desktop handoffs, terminal-input blocking,
private-agent confirmation, report privacy, HTTPS/archive guards and scoped
rollback are included. General separates quiet tray startup from voice startup;
Dashboard controls the current session. Readiness uses actual worker replies.

Media 0.3.5 acknowledges before lookup and waits three seconds after a valid
result before opening it. The exercised laptop retry is accepted. Qwen and the
shared 11-second search gap remain. Named-city weather uses that city's
coordinates/timezone without changing saved preferences. Newly resolved cities
can take about 15 seconds; repeated locations avoid the lookup. Multiple music
tabs may play concurrently; selecting another song does not claim to stop the
previous tab. These two limitations are accepted for this release.

**Scope decision:** publish the current working implementation for the controlled
small-client deployment using existing passed checks and exercised laptop
results. No additional laptop tests are requested. Full acoustic/real-model
350-case coverage, every Zoom/fresh-login/focus variant, weather interruption,
mediated/inherited socket and native recovery acceptance, Hermes permissions and
owner account/repository protection remain explicitly unverified. Production
signatures, full fresh-OS/model offline installation and Flatpak are deferred.
World-time city routing and online Wikipedia/WikiHow answers are deferred; those
web skills stay disabled in restricted core. Same-user/X11 access remains trusted.

**VERIFIED behaviour source:** run 36819754595 at
884259cf18c4df25819d630e78dcbee921fb700f passes all six jobs, complete deployment
and rollback, source/history/archive scans, exact upstream regressions, 350/350
clean-copy policy cases and the complete closure. Stable packaging verifies
those behaviour files are unchanged, rebuilds only the three first-party wheels,
rechecks the retained runtime, scans the exact archive/assets and verifies public
checksums/tag. Runtime SHA-256 remains
03cbba7effa9046d9ce7a63b26d9a0b886eebf4f58f445dda2ae37af07e8c288.
**VERIFIED publication:** release 400682742, tag `v4.0.0`, source commit
72f7c85d15b1c7331e1e193356873354bdf178af. Publication run 36821631654 passes
both packaging and publication jobs. It verifies unchanged passed behaviour,
complete runtime closure, current wheel metadata/inventories, source/history and
exact asset privacy, then uploads all 11 assets and downloads them again to
verify SHA256SUMS and the public tag. The release is neither draft nor prerelease
and is the latest stable. Code archive: 779260 bytes, SHA-256
6983a37a9b2750a1dad24c6da648c8bf7e96e89a31917f3458d262ba38ed5652.
Dispatcher wheel SHA-256:
6606f49fe1181207fab3de6d1f39dceed0c4012b12b316bf39781537a60e0bac.
Media wheel SHA-256:
03e6fb92d807d47934b1f72caebc97c139f96308528e0299935eca32f2e2c6fc.
File Search wheel SHA-256:
b173c592fff3b843c9cf8189e8e567e02df757b453d30f1b5c06430c7384a3ef.
See [V4 release notes](release-v4.0.0.md). Original rc1/rc2 evidence is retained.

**VERIFIED release-list cleanup:** run 36826895321 shortens the stable release
card and retains RC1/RC2 as drafts, leaving only stable V4 published. All 11
assets on each retained release and the stable tag are unchanged. Historical
RC download instructions are no longer public installation paths.

**VERIFIED owner report, post-publication:** the full stable laptop installation
completed. Documentation maintenance updates command, plugin, security and
isolated-upgrade guidance without changing behaviour, versions, tags or assets.
Restored core activation/readiness remains a separate owner-terminal result;
this report does not close broader native recovery or network acceptance.

## V4 development history

RC trials and post-RC investigations are retained in the
[historical V4 development record](history/v4-development.md). Their candidate
versions and pending checks describe their original point in time.

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
