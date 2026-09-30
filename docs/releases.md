# Release record

This is the one current ledger for release changes, verification and open
acceptance work. Durable design choices belong in
[`12-decisions.md`](12-decisions.md), reusable fixes in
[`troubleshooting.md`](troubleshooting.md), and completed investigation detail
under [`history/`](history/README.md). Other current documents link here rather
than repeating release narratives.

## 4.0.0rc1 (published laptop test; stable release pending)

Status: **Implementation in progress. Owner authorised completion and publication;
artifact and live acceptance gates remain open.** This entry supersedes the collection-only checklist; the full
agreed scope is retained in the owner's V4 implementation plan.

**Owner decision, 30 September 2026:** publish this candidate as a prerelease
for the current laptop, including the exact verified runtime and plugin wheels.
The stable channel remains 3.9.0. Production signing is deferred until wider
deployment; 3.9 response speed and Brave session-expiry recovery are accepted.
This approval does not assert live voice/startup/isolation acceptance. See
[test release and installation](v4-laptop-test-release.md). Native notices and
source pointers accompany the assets; exact upstream binary/source correspondence
and wider redistribution review remain explicitly open.

**VERIFIED publication:** public prerelease
[v4.0.0rc1](https://github.com/evok3dx/OVOS-Commands/releases/tag/v4.0.0rc1),
release `400441025`, points to commit
`f31eeab5a77c7d2eaa52e47057ec583180bb27a0`. Publication run `36777754236`
passes the final archive's complete source/deployment suite, 350/350 policy
cases, source/history/archive/asset scans, exact retained runtime staging and
current-source parity for all three tested plugin wheels. It publishes 11 fixed
assets and downloads them again to verify every checksum. Independent public
tag and asset metadata verification also passes. Source run `36777753941`
passes Python 3.10–3.13 and security checks. The code archive is 728331 bytes,
SHA-256 `763bb5bf8a75e90b1615d90758bdc30a54bfb937c3a5d437f3cf7082fa283ec4`.
The public runtime has the unchanged 453638809-byte identity recorded below;
all asset digests are in public `SHA256SUMS`. Stable latest remains `v3.9.0`.
No laptop installation or live isolation enforcement is claimed.

**Recovery history, 30 September 2026:** a workspace reset restored an earlier
checkout and lost later local commits and original runtime bytes. Source recovery
and a fresh complete runtime rebuild have since passed ordinary-user GitHub CI.
The exact rebuilt policies are now adopted in this source candidate. Earlier
results remain **HISTORICAL evidence for their exact inputs**. The original v2
collector source/archive remain unavailable; the supplied unchanged report still
establishes temporary system-manager feasibility.

**Restored in source; isolated regressions pass:** quiet login requests the
stopped stack once and preserves deliberate mute/off choices. Three ordinary-user
system-manager workers deny non-loopback IP; separate Weather/Media workers
retain online operations. Fixed-account polkit grants only five static service
names and three control verbs. Activation/removal tests cover injected reload
failures, private owned files, unchanged settings and stale compatibility relays.
Run/Stop, restart, microphone and log controls use actual worker identities.
The distinct version-3 collector tests actual workers with private single-use
tickets; absent, muted, wrong-source or inconclusive workers cannot pass.
These are source/fixture tests, not live service enforcement.

Runtime staging now requires the complete hash-checked closure and installation
receipt. The restored separate-bundle builder verifies packaged bytes; real
fixture-wheel tests cover deterministic output, staging and tampering. The
current bundle policy identifies the exact verified new archive; all 296 wheel
hashes, packaged bounds and the reviewed closure are checked before staging.
There is no resolver/source fallback. NumPy 2.4.6 and zero exemptions remain.
Ollama has a separate data-only network policy candidate preserving its existing
ordinary-user daemon, executable, models and CPU/GPU settings. Nothing has been
applied to the laptop. See [the bounded service candidate](core-isolation.md).

**Remaining stable acceptance:** actual OVOS/Ollama, model,
DNS/proxy/inherited-socket, voice, GUI, login, stage-switch and recovery
acceptance; effective Hermes permissions and owner repository review. Native
binary/source correspondence and licence review remain open before wider
redistribution. Runtime asset retention and final scans are completed for this
test release. Fresh source and full-history Gitleaks scans pass after tool recovery; the
production shell check also passes after correcting an unused loop variable.
The complete source recovery branch is published under the owner's authorisation.
The publication workflow validates and releases only this named test candidate;
no live laptop migration is performed remotely. The complete V4 scope remains.

**VERIFIED current ordinary-user GitHub evidence:** source run `36765769296`
passes security scans, production ShellCheck and the complete required suite
on Python 3.10, 3.11, 3.12 and 3.13. The clean-extracted code archive passes the
same complete suite and 350/350 non-executing policy cases. Runtime run
`36765769244` passes all 296 unchanged package versions and dependency metadata,
full hash-enforced offline and staged installation, three independent plugin
builds/hash installs/imports, OVOS overlay API imports, real ONNX inference on
50 silent frames with socket connects forbidden and no TFLite import, and
packaged bundle-byte verification. Compiler 13.3.0 and glibc 2.39 match the
recorded toolchain. The nine upstream source-built wheel hashes changed and are
explicitly recorded; their hash-pinned sources and metadata are unchanged. The
ONNX-only downstream wheel reproduces its existing hash. NumPy 2.4.6 and zero
exemptions remain. No positive wake/microphone or actual laptop-service claim
is inferred from these runs.

The latest inner runtime ZIP is 453638809 bytes, SHA-256
`03cbba7effa9046d9ce7a63b26d9a0b886eebf4f58f445dda2ae37af07e8c288`.
GitHub artifact `11120453380` retains it with independently verified small proof
artifact `11120708039`. CI artifacts expire after seven days. The exact candidate
wheel lock, artifact manifest and bundle policy are now adopted after independent
proof-digest, complete version/metadata parity and nine explicit hash-difference
checks. No package versions or dependency exemptions change. A separate workflow
retains these same bytes for 90 days without rebuilding; run `36772541316`
passes exact policy/archive and complete wheel/closure checks. Retained artifact
`11123863124` and proof `11124427704` expire on 29 December 2026. Source run
`36772321779` passes after candidate policy adoption.
Candidate adoption does not close live acceptance or publish a stable release.
Details are in
`voice/runtime-rebuild-evidence.json`.

**Remaining redistribution check:** the exact `espeakng-loader==0.2.4` wheel
embeds `libespeak-ng.so` without a separately identified licence/COPYING/NOTICE
entry. Upstream eSpeak NG uses GPLv3. Complete notice and corresponding-source
handling, including bundled native libraries, before broad runtime-bundle
redistribution; the report is an inventory, not a compliance conclusion. See
[upstream COPYING](https://github.com/espeak-ng/espeak-ng/blob/master/COPYING).
This does not change package versions or remove the agreed full-hash requirement.

**VERIFIED restored-candidate checks:** required source validation/routing/Qwen/
updater tests and the complete deployment suite pass. The rebuilt code archive's
clean-extracted copy passes the same suite, including preservation, staged
failure recovery, rollback and uninstall. Source and clean-copy policy runs
each pass 350/350 without model calls or desktop actions. All four surviving
plugin wheel checksums pass and their package bytes match current source.
Python compilation, shell syntax and diff checks pass. These checks do not
close the current artifact, scanner or live gates above.

**Publication privacy correction:** an approval review blocked the raw laptop
inventory upload. The original capture is retained privately and removed from
Git/public packaging and its manifest. Public runtime files now contain only
reviewed installer pins, wheel/source hashes and dependency metadata. Observed
model digests and source-install indicators remain in private evidence. Packaging and the
release scanner refuse an observed-runtime capture, including untracked backups. No runtime package version
or dependency exemption changes in this correction. The recovered runtime builder
uses an ordinary-user GitHub runner, verified upstream wheel hashes, nine
hash-pinned upstream sources and the reviewed ONNX downstream source. New locks
remain separate candidates until metadata, complete offline installation, staged
installation and archive byte checks pass; rebuilt hash differences remain explicit.
The workflow never publishes a release or changes a live laptop.

**VERIFIED in isolated tests:**

- Native and Qwen candidate coverage for current-app minimise, maximise and
  restore wording, retaining named-target checks. The 350-case policy run
  passes; it makes no model calls and executes no desktop actions.
- Distinct native `Speak selected text`, `Speak highlighted text` and 2× reading
  phrases reuse the existing reader and appear automatically in Commands.
  Reading/writing candidate separation tests pass. The owner's supplied trace
  first transcribes `Write this` and selects writing, then transcribes `Read
  this` and selects reading; acoustic accuracy remains a live gate. Existing
  writing behaviour is preserved, with no read-for-write substitution, command
  hint bias, microphone/model change or added writing confirmation.
- Shared terminal identity checks block generic writing, Enter, new line,
  period and space before input. Focus changes cancel typing/submission.
- Private agent prompts are captured, read back and require `send it` once.
  Cancel, timeout and native-command escape clear pending prompts.
- Reports redact quoted credentials, authorization schemes, credential URLs,
  nested locations, hostnames and IPv4/IPv6. Archives are private from creation,
  published atomically only when complete and never overwrite an existing path.
  Diagnostic material is explicitly untrusted; reports are never auto-uploaded.
- Window matching uses the WM_CLASS column. A browser title containing Zoom
  cannot pass. A running tray-only Zoom process returns clear feedback without
  relaunching or killing it; safe tray activation remains unverified.
- Updater transport requires HTTPS and reviewed GitHub hosts on every redirect.
  The public release API/checksum asset redirect chain passes. Manual archive
  checks remain, with Python's data filter added where supported.
- The reading helper verifies clipboard readiness before requesting playback,
  clears temporary text after the bounded handoff, and never restores a prior
  clipboard. Existing speed, lock, update cancellation, upgrade preservation,
  rollback and uninstall tests pass.
- **HISTORICAL pre-reset:** source and full history scans passed with Gitleaks 8.30.1. Two exact
  historical findings were inspected and are public Ctrl+Shift+End chords;
  `.gitleaksignore` contains only those reviewed fingerprints. ShellCheck
  0.11.0 warning-level checks pass for the changed production shell files.

**Implemented in source; live GUI acceptance pending:** separate Speech Note
open/guide actions, a bounded one-line activity banner, a scrollable guide with
Copy rule/one-second clearing, responsive two-column Voice and Maintenance
cards, more Results space, category/application icons, and green `Up to date`
only after a successful update check. Unchecked/failed checks remain distinct.

**Dependency feasibility evidence:** both supplied laptop reports contain the
same complete 296-package inventory, including `yt-dlp==2026.8.19`, matching the
then-reviewed pins. Their original inventory is retained separately. The V4
derived candidate retains NumPy `2.4.6` and changes only the wake plugin to the
clearly versioned `0.4.5a2+jarvis.1` ONNX-only downstream build. Its 296 wheels installed
with `--no-index --no-deps --require-hashes` in an isolated Linux x86_64
Python 3.11.16 environment. Complete installed inventory parity and the three
first-party plugin imports pass. Nine upstream source builds and the downstream
plugin build used a separately hashed
four-package build-tool lock with build isolation disabled. The source lock,
wheel hashes, complete metadata and toolchain evidence are recorded in `voice/`.
ALSA headers were extracted temporarily; no system packages were installed.
The upstream `0.4.5a2` plugin's `numpy<2` conflict is resolved in the candidate
by enforcing an actual ONNX-only boundary: TFLite is rejected before model
creation, default paths are explicitly ONNX, and runtime model downloads are
removed. The Apache-2.0 source, upstream archive hash and exact patch provenance
are packaged. All active constraints pass with **zero exemptions**; staged
dependency checks now reject every conflict. Actual plugin inference on 50
silent frames passes with real Hey Jarvis ONNX models, network connections
forbidden and no TFLite import. NumPy 1.26.4 was tested successfully as an
alternative and superseded to retain the owner's NumPy 2 stack. ONNX Runtime,
Faster Whisper imports and the Adapt
intent API pass. This is **candidate installation evidence**, not laptop
native ABI/model inference on the laptop, a reproducible OS/compiler toolchain
or current production acceptance. The current restored installer enforces full
hashes in its staged path; the full rebuilt artifact passes current ordinary-user CI, while
actual laptop acceptance remains required before stable release.

The dependency tool captures complete laptop pins and validates wheel hashes,
metadata, transitives and requested extras. It refuses incomplete/changed wheel
sets. [The laptop handover](v4-acceptance.md) describes the remaining gates.

**VERIFIED continuation:** the disposable offline probe copies and rechecks
actual wheel bytes, rejects altered/injected locks before installation, disables
indexes/dependency resolution/source builds, checks complete installed parity
and removes its temporary environment. A real local fixture wheel installs on
Python 3.11.16; the complete captured laptop wheelhouse also passes this probe.
Capture now records Python patch version and safe non-index source identities;
unknown/editable sources require review instead of being converted to PyPI pins.
Dependency markers use the captured Python patch version. One read-only laptop
report includes user services, system Ollama, safe configuration/Hermes
indicators and a loopback-only Qwen digest. No model is loaded or downloaded,
and no service rule, live environment or account setting is changed.

**Startup follow-up:** the second supplied report shows all five OVOS user
services active after the owner started them manually. It does not capture
login enablement or establish the boot failure's cause. Overview now separates
**Auto-start at login** from **Run Jarvis / Stop Jarvis**. Auto-start changes
only future login enablement of the existing `ovos.service` target and quiet
tray launcher; it neither starts nor stops current services. The private saved
choice and unknown fields survive updates and rollback. Failed writes or
partial enablement failures restore the prior state; unsafe/customised paths
stop for review. The read-only handover now reports login preference and actual
enablement. Regression tests pass; GTK interaction and the next real login
remain live acceptance gates.

**Conditional prototype:** Minisign 0.12 disposable keys pass authentic,
wrong-key, tampering and rotation-boundary tests. Production signing,
bootstrap-key distribution and updater integration are not enabled.

**Earlier blockers, still open unless explicitly closed above:** full-artifact
production hash-enforced staged wheel installation and
live voice/model acceptance; managed model
identities; actual core service egress enforcement with separated weather/web
functions; GUI/desktop/350-case real-model tests. This environment has no live
OVOS user services or GTK desktop. Hermes sandbox/tool permissions need a live
review. No blanket firewall, new daemon or speculative sandbox change is applied.
Full-hash and isolation failures require the owner's explicit scope decision
before final V4 release. No silent deferral or `fully offline` claim is permitted.

The items below are live acceptance gates. Pre-change descriptions explain
the original reported issues:

- [ ] Add an explicit, verifiable network-isolation mode instead of describing
  local operation as enforced offline isolation. The current router contacts
  Ollama only on `127.0.0.1`, but the installed OVOS user services have no
  outbound-network denial and UFW's existing inbound policy does not provide
  that guarantee. Define an **Offline enforced** mode that blocks non-loopback
  traffic while separate, narrowly reviewed weather/online helpers, Brave music
  and the updater retain their intended online functions. Keep **Local-first**
  as the accurate current label until enforcement is proved. OVOS
  loads core routing and some network-backed skills in the same process, so do
  not apply a blanket service restriction until those boundaries and failure
  paths are tested. Add negative egress tests and do not claim air-gapped
  operation until live verification proves the block.
- [x] Add a scoped performance comparison to the local-routing documentation.
  Keep post-transcription native routing, the small warm Qwen diagnostic,
  independent smart-speaker observations and research desktop-agent timings
  explicitly separate. Do not market unlike workloads as one benchmark, and
  retain the full 350-case laptop run as pending acceptance evidence.
- [ ] Treat `minimize/minimise this app` and `this application` as focused-window
  requests in both native vocabulary and the Qwen safety filter. Audit the
  equivalent maximise/maximize and restore forms at the same time. Add positive
  benchmark variations while retaining the rule that named-application actions
  require an enabled, recognised target. Live evidence: `Minimize this app` was
  transcribed exactly, missed native routing, lost `window.minimize` during
  candidate filtering and correctly ended with `Please repeat.`
- [ ] Redesign the Speech Note setup result in the Control Centre. The current
  pre-V4 action placed the helper's complete multiline guide in the top activity
  banner, expanding it and pushing the working page downward. Keep the banner
  to one concise status such as `Speech Note opened`. Put the formatted setup
  guide in a fixed-size, scrollable dialog or an in-card expander with clear
  sections, a monospaced wake-filter pattern and a **Copy rule** action. Keep
  **Open Speech Note** and **Setup guide** as separate, clean actions, preserve
  existing settings, and add a GUI regression proving long guidance cannot
  resize or displace the main Control Centre layout.
- [ ] Replace the Updates tab's disabled `No update available` wording with a
  calm green healthy state labelled **Up to date**. Keep update failures and
  unchecked state visually distinct; green must mean a completed successful
  check against the published release, not merely the absence of cached data.
- [ ] Add meaningful icons throughout Apps & Commands defaults: symbolic icons
  for default categories such as Browser, Mail, Notes and Office, plus each
  application's real desktop icon where available and a consistent generic
  fallback where it is not. Preserve text labels and accessible names so the
  icons improve scanning without becoming the only identifier.
- [ ] Rework Voice and Maintenance into balanced two-column card grids instead
  of one long vertical stack. Pair related Voice cards and Maintenance cards in
  one row of two at the normal Control Centre width, while retaining a readable
  stacked fallback for narrow layouts. Restyle Advanced as a deliberate compact
  section with clear action descriptions rather than a visually unfinished
  expander, and give **Results and details** the reclaimed space as the large,
  stable output area. Add visual/layout checks for equal card alignment,
  wrapping and unchanged window height.
- [ ] Restore Zoom correctly when its main window has been closed to the tray.
  Live evidence confirms the exact `Open Zoom` transcription and native intent
  succeed, while starting Zoom again hands off to the existing tray process and
  produces no window for `jarvis-app-window` to focus. Detect these states
  separately: focus an existing window; otherwise, if Zoom is already running,
  activate its real Cinnamon tray/status item; only launch Zoom when no process
  is running. Do not kill or restart a running Zoom process because it may own
  an active meeting. If safe tray activation is unavailable, say that Zoom is
  running in the tray instead of waiting ten seconds and reporting a false
  launch failure. Verify the tray protocol and observed process/window identity
  on both native and Flatpak installations, retain exact allowlists, and add
  visible-window, tray-only and cold-start regressions.

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
