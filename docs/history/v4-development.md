# V4 development record

**HISTORICAL:** these trial notes preserve their original evidence, limitations
and decisions. They are not current installation instructions. Use the
[current release record](../releases.md), [commands](../command-reference.md)
and [installer guide](../07-installer-updates.md) for stable V4.

## Post-rc2 music correction (verified source and exercised laptop retry)

Media 0.3.5 queues its acknowledgement immediately, then waits three seconds
after finding a valid result before opening it, regardless of lookup duration. Stop and title replacement cancel the remaining wait. The shared
11-second gap, bounded single search, direct route and Qwen fallback remain.
These timings provide a comfortable transition, not a provider-alert guarantee.

Weather stage measurements identify roughly 12.5–13 seconds in a new location's
search and reverse lookup, plus roughly two seconds in forecast retrieval.
A repeated location skips those city lookups. These measurements do not isolate
network transport from provider response time or prove that Stop interrupts a
pending lookup. No network-policy, dependency or weather-provider change is
included in this timing correction. **VERIFIED source:** commit
6dd4283e080160a640aa358d61a44b1d40772412, run 36819524368 passes all six jobs,
including fast/slow lookup timing, post-result cancellation, Python 3.10–3.13,
GTK, source/history/archive scans, full deployment/recovery, 350/350 clean-copy
policy cases and all 296 reviewed dependencies with zero exemptions.
The guarded two-file handover in commit
884259cf18c4df25819d630e78dcbee921fb700f uses immutable source/checksums and
private Downloads backup, registers only Media locally without dependency
resolution, and restores source/prior registration on failure. Its automated
validation passes all six jobs in run 36819754595, including source guards,
source/registration rollback, three-second transition cancellation and
350/350 clean-copy policy cases. The exercised laptop music retry passes;
Stop/replacement interruption remains automated evidence only.
See [music timing handover](../v4-media-timing.md). The published rc2 archive/tag
is unchanged.

## Post-rc2 weather and handler correction (verified source; exercised laptop weather)

**VERIFIED owner music timing:** the owner reports the final patch works and
the song timing is satisfactory. The acknowledgement is queued before the
lookup thread, without waiting for TTS completion. Queue replacement and Stop
acceptance still need their separate live checks.

**VERIFIED diagnostic finding:** two named-city weather commands match in
about 0.55 seconds, then take 15.4–16.5 seconds before the first speech submission.
This locates the main delay after intent matching; the provider/lookup/display
split is not yet measured. Inspection of the exact pinned Weather 1.4.8a1 source
finds that it resolves the named city for labels but passes the configured home
coordinates to its forecast call. A source-hash-guarded in-memory adapter clones
only that request's coordinates/timezone from its resolved location. Saved
configuration, session preferences, units, intents and provider restrictions
stay intact. Stage/provider timing logs contain no city or coordinate values.
This correctness correction does not claim the latency is resolved.

Media 0.3.4 carries its fixed remote owner in match data and includes the fixed
intent name in its completion signal. This allows core's existing dispatcher
to resolve the handler without activating an unloaded local skill or producing
a false five-minute timeout. Search pacing, acknowledgement order and Qwen are
unchanged. **VERIFIED:** source 1576681ec61d37c5363873c9ecf41a73f8ed900b,
run 36817087134 passes all six jobs, Python 3.10–3.13, GTK, source/history/archive
scans, full deployment/recovery and clean-copy policy checks. The exact
hash-locked Weather methods fetch separate named-city coordinates without
changing home preferences. The exact pinned core dispatcher reproduces the old
Media timeout and resolves the corrected owner exactly once. A four-file
normal-user handover checks known source identities/stopped workers, preserves
settings/policy and registers only Media offline, with private Downloads backup
and rollback. **VERIFIED handover:** commit
b20302fa9d334f86ba9b366b47f5dbfa81b2406a, run 36817351596 passes all six jobs,
including normal-user/stopped-worker/custom-source guards, complete source and
registration rollback, exact upstream regressions and 350/350 clean-copy cases.
Script SHA-256: c9e814e47f36e22adb1d8eff9a12288c19491bb656b78c679324aff31e5500c7.
See [weather handover](../v4-weather-handover.md). The public rc2
tag/assets are unchanged.

**Owner-deferred compatibility gaps for a future release:** the supplied named-city time question transcribes
correctly but finds no time intent. The installed time skill has city phrases,
yet its built-in resolver attempts online geocoding before local tables; the
core must remain blocked. Wikipedia/WikiHow are installed but disabled by the
isolation load blacklist and have no separate reviewed online worker. The
supplied pie question therefore falls through to local Qwen, which times out.
Do not call those web skills enabled, silently restore their core network access,
or label this local-model timeout an internet failure. Restoring supported web
answers/world-time routing is recorded for the future release at the owner's
request, with these V4 limitations kept visible.

## 4.0.0rc2 (published cumulative laptop test; stable release pending)

**VERIFIED publication:** release 400636664, tag `v4.0.0rc2`, commit
`cc35fd7484d96dee05544082809549a8b8ee30da`. Source run 36812460617 passes all
six jobs, including guarded handover rollback/new-file removal and 350/350
clean-copy policy cases. Publication run 36812460641 verifies the retained
296-wheel closure, rebuilds only current first-party wheels, checks their exact
source inventories, scans the final archive/assets, repeats the clean-copy
suite, publishes 11 fixed assets and downloads them again to verify checksums
and the public tag. Archive SHA-256:
`73166faa5d5e65db5e1a2db391615a6aee85c30a3d3611f8fc196d65a8da0010`.
The 453638809-byte runtime digest remains
`03cbba7effa9046d9ce7a63b26d9a0b886eebf4f58f445dda2ae37af07e8c288`.
The immutable handover script SHA-256 is
`d45039137946df746645d1c89fefc7688c8079ba8c10465f5582bbacedb9b95c`.
Stable latest remains 3.9.0; the owner laptop queue/weather interruption and
broader isolation/recovery gates are not declared complete by automated checks.

**Owner-directed final music/UI/installer correction, source candidate:**
Media 0.3.3 restores the deliberate-title fast route across the existing local
bus when the separate helper reports ready. The original owner blacklist is
checked before applying the isolation load blacklist, including configuration
reloads. Remote delivery uses the fixed pipeline-owned helper event and never
activates a Media instance deliberately unloaded from core. Qwen remains the
semantic fallback. The owner selected an **11-second gap between searches**;
accepted music requests acknowledge once, wait locally and cancellably for the
remaining gap, and perform one lookup. Only the latest pending request is kept.
Stop cancels it; provider challenges never trigger retries. The brief 0.5–1
second pre-search pause and 0.35-second result transition remain. No timing
value guarantees avoidance of provider alerts.

The exact pinned Padacioso adapter serialises mutation callbacks to prevent
concurrent detach check/remove races, preserving alias and language handling.
Boot acknowledgement reuses the existing listening cue for the missing default
sound, retaining custom sound choices. Upstream deprecation notices remain
visible; background intent compilation remains enabled and is not labelled a
fault based only on its duration. The disabled green update button's label and
icon are explicitly white. CLI installation now reports initial checks, measured
download/archive/wheel progress and continuing activity during slow phases;
percentages describe measured work, never readiness or elapsed-time guesses.
Tests for these boundaries pass in the runs recorded above; exercised laptop music timing
is accepted in the post-rc2 checkpoint above. Frozen dependencies, models and native IP policy
are unchanged.

**VERIFIED source checks:** commit 2df1de58bdd09520606cbaa2ee2aa89ef839dc8f,
run 36812008636 passes all six jobs: Python 3.10–3.13, GTK, source/history/archive
security scans, full deployment/recovery and 350/350 clean-copy policy cases.
The exact pinned Padacioso detach method reproduces the reported race without
the adapter and passes concurrent/alias/language preservation checks with it.
GTK checks the computed white label/icon colours. The immutable 13-file normal-user
handover targets those passed bytes, checks stopped native workers and
known source identities, backs up in Downloads, and registers only Media with
no index/dependency resolution. Handover rollback and cumulative release
packaging/public-byte verification pass in the publication record above.
See [cumulative handover](../v4-final-candidate.md). Stable V4 remains subject to
the retained live acceptance gates; this does not replace the original rc1 tag.

## 4.0.0rc1 (published laptop test; stable release pending)

**VERIFIED owner laptop lifecycle retry, 30 September 2026:** after the guarded
patch, the owner reports the ready announcement working, all voice services
starting with green status and the tray returning to grey on Stop. This closes
the exercised announcement/start/stop UI regression. It does not prove repeated
fresh-login cycles, every recovery path or a uniquely identified old lingering
thread. Music/browser latency improvements and the remaining stable release
gates remain unconfirmed.

**Owner-requested lifecycle and latency correction, source candidate:** the
boot announcement uses enabled local service/skill readiness replies instead
of waiting for default blacklisted skill IDs. Explicit ready_settings,
speak_ready and ready_sound choices remain intact. A per-instance stop event
cancels pending checks between bounded bus waits; duplicate checks coalesce and
the announcement is single-use after confirmed readiness. The in-memory adapter
requires the exact reviewed upstream source hash. The supplied journal shows
main cleanup completes before a residual-process stop timeout; callback
cancellation addresses a supported candidate cause; the owner subsequently
confirms the exercised laptop Stop returns the tray to grey. Stop errors never restart voice through recovery and failed
shutdowns remain visible. The web-dependent wallpaper skill joins the core
blacklist; Weather/Media retain separate online workers.

Media 0.3.2 starts lookup before its nonblocking acknowledgement and shortens
the post-result transition to 0.35 seconds. Browser/visible YouTube search pacing
is 0.5–1 second, typing 10 ms per character and the final focus-checked pause
0.2 seconds. The shared 12-second anti-burst reservation, one bounded result,
cancellation, challenge reporting and browser allowlist remain. No bot-evasion
or provider latency guarantee is claimed. Existing frozen runtime bytes and
models are unchanged; the independently versioned Media plugin changes.
**VERIFIED:** source commit 36e9fc7a9abd8be10992d1a8b3466f51761c4129,
run 36807773926, passes Python 3.10–3.13, GTK, security/source/history/archive
scans, full deployment/recovery and 350/350 clean-copy policy cases. The exact
hash-locked upstream boot class passes readiness and real executor-cancellation
integration. Owner announcement/start/stop UI retry passes above; live
music/browser timing and broader lifecycle acceptance remain open.
A bounded owner-terminal patch checks exact installed/source hashes with stopped
workers, backs up privately in Downloads and registers only first-party Media
locally with no index/dependency resolution; native policy/settings/models stay.
The guarded handover commit 5e3451773fef0d756b3b45eaaa6a834aee8ed004
also passes run 36808258392, including complete source/registration rollback,
unknown-source/stopped-worker guards and the repeated clean-copy suite.
This source candidate does not retag the original published test archive.

**Slow-start readiness correction, source candidate:** the supplied core log
shows more than 74 seconds of skill loading before the dispatcher's ready
marker, exceeding the Control Centre's former 60-second wait. That timeout can
enter recovery and leave the microphone paused even though Commands finishes
loading later. Allow a bounded 180-second default wait, report continued loading
every 15 seconds and retain current-invocation readiness markers. An actually
failed worker fails immediately; never-ready workers still time out. No setting,
microphone preference, native unit or dependency changes are made.
**VERIFIED:** source commit `0aad146972e2494655755ae5d819c807c41165e6`,
run `36805354003`, passes delayed/never-ready/failed-worker regressions,
Python 3.10-3.13, GTK, security scans and the complete clean-copy deployment/
recovery suite. The later lifecycle patch and owner retry above close the
exercised start/announcement/stop regression; this earlier wait-only change
does not independently fix the latter two.

**Isolation desktop regression, source correction:** systemd 255 treats enclosing
quotes in `EnvironmentFile=` as literal filename characters and ignores the
resulting non-absolute path. The saved session could therefore be correct while
workers started without the desktop environment, breaking selected-text reading
and focused-window actions. Generate the literal absolute path with percent
specifier escaping, retaining the existing private session file, ordinary-user
identity and network policy. Exact legacy candidates remain accepted only for
removal; new activation rejects them. A native parser regression reproduces the
ignored quoted setting and checks paths containing spaces and percent signs.
**VERIFIED:** source commit `1e0c525c1e7cb02c6c28caba16d51315093ac087`,
run `36803027157`, passes the native parser and legacy-removal regressions,
Python 3.10-3.13, GTK, security scans and the complete clean-copy deployment/
recovery suite. Owner native-data repair and desktop acceptance remain pending.
This does not establish the separate microphone Stop/Start cause.

**Owner-directed controls refinement, source candidate:** Overview is labelled
Dashboard; General contains separate **Start app minimised at login** and
**Start voice services at login** switches. Tray startup alone never starts
voice. A separate quiet voice-login entry makes service startup work when the
tray is disabled; enablement, settings and launcher writes recover together on
failure, and changing a future-login preference never starts/stops current
services. Legacy combined preferences retain their meaning; independent
settings and unknown fields survive updates. Install/rollback/uninstall include
the new owned voice-login entry. The Updates button itself is green when current
and blue when an update is available, with neutral unknown/failed states and no
duplicate green status line. Real GTK and four-combination startup regressions
pass. **VERIFIED:** source commit `dacc2cdb35c585e715642971b7b85269457c9e5d`,
run `36793219822`, passes real GTK 3, all four Python versions, security scans,
independent login/failure/privacy regressions and the complete clean-copy
deployment/recovery suite with 350/350 policy cases. Owner laptop checks remain
pending; publishing the source does not update an installed laptop.

**Owner-directed review location:** new core and Ollama candidate directories
default to Downloads, with private directories/files and accurate native source
paths in REVIEW.md. Existing private-state candidates remain supported. Source
fingerprints still reject stale candidates; nothing is installed or activated
by preparation. The owner's supplied candidate has matching file/source hashes
and reviewed narrow policy; that is file review, not actual egress enforcement.
The uploaded candidate and client account/path/model data remain outside Git.

**Post-install GUI finding:** owner reports working V4 commands, but opening
the Control Centre fails when restoring a default app. Icon rows use a custom
GTK child, so the radio button's `get_label()` returns `None`. The source fix
retains each option's display text and refreshes the selected label, icon and
accessible name even if the radio was already active. It changes no app choice,
voice setting or runtime dependency. A real GTK 3/Xvfb regression checks initial
and repeated restoration, user selection, reset and rebuilt choices.
**VERIFIED:** commit `0c705c77f357bf5c1a803094cc9c9aa4c8caa7c6`, setup SHA-256
`059510eeed465406325615344e72feac323a809a29b68d04bb82a5cfe03323f7`, passes run
`36791112074`: real GTK 3, all four Python versions, security scans and the
complete clean-copy deployment/recovery suite with 350/350 policy cases.
Owner GUI retry remains open; microphone-wide acceptance is not inferred from
the reported successful normal commands. The original frozen release needs
this additional GUI source fix, now included in the testing instructions.

**Implemented source requirement; validation pending:** the owner clarified that initial feedback is
missing in the CLI installer, not the GUI. Show current steps and visible
activity throughout slow download/verification/staging phases, with a green
progress bar for measurable progress and an activity indicator otherwise.
Do not invent percentages or leave a silent initial phase. The GUI already
has its progress bar; real CLI download/verification feedback is now included.

**Post-publication dependency verifier finding:** the laptop's bundle staging
rejected `phoonnx -> ovos-number-parser>=0.4.0` although the exact selected
version is `0.22.17a1`. Packaging before 26 rejects prereleases by default in
membership checks; the CI library accepts them. The source hotfix explicitly
checks the exact reviewed pins with prereleases enabled, retaining every bound,
exclusion, complete-inventory check and wheel hash. No package, dependency
metadata or zero-exemption policy changes. CI now tests the actual packaging
24.2 source and complete 296-package closure in addition to current hosts.
The laptop failed before its runtime or app configuration was replaced.
**VERIFIED:** source commit `8df0002e2aa3e57b0e178681827bb648933376c6`,
verifier SHA-256 `8b032f679e1c3ac87305e7f4fbbfc8e902b54797dd523c738b997a6848d433c5`,
passes run `36787735811`: all four Python versions, security scans, clean-copy
deployment/recovery tests and 350/350 policy cases. The actual packaging 24.2
compatibility step reproduces the old implicit rejection and passes the full
296-package closure and out-of-range/excluded-alpha failure cases. The runtime
archive and package identities remain unchanged; the original release archive
uses the immutable hash-verified source fixes in the testing instructions.

**Current password-free hotfix:** owner requires routine updates to remain
password-free. The revised guard invokes only read-only system-manager show
for the exact five worker identities, with authentication explicitly disabled.
Protected polkit-directory access alone is not a deployment blocker when all
workers are definitively not-found/inactive with no fragments/drop-ins and
other native paths/receipts are absent. It does not inspect or declare a hidden
rule missing. Existing/loaded workers, visible native policy, Ollama policy,
incomplete/error/denied state and timeouts still block. Source commit
`ee07b82d1d50a9edaa25c43d7a8dff351f1ad2c7`, guard SHA-256
`cd217b562dee0c635dfb16a46233a2d913045f606f387ce3fcd782787a646231`,
supersedes the first sudo-stat approach. Native isolation setup/removal remains
separate administrator work; ordinary updates add no sudo privilege.
**VERIFIED:** run `36786203107` passes security scans, all four Python versions,
loaded/stale/incomplete-state regressions and the complete clean-extracted
deployment/recovery suite with 350/350 policy cases. The hash-verified testing
instructions now use this password-free guard.

**HISTORICAL first hotfix, superseded:** the initial installer guard stops before
any Jarvis changes when the native polkit directory cannot be traversed by the
desktop user. A bounded source hotfix checks only the current account's public
rule with cached owner-authorised native stat; it requires a definite missing
file result and continues rejecting existing policy or unknown/denied checks.
Fixture checks cover exact arguments, protected directories, absence, existing
rules/symlinks, missing authorisation and timeouts. The published archive/tag
remain unchanged; the immutable, hash-verified source hotfix is applied to the
downloaded copy for this laptop test. **VERIFIED:** hotfix commit
`5280ae9339584da040e5d1e4caff21abc1043c4e`, guard SHA-256
`563ceb016f71a3207f0e940d3168796a2447758ee2913a2dfe81235dcf2dc456`,
passes run `36785366867`: all four Python versions, source/history/archive
scans and the final clean-copy deployment suite with 350/350 policy cases.
That first proposal was superseded by the owner's password-free requirement.
Current [installation instructions](../v4-laptop-test-release.md) use the revised
guard above. See
[troubleshooting](../troubleshooting.md).

Status: **Implementation in progress. Owner authorised completion and publication;
artifact and live acceptance gates remain open.** This entry supersedes the collection-only checklist; the full
agreed scope is retained in the owner's V4 implementation plan.

**Owner decision, 30 September 2026:** publish this candidate as a prerelease
for the current laptop, including the exact verified runtime and plugin wheels.
The stable channel remains 3.9.0. Production signing is deferred until wider
deployment; 3.9 response speed and Brave session-expiry recovery are accepted.
This approval does not assert live voice/startup/isolation acceptance. See
[test release and installation](../v4-laptop-test-release.md). Native notices and
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
applied to the laptop. See [the bounded service candidate](../core-isolation.md).

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
sets. [The laptop handover](../v4-acceptance.md) describes the remaining gates.

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


## Original expanded stable release notes

# Jarvis 4.0.0

V4 brings the working Linux Mint/X11 voice-control stack together with reviewed
runtime hashes, clearer startup controls and optional service network isolation.
The dispatcher is 4.0.0, Media is 0.3.5 and File Search remains 0.3.0.

## Security and reliability

- Complete 296-package runtime with exact versions and enforced wheel hashes,
  zero dependency exemptions, retained NumPy 2 and an ONNX-only wake plugin.
- Optional native policy denies external IP traffic for core/listener/audio and
  Ollama while weather and browser music use separate online paths. Activation
  remains an explicit reviewed step; installation alone does not isolate core.
- Generic terminal writing/submission is blocked. Tool-capable private-agent
  prompts require readback and a single-use explicit confirmation.
- Selection reading clears its temporary clipboard text without restoring the
  previous clipboard. Support reports use private atomic publication and
  redact reviewed credential/location forms.
- HTTPS-only reviewed update hosts, bounded archive extraction and recoverable
  installation preserve settings, application choices, models and private helpers.

## Everyday improvements

- General separates starting the app minimised from starting voice services at
  login; Dashboard controls Run/Stop for the current session.
- Readiness follows actual worker replies. GUI status, icons, card layout,
  setup guide, update cancellation and CLI progress have been improved.
- Current-app window phrases and WM_CLASS targeting are consistent. Zoom's
  tray-only state receives honest feedback without restarting an active meeting.
- Music acknowledges immediately, uses the direct isolated-helper route with
  Qwen fallback, then waits three seconds after finding a result before opening.
  `Put on {title}` is an alternative to `Play {title}`.
- Named-city weather forecasts use resolved city coordinates and timezone.

## Accepted limits

Music can open another tab without stopping an earlier tab. Brave's idle-session
expiry remains outside Jarvis control. Provider requests have an 11-second
shared search gap; no timing guarantees avoidance of provider alerts.
New weather locations can take about 15 seconds; cached location lookups are
quicker. Weather Stop during retrieval remains unverified. City-time routing
and online Wikipedia/WikiHow answers are deferred and web skills remain disabled
in restricted core.

The local bus, desktop session and same-user plugins remain trusted. Full
acoustic/real-model coverage, all desktop/login variants, mediated/inherited
socket and native recovery acceptance, effective Hermes permissions and owner
account/repository protections are not certified by this release. Production
signatures, Flatpak and complete fresh-OS/model offline installation are later
work. The runtime ZIP contains wheels, not all voice/Qwen model data or OS tools.

## Install and update

Download `ovos-commands-4.0.0.tar.gz` and its matching `.sha256`. Normal setup
uses the separately hash-verified `jarvis-runtime-linux-x86_64-py311.zip` from
this release. A saved copy can be supplied with `--runtime-bundle PATH`.
Use [installation guidance](../07-installer-updates.md).

An already patched laptop has the latest behaviour code. No reinstall is needed
merely to exercise the same fixes. The normal installer/updater refuses remaining
native isolation data; use the reviewed deactivation/removal path before a full
managed update. It does not silently replace active protected workers.
Original rc1/rc2 releases remain available. Source, automation and publication
evidence are recorded in [releases](../releases.md).
