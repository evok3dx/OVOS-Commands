# Decisions and constraints

**VERIFIED** means code or a recorded machine test supports the claim.
**PLANNED** means agreed intent with no completed implementation.
**HISTORICAL** retains older context without presenting it as current.
Contradictions stay visible in the [historical audit](history/v2.4-audit.md).

| Decision | Why and limits | Revisit when |
|---|---|---|
| Private temporary delivery, public reusable solutions (**VERIFIED owner direction, 6 October 2026**) | Deliver owner-test patches and bundles as private attachments with SHA-256 checksums and a known source baseline. Keep disposable delivery/staging files out of Git. Maintain finished code/tests and concise, sanitised issue/solution records in the existing troubleshooting, release and history documents. Earlier public repairs remain until supported upgrade/recovery references can be retired safely. | A temporary fix becomes a maintained compatibility repair or the release/support process changes. |
| Guard standalone helper lifecycle (VERIFIED automated for 4.4; live acceptance pending) | Media and Weather use a per-container lock around the exact reviewed Workshop lifecycle. Initial readiness and ready events cannot leave orphan handlers; activating a loaded helper is idempotent, legitimate reload/reactivation stays available and final shutdown rejects late loads. Future standalone helpers must use this path and extend the exact-wheel regression. Core-loaded plugins are unaffected. See the [release record](releases.md). | Workshop source or helper ownership changes; revalidate the adapter rather than weakening its hash check. |
| Useful fixed diagnostics (VERIFIED automated for 4.4; live acceptance pending) | Exact reviewed sites map to constant failure/stage labels and relative capture time. Validate optional wire fields; distinguish absent collectors and skip standalone helper collectors in ordinary deployments. Keep five-minute expiry, no persistence and no original messages or private arguments. | A new reason or collector is added; extend privacy regression rather than restoring raw logs. |
| Two logging modes (VERIFIED automated for 4.3; live acceptance pending) | Default No logs suppresses raw managed voice-worker output. Diagnostics for 5 minutes stores only bounded technical fields in process memory, expires without the GUI and never retains utterances, messages or tracebacks. Readiness is separate current-process state. Recent Activity remains a bounded in-memory feed of action labels. Existing logs, exported reports, Speech Note and unrelated applications are separate. See the [release record](releases.md). | A diagnostic needs additional fields; approve an explicit allowlist rather than enabling raw upstream logging. |
| Separate GUI update and service-control locks (VERIFIED in cross-process tests) | Keep duplicate updates blocked without holding the installer's Stop/recovery lock. Existing 4.0.1/4.2.0 GUIs need the reviewed one-time repair. Refuse source changes while an interrupted-install journal remains. | The GUI/installer coordination protocol changes; retain regressions against the released updater. |
| App-scoped Light/Dark appearance and session activity (VERIFIED in automated tests) | Theme changes preserve services/login choices. Activity stores bounded reviewed results in memory, without transcripts, queries or user-supplied labels. | Wider activity coverage or persistence is proposed. |
| Readable review/report folders and visual isolation status (VERIFIED in automated tests) | New Downloads folders use timestamps and numeric collisions. Existing candidates and internal tokens stay intact. Inspected native policy is displayed separately from actual network tests. | A new diagnostic or enforcement boundary is introduced. |
| Stage the reference system-compatible voice stack for V3.1 (VERIFIED in isolated switch/rollback tests; laptop voice test pending) | Keep existing local models and settings while updating the normal OVOS virtualenv as a unit. Preserve the entire previous virtualenv so a failed migration can revert. The old preserve-only policy is HISTORICAL for V3. | Revisit if laptop voice checks expose a dependency or media regression. |
| Build the 3.1.1 OVOS stack from a clean environment (VERIFIED in isolated transactions; real resolution and live voice pending) | Copying the old laptop virtualenv retained incompatible legacy packages even after selected core pins were upgraded. Build a new staged virtualenv from the complete final reference system audit, reject version/dependency/entry-point/launcher failures before swapping, and retain the old virtualenv for rollback. The dispatcher and two bundled plugins remain separate. Machine configuration, models, app choices, personal commands and private helpers stay outside the clean environment. The earlier partial-pin/copy approach is HISTORICAL. | A clean resolver cannot reproduce the reference system set, the ONNX runtime probe fails, or live laptop tests expose a package that must be machine-specific. |
| Select a microphone path explicitly (VERIFIED in isolated and live tests) | One backend opened successfully on a tested host but delivered unusable audio, so fallback could not activate. Use reviewed SoundDevice `0.0.3a9` first on an unset configuration, retain ALSA `0.1.3` as fallback, and preserve every explicit module/device. | Live capture fails through SoundDevice, or upstream provides reliable capture-quality negotiation. |
| Require the reviewed local Qwen model for V3 guided installation | A model helps with varied phrasing but must not choose arbitrary shell, keys or disabled apps. Prompt before downloading a missing model; preserve an installed model and existing timeout. Reuse local Ollama; no new listener port. An absent Ollama service or different saved model stops for review. | The older i7 fails a real latency or safety test and a different routing profile is approved. |
| Bundle Media and File Search as separate local OVOS skills | The final reference system snapshot contains integrated Media and file-search 0.1.9. Supplied reviewed packages separate bounded title routing and read-only filename search from core commands. Keep core's action allowlist and one current GUI command source. | Live upgrades fail reference system/laptop acceptance or the packages' dependencies become excessive. |
| Keep reference system media on `ovos-audio` OCP (**VERIFIED offline for 3.9; live pending**) | The experimental standalone `ovos-media` trial caused queue/control instability; provider/extractor access to YouTube is intermittent. The repeated Common Play Stop traceback is traced to the reviewed player implementing `stop()` without Workshop's required `can_stop()`. Patch only exact Common Play `1.3.10a1` source with the reviewed hash, return true only while playing or paused, compile before replacement, and retain the original for rollback. | Upstream Common Play supplies the compatible method, the reviewed source changes, or live Stop testing still fails. |
| One tray icon and native GTK Control Centre | Service, update and Jarvis microphone state fit together; avoid a second polling icon or local web server. | GTK becomes unavailable on supported hosts. |
| Keep private host helpers outside managed release paths | Machine-specific code and secrets should survive portable Jarvis updates. | A helper becomes a reviewed cross-machine capability. |
| Match the installed reference system Whisper prompt without expanding its cues | The final installed helper includes dynamic app names and a short media/writing list. Match that reviewed behavior in the candidate and test the plugin source exactly. A false “Pause music” event was recorded before the newer hint, but its cause is unknown. | A measured recognition or false-trigger result supports a narrower prompt; do not add commands speculatively. |
| Stop if an older plugin's local installer source is missing | The current rollback reinstalls the prior Media/File Search package from pip's recorded direct URL. A deleted local source would leave rollback incomplete after an upgrade. Check its presence before changing Jarvis. | A self-contained backup of the exact prior wheel or a tested different rollback mechanism is implemented. |
| Publish V3 with documented remaining machine checks | The owner confirmed both new plugins work and expressly requested publication. Keep the older unrelated OCP/NPR error, i7 latency, and full live upgrade/rollback checks visible; source and isolated tests do not prove those paths. | A live check exposes a regression; prepare a small corrective release and update the evidence. |
| Documentation reflects evidence | Code/tests describe behaviour; this log records intent. Preserve unresolved requirements and show proposed deletions before removing them. | A verified source revision supersedes a documented decision. |
| Preserve Speech Note rules and guide the wake-filter step (**VERIFIED in setup source; live GUI step pending**) | The working reference system manually filters its wake phrase in Speech Note so the phrase used to stop continuous dictation is not inserted. Speech Note applies rules sequentially, so a plain `Hey Jarvis` replacement can leave a final full stop. Setup now guides one case-insensitive STT regular expression covering the comma and optional full stop, warns that a changed wake phrase requires a changed rule, and preserves every existing rule. Speech Note's public D-Bus API does not manage rules, and its stored `QVariantList` is not safe to overwrite. | Speech Note exposes a supported rule API, or a tested Qt-native merge can prove it preserves unknown rules and future schemas. |
| Use one-turn dictation for Hermes, Claude Desktop and private agents (PLANNED until tested on a desktop) | The owner prefers “Ready,” one dictated message, then “Message sent.” Hermes opens a fresh chat; both desktop apps verify focus before submitting. Native media commands and blank speech do not send; private agents use the allowlisted helper. A mistaken but plausible transcription beyond the excluded commands remains a risk, so test the microphone path before release. This replaces an uncommitted Hermes confirmation proposal. | False sends recur in live tests or the allowed commands need a broader escape mechanism. |
| Route reading by exact target and speed (VERIFIED offline; live pending) | Qwen may select only selection/page at the requested 1× or 2× speed. A changed speed is rejected before dispatch, timeout yields to native intents, and the command editor groups actual phrases by the action they trigger. This keeps the existing focused-window check and does not add Whisper hints without measured recognition errors. | Spoken tests expose a mismatch or an unsafe candidate action. |
| Separate unmatched command feedback from general fallback (**VERIFIED locally; live rc10 pending**) | A live rc9 trace proved DDG medium fallback claimed “Purple Bananas Now” before Jarvis's final reply stage. Insert one narrow stage after native/Media/Qwen command routing and before broad fallback. It claims only recognised non-question commands and says “Please repeat”; empty/wake-only input stays silent and real questions continue to DDG/common-query/Qwen chat. | A useful non-question fallback is pre-empted or a real question stops reaching its answer routes. |
| Treat 2× reading as a reversible transaction (**VERIFIED locally; live rc10 pending**) | Rc9 could report a Speech Note connection failure while its delayed Flatpak launch later began at 2×, leaving the running app at that speed. Allow up to ten seconds for cold-start task-state acceptance; on failure terminate both the pending launcher and Speech Note before restoring the saved speed and clearing the marker. Never permit a late start after reporting failure. | Speech Note adds a supported runtime speed API or live cancellation/restoration still fails. |
| Preserve the user's Speech Note speed; make spoken 2× temporary (**VERIFIED offline for V3.2; live pending**) | Ordinary “read this” uses the current Speech Note speed, including a manually selected 1.5× or 1.8× preference. An explicit “at 2×” request temporarily uses 2×, restores the exact prior value, and reopens Speech Note if Jarvis had to restart it. The tray and Control Centre deliberately have no second speed setting that could disagree with Speech Note. The rc13 fixed-1× interpretation is HISTORICAL. | Speech Note provides a reliable runtime speed API, or live playback exposes a restoration/reopen failure. |
| Scope reading locks to setup, not playback (**VERIFIED by 3.8 regression**) | The reversible 2× monitor may live for the whole passage, but it must close the setup lock descriptor before backgrounding. Otherwise one accepted 2× request can make later normal reads falsely report contention. Keep the monitor, speed restoration and late-launch cancellation intact; do not weaken the transaction to fix the lock. | Speech Note exposes one atomic read-with-temporary-speed API, removing the external monitor. |
| Treat the clipboard as transient input, never saved state (**VERIFIED focused/native-X11 tests, live normal cleanup and 4.4.1 release checks**) | Reading copies only from the verified focused window, never uses stale X11 PRIMARY data and never restores an earlier clipboard value. Keep the foreground `xclip -quiet` owner through the accepted Speech Note request and one bounded second for retrieval. Normal cleanup and independent 15-second expiry explicitly clear only its verified X11 window/process before ending it, with an atomic check that preserves newer copies even if their text is identical. Owner disappearance alone lets Cinnamon restore cached text; fixtures must reproduce this and forced helper death. Every owner closes the reading lock descriptor. See the release record for failed early trials, passed checks and remaining live crash/later-copy acceptance. | Speech Note accepts text directly over a supported API without clipboard mediation. |
| Migrate known voice defaults, preserve custom policy (VERIFIED offline; live rc6 pending) | Rc5 proved that preserving every listener and pipeline field can retain a broken released default after package parity. Rc6 migrates only recognised Jarvis defaults. Unknown models, thresholds or stages stop for review. Apps, personal commands and hardware-specific microphone selection remain machine-owned. | A live rc6 test fails or a future schema marks managed fields more precisely. |
| Separate command restart from full voice restart (VERIFIED in source) | The older tray exposed both. The first Control Centre made its primary restart reload audio, listener, core, every skill and the intent container. Rc6 makes command/core restart primary and keeps full voice restart under Advanced. | OVOS gains supported single-skill hot reload or command restart becomes unsafe. |
| Fixed 0.35-second cue delay (**HISTORICAL: failed rc7 live acceptance**) | Dinkum 0.10.5a1 lowers playback before emitting its confirmation event. Rc7 delayed the 15% duck by 0.35 seconds and retained record-end plus 15-second fail-safe restoration. A measured laptop cycle proved the cue stream was still active when the sink dropped. Reference and laptop reports also proved identical static settings, versions, Audio source and ALSA PHAL source; the reference had only a dummy sink. Do not silently promote or extend the timer. | Revisit only if the audio service loses its completion response and a measured fallback is required. |
| Use cue completion, a fresh per-activation volume snapshot and configurable 20% duck (**VERIFIED locally; rc9 live pending**) | The audio service replies after instant-sound playback completes. Keep full volume and exclude confirmation audio from STT until that response, then lower background audio and accept the command. Rc8 proved that a service-start snapshot can become stale and restore the wrong level, so rc9 queries immediately before every activation and does not duck if the query fails. Retain record-end and 15-second emergency restoration, plus a three-second missing-cue fallback. The Voice page has an enable switch and 10–50% slider; migration recognises only the exact former managed default. | Live hotkey/wake tests show delayed capture, missed speech, cue leakage, failed restoration, or a different hardware-safe default. |
| Decouple cue-volume completion from microphone capture (**VERIFIED locally; rc11 live pending; supersedes the capture-gating part above**) | A live prompted-writing trace lost the beginning of a controlled sentence while the audio-service response controlled Dinkum's confirmation state. Restore the exact upstream voice loop. Use cue completion only to time background-volume ducking; retain fresh volume snapshot, record-end restore and fail-safe. | Upstream timing again admits cue audio into STT; address the cue asset/playback path without delaying microphone capture. |
| Keep message fallback exact and model-independent (**HISTORICAL: superseded before live rc11**) | The first rc11 repair added exact reviewed phrases after “message Hermes” reached unmatched feedback. It preserved safety but made natural wording unnecessarily brittle because the corresponding interaction starters were absent from Qwen's catalogue. Keep the exact phrases only as a fast path. | Retained for the failure history; do not restore exact-only routing. |
| Use native-first, semantic Qwen fallback for bounded workflows (**VERIFIED offline in rc13; live pending**) | Native intents and the exact fast path run first. If they decline, Qwen may select safe writing/dictation, reading, search, media-title, message-starter and enabled-app actions. Message actions only focus a reviewed target and begin the existing second-turn capture; Qwen never sees, generates, types or sends the dictated message. New detected apps and saved spoken names flow through the profile automatically. Delete/close, arbitrary keystrokes, shell commands and ambiguous multi-target requests remain excluded. | Live model tests produce false actions, an action bypasses focus/capture checks, or a newly added workflow needs a reviewed risk classification. |
| Reject false speech by evidence, not a command blacklist (**VERIFIED locally; live determination pending**) | `Pause music` is both a valid command and a repeated false Faster-Whisper result. Rc8 keeps cue audio outside STT and enables the plugin's supported VAD filter for the managed small.en setup; it does not blacklist the command. Silence, music and genuine short commands still require live retesting. If the false phrase persists, use no-speech/confidence metadata without retaining audio to derive a threshold. | The valid pause command regresses, the filter drops genuine short speech, or measured metadata cannot separate true and false samples. |
| Pace provider-backed searches without evasion (**owner-selected V4 candidate; live timing pending**) | Browser, visible YouTube and Media title searches share an 11-second minimum gap. This is between requests, not a delay on every command. Brief pre-submit pacing is 0.5–1 second; Media queues only the latest explicit request, acknowledges once without waiting for TTS, and waits cancellably for its slot. Stop cancels pending work. After a valid result is found, a three-second cancellable transition precedes opening, regardless of lookup duration. Browser typing remains 10 ms per character with a final 0.2-second focus-checked pause. These timings do not guarantee avoidance of provider alerts. Qwen remains the semantic fallback while clear titles use the direct helper route. Never automatically retry provider failures, rotate VPNs, bypass CAPTCHAs or simulate activity. Explicit YouTube/429 challenges remain visible. | Measured normal-use results support a different interval or provider guidance changes. |
| Default fresh setup to a recommended detected app set (**VERIFIED in source and isolated setup tests; live GUI pending**) | A fresh setup should not enable a large discovery catalogue automatically. Offer Recommended, All and Custom choices. Recommended enables only detected everyday apps plus the fixed private-agent bridge when its helpers actually exist. Detected Standard Notes maps to Notes, Proton Mail becomes the generic Mail target, Proton Calendar maps to Calendar, and a separately detected System Calendar remains available by name. Updates preserve saved policy, spoken names and personal commands; an interactive upgrade offers review, with retired `core-only` defaulting to review. The four-choice Voice-only UI is **HISTORICAL**. | A commonly expected safe app is missing, a generic mapping surprises users, or live setup shows that the curated set is confusing. |
| Keep updates separate from maintenance (**VERIFIED in source; live GUI pending**) | Version, release date, check and install form one short user task and should not be buried below diagnostics. Overview retains only a slim status summary; Updates owns release controls; Maintenance owns health, private export and support. | The navigation becomes too crowded or live use shows the split is less clear. |
| Export persistent Jarvis settings, not transient state (**VERIFIED by archive test**) | The bounded private export includes current app choices, spoken names, personal commands, shortcuts, router/update/voice settings, personas, listening cue and saved normal reading speed. It excludes the temporary 2× marker, models, code, logs, recordings and unreviewed files. This keeps the archive inspectable and avoids restoring a half-finished operation. | A reviewed merge-based import defines additional portable fields or a new persistent setting is added. |
| Keep one-shot writing literal and punctuation explicit (**VERIFIED in unit tests; live voice pending**) | “Write this” removes only Whisper's automatic final full stop and trailing whitespace, types no Enter, and never silently adds punctuation. If Whisper preserves the words, a final “period,” “full stop” or the more distinctive “insert a period” adds a period in that capture. Because STT may instead collapse ordinary spoken punctuation into indistinguishable automatic punctuation, a separate strict native “Full stop”/“Period” command inserts one literal `.` into the verified focused field without Enter or Qwen. | Whisper exposes reliable spoken-punctuation metadata, the standalone command collides in live use, or a configurable writing policy is requested. |
| Run deliberate Media title matching before Padatious (**VERIFIED offline; live rc3 pending**) | A supplied live trace showed Alerts claiming `Play I'm Walking on Sunshine` as timer status when Media ran later. Native Adapt still runs first. Place the narrow `Play {title}` Media stage next, then Padatious; leave Qwen and unmatched feedback near fallback. This corrects one evidenced collision without broadly promoting model routing. | Media claims a legitimate non-media Padatious phrase, or a future OVOS pipeline offers explicit intent priority metadata. |
| Keep prompted browser input in one verified conversation (**VERIFIED offline; live rc3 pending**) | Clearing/deactivating immediately before activation caused the address reply to fall through to DDG. Start only when no other prompt is active, record the focused browser window, activate once, consume one reply, recheck focus, type it and press Enter without confirmation. | OVOS guarantees synchronous deactivate/activate ordering, or live testing shows another handler can still steal the reply. |
| Do not add direct Standard Notes title or Proton subject navigation without a stable target (**VERIFIED design boundary for 3.6**) | Both products expose the fields, but neither reviewed integration has a documented stable direct-focus shortcut. Screen coordinates and assumed Tab counts vary with app version, editor, recipient fields and layout. Keep focused-window `Write this`, New Line and Next/Previous Field controls available instead of pretending a brittle sequence is a reliable semantic action. | Either app publishes a stable shortcut/accessibility target and it passes focused-window tests on supported versions. |
| Enable the official OVOS user target and install one desktop launcher (**VERIFIED offline for V3.2; login test pending**) | The tray alone is only a status interface. Enable the existing official `ovos.service` user target so voice services return after login, delay the combined tray briefly so its first status is meaningful, and add one **Jarvis OVOS** Start Menu shortcut that opens the existing Control Centre. Add no second daemon or listening port; backup and rollback the prior enablement and desktop files. | A supported desktop requires a different user-session startup mechanism or a live login test exposes an ordering problem. |
| Keep reading speed owned by Speech Note (**VERIFIED in source**) | Jarvis preserves the user's manually selected normal speed and makes spoken 2× temporary. A second tray/Control Centre speed control would create conflicting state, so Voice links to Speech Note instead. | Speech Note publishes a stable external settings API that can be shared without duplicate state. |
| Make complete removal explicit and component-scoped (**VERIFIED in isolated uninstall test**) | Ordinary uninstall removes only Jarvis-managed commands, plugins, helpers, tray, launchers and user units. Qwen, settings/history and the whole OVOS virtualenv each require an explicit choice. Never silently remove Speech Note or unrelated apps. | The installer gains a trustworthy ownership receipt that can safely simplify OVOS removal. |
| Keep Updates last and make healthy state prominent (**VERIFIED in source; live GUI pending**) | Overview should reassure the user with a strong green healthy banner and compact service indicators. Microphone and emergency speech controls sit side by side; active pause/stop controls use one calm blue, while re-enable uses green. Maintenance precedes the final Updates tab. | Accessibility review or live use shows inadequate contrast or grouping. |
| Exclude private machine launchers from portable discovery (**VERIFIED in source/tests**) | A public app chooser must not expose private remote-terminal launchers, Jarvis's own launcher or other project-internal helpers merely because they have desktop files. Known public integrations retain allowlisted commands. | A more precise privacy-safe desktop-entry marker replaces the conservative terminal-launcher filter. |
| Resolve generic app roles to one enabled compatible target (**VERIFIED in source/tests**) | Browser, Notes, Mail, Calendar and Office are user-facing roles, not permission to launch any desktop entry. Offer only compatible enabled choices, keep one generic alias owner, preserve the selection on update and fall back safely if an app disappears. | A new role or integration has reliable detection and an explicit compatibility mapping. |
| Include recognised Email and Office desktop entries in Recommended choices (**VERIFIED in source/tests**) | Thunderbird, ElectronMail, LibreOffice-family entries and OnlyOffice are ordinary expected defaults when installed. Dynamic entries must match a recognised family; category-only entries remain available through All or Custom. Launching still uses the reviewed desktop entry, and Qwen sees only enabled action IDs. | Add a family only after verifying its desktop identity and compatible role metadata. |
| Use Firefox only as Media's bounded browser fallback (**VERIFIED in source/tests**) | Keep enabled Brave as the first YouTube playback browser to preserve the reviewed workflow. If its launcher is unavailable or fails, try enabled Firefox through the same application registry. Do not fall back to an arbitrary system command or browser. | The user selects a different reviewed Media browser or the browser registry gains a safe generic URL capability. |
| Pin CI actions and prefer immutable releases (**VERIFIED for CI; repository release setting remains owner-controlled**) | Full commit SHAs prevent an action tag moving after review. Release checksums catch corruption but not publisher compromise; GitHub release immutability and provenance strengthen future publication without changing Jarvis runtime discovery or Qwen. | GitHub changes its provenance model or a separately protected signing workflow is adopted. |
| Describe settings export as a private backup (**VERIFIED**) | The allowlist bounds files and excludes models, code, logs and recordings, but reviewed OVOS configuration may contain credentials. Do not call this privacy-filtered or portable until a redaction policy and merge-based import are implemented and tested. | A separate redacted export/import format is approved. |
| Keep one active wake phrase; do not pretend free text is a trained model (**VERIFIED design boundary for 3.7**) | OVOS can host multiple engines, but OpenWakeWord recognises trained models rather than arbitrary phrases. Retain the tested Hey Jarvis model and the existing single custom local-Vosk replacement. Do not add a multiple-wake GUI until each offered model is real and independently validated. | Multiple independently load-tested models have acceptable false-positive and latency results on supported hardware. |
| Treat generic music as a bounded two-turn request (**VERIFIED in source/tests; live pending**) | “Play music” asks what to play and sends one bounded reply as title data to the separate Media skill. Direct `Play {title}` stays fast. Exact `lay` and `pose`/`poze music` variants address observed STT/accent errors without fuzzy media execution or bare-word collisions. | Live recognition shows harmful collisions or a stable structured Media search API replaces the title event. |
| Relaunch the Control Centre after its own update (**VERIFIED in source/tests; live pending**) | The updater can replace GUI code while the old Python process remains loaded. After a successful transaction, a fixed user-space helper waits for the old PID to exit and starts the installed launcher once; failed updates do not relaunch. | GTK gains a supported in-process code reload or the desktop application lifecycle changes. |
| Make Control Centre update cancellation explicit and bounded (**VERIFIED in source/tests; live pending**) | The Updates page exposes **Stop update** only while its exact fixed update process is active. Closing the GUI at that time asks before sending `SIGTERM` to the update process group, escalates to `SIGKILL` only after five seconds, and restores the page state. This is recovery for a stuck GUI operation, not permission to kill unrelated installers. | The updater gains a transactional cancellation API or live testing finds a phase that must not be interrupted. |
| Keep browser music control on MPRIS (**VERIFIED in source; external idle limit accepted**) | Jarvis controls the media session Brave exposes through `playerctl`; it does not guess tabs, inject webpage clicks or bypass YouTube inactivity prompts. Play reports when no compatible session exists. Bring the tab forward or choose a new song if the session disappears. No Brave performance-setting guarantee is assumed. | Brave exposes a safer persistent-session API. |

| Block generic input in terminal windows (**VERIFIED in V4 offline failure tests; live pending**) | Text editing, generic writing, Enter and soft line breaks use one terminal-identity test. Refuse input before typing, including modern terminal classes. Recheck window identity before typing and submission. Opening an allowlisted Terminal application does not authorise input to it. | A separately designed, explicitly approved terminal mode has a stronger execution boundary. |
| Confirm tool-capable private agent prompts (**VERIFIED in V4 offline tests; live pending**) | Capture and read back the message; require exactly `send it`; cancellation, timeout or native-command escape clears it. Confirmation is single-use and uses the fixed private helper. Ordinary desktop messaging is preserved; actual desktop tool permissions remain a live review gate. | A desktop agent gains tools or private helper permissions change. |
| Separate version pins, hashes and isolation claims (**VERIFIED policy; production gates open**) | A resolver hash lock is a candidate, not proof of laptop parity or reproducible source builds. Preserve the actual capture and record each proposed change. A verified wheel closure must account for extras, reject all conflicts and pass isolated/live tests. The historical NumPy exemption is superseded by the separately versioned ONNX-only plugin while retaining NumPy 2. Loopback model use is not egress enforcement. Unresolved full-hash or core-isolation gates require an owner decision before release. | The owner explicitly revises release scope after reviewing evidence. |
| Keep all Jarvis and upstream-bootstrap staging user-owned (**VERIFIED in source/tests**) | Earlier copied launchers retained deleted staging paths, and a root `/var/tmp` bootstrap broadened the privilege boundary. Stage under private Jarvis state, relocate and validate launchers before switching, and let only explicit upstream/system-package steps request administrator access. | The supported upstream installer publishes a narrower noninteractive system-package API. |
| Separate login auto-start from current run state (**VERIFIED in isolated V4 tests; next-login acceptance pending**) | Auto-start controls only enablement of the existing OVOS user target and quiet tray launcher. Run/Stop controls this session. Preserve the private saved preference, including unknown fields, across upgrades; restore prior enablement/files after failure. Never unmask services, launch the Control Centre on login or silently override an explicit off choice. | A real login shows the reviewed user target cannot provide reliable session startup. |

## V4 isolation and recovered runtime decisions

These retain their original candidate evidence. The stable scope decision below
supersedes earlier publication gates without relabelling unverified tests.

- **VERIFIED privacy boundary:** public runtime manifests describe the reviewed
  installer package policy and its wheel hashes. Keep original laptop captures,
  observed model digests, source-install indicators and private diagnostic
  snapshots outside Git and release archives. Full dependency hash enforcement
  does not authorise publishing a client's diagnostic inventory.

- **VERIFIED policy; live acceptance open:** use five fixed system-manager
  services with ordinary-user workers after the supplied temporary-policy
  experiment. Grant only their exact account/service names and start/stop/restart
  verbs. Prepare administrator-owned service data; never execute repository
  Python, pip or a generated script as root. Keep Weather/Media separate and
  desktop handoffs in the existing user-session launcher.
- **VERIFIED in isolated recovery tests:** activation requires stopped services,
  reviewed native data, current source identities and complete runtime provenance.
  Removal remains possible if worker source is damaged. Install/update/rollback/
  uninstall refuse remaining owned native policy until it is safely removed.
  Settings, models, login choice and deliberate mute stay preserved.
- **VERIFIED policy:** a temporary filtering pass, installation receipt or unit
  property is insufficient for an isolation badge. Require actual OVOS and Ollama
  socket/application evidence, including DNS/proxy/inherited-socket paths. The
  existing local bus and same-user session are trusted, not hostile-user isolation.
- **VERIFIED policy:** default staged installation uses the separately verified
  full runtime bundle with no resolver/source fallback. Explicit source-build
  experiments do not satisfy the full-hash gate. Retain NumPy 2.4.6, the documented
  ONNX-only downstream wake plugin and zero dependency exemptions.
- **VERIFIED candidate policy adoption:** adopt only the exact runtime lock,
  artifact manifest and bundle policy whose archive bytes and complete offline
  installation pass. The latest rebuild keeps all 296 versions and dependency
  metadata unchanged; nine source-built wheel hash changes remain explicit.
  Retain this tested archive without rebuilding. Candidate adoption is separate
  from stable release, bundled-source obligations and live laptop acceptance.
- **VERIFIED recovery limitation:** missing artifacts and source fingerprints
  cannot be reconstructed from a previous checksum. Preserve historical reports,
  identify new collectors separately and revalidate reconstructed source/artifacts.
  Publication remains conditional on the full agreed V4 acceptance.

## Historical owner-authorised V4 laptop test, 30 September 2026

- **VERIFIED owner requirement; implemented source candidate:** General has
  separate tray-minimised and voice-service login options. Dashboard keeps
  current Run/Stop. Preserve the legacy combined preference and all unknown
  fields; new independent choices survive updates and failed writes recover
  both launchers and service enablement. A dedicated quiet voice-login entry
  supports service startup without showing the tray. Neither preference change
  changes current listening/running state. Future candidate review files go
  directly to private Downloads directories; operational receipts remain state.

- **VERIFIED owner requirement:** routine updates remain password-free. An
  unreadable polkit directory alone must not introduce sudo; require complete
  ordinary-user system-manager evidence that all five fixed native workers are
  absent/inactive, with other native deployment paths/receipts absent. Do not
  assert a hidden rule was inspected or removed. Existing/loaded workers,
  visible policy and uncertain checks remain blocked. Administrator access is
  reserved for explicitly reviewed native isolation setup/removal or missing
  operating-system prerequisites.

- **VERIFIED owner decision:** publish 4.0.0rc1 as a laptop-testing prerelease
  with the exact retained full-hash runtime and independently versioned plugins.
  Keep the stable channel on 3.9.0 and record unverified live acceptance openly.
- **VERIFIED owner decision:** production signing can wait until deployment
  beyond the current client. Byte checksums do not authenticate a publisher.
- **VERIFIED owner decision:** response speed as in 3.9 is accepted; GPU tuning
  is unnecessary for this release. Brave session expiry remains accepted, with
  tab reopening or a new song as recovery.
- **VERIFIED installer scope:** install Jarvis/OVOS dependencies and local models;
  require existing Ollama. Do not install Hermes, Claude, Codex or another agent
  platform. Keep Speech Note installation optional with explicit approval.
- **VERIFIED reporting constraint:** automated reading/writing and clipboard
  checks are separate from acoustic transcript accuracy; preserve writing and
  offer the distinct speak-selected/highlighted alternatives. Test on the laptop.

**HISTORICAL:** the original 2.3.1 fresh-install pins still describe the
previously reviewed baseline. They do not describe the reference system's upgraded media
and alpha voice stack. The broader five-reviewer model design belongs outside
this desktop-control release until there is an actual integration requirement.

## Stable V4 scope decision, 1 October 2026

- **VERIFIED owner direction:** publish the working V4 implementation as 4.0.0
  for the controlled small-client deployment. Reuse existing passing behaviour
  checks, scan/verify the final release assets and request no further laptop
  tests. See [release record](releases.md) for the exact accepted limits.
- **VERIFIED exercised music acceptance:** retain immediate acknowledgement and
  a cancellable three-second post-result transition. Existing tabs are not
  forcibly stopped; overlapping playback is an accepted follow-up. No timing
  value guarantees avoiding provider challenges. Longer `Put on {title}` wording
  remains available without changing recognition policy.
- **VERIFIED weather observation:** new-city search/reverse takes roughly 13
  seconds, forecast roughly two; repeated locations skip the city lookup.
  These durations include wrapper/network/provider work. Leave the provider,
  deadlines and isolation policy unchanged for V4.
- **PLANNED broader assurance:** real-model/acoustic coverage, all desktop/login
  variants, mediated/inherited socket and native recovery checks, effective
  Hermes permissions and maintainer account protections retain their unverified
  status. Stable publication is not a claim those checks passed. Production
  signatures and fresh-OS/model offline packaging remain deferred.

## Stable V4 documentation maintenance

- **VERIFIED owner direction:** keep README structure and style; refresh current
  command and plugin guides from source. Keep public release notes in the short
  V3 format and retain detailed V4 trials under `docs/history/`.
- **VERIFIED release-list cleanup:** stable V4 is the only published V4 release.
  RC1/RC2 remain drafts with their assets intact; keep tags and Git history.
  Stable downloads are not rebuilt for documentation maintenance.
- **VERIFIED owner report:** the full stable laptop installation completed.
  This report is not a new network or recovery acceptance test. Restored core
  activation and readiness require their own result after the upgrade.
- **PLANNED in published 4.0.0; implemented in the candidate below:** guided
  upgrades across the optional native isolation boundary.
  The current updater must retain its refusal while native data remains;
  manual owner-terminal removal and restoration must be exact and reviewed.

## Guided isolation and dedicated model, 1 October 2026

- **VERIFIED owner direction, automated tests and supplied live migration/recovery:** new installs
  offer network isolation selected by default, briefly explaining administrator
  approval. Existing installs keep their actual isolation choice and unknown
  settings. Declining isolation retains the existing ordinary-user model path.
- The selected isolated path uses a dedicated ordinary-user Ollama service,
  fixed to `127.0.0.1:11435`, a private model directory and disabled cloud features.
  Kernel IP restrictions apply to it and the voice workers. This explicitly
  supersedes the earlier no-additional-local-port constraint for this one endpoint.
  General Ollama, including any previously applied policy, is left unchanged.
  There is no fallback from the dedicated instance to general Ollama.
- Prepare the reviewed Qwen model before restricting it; verify local manifest
  and blob digests and copy only that model without hardlinks or source deletion.
  Reuse the trusted installed Ollama executable; do not install another platform.
- Upgrades keep native policy and compatibility relays installed while replacing
  managed code. An exact process-bound journal authorises only installation and
  recovery. Preserve running/muted state, restore previous source/policy on failure
  and keep workers blocked when recovery cannot finish. Never quietly downgrade.
- Administrator operations remain bounded native file/service commands. The
  exact account grant expands to its five workers and dedicated model unit,
  start/stop/restart only. Routine upgrades require no new authentication when
  native data is unchanged. Same-user and loopback mediation remain trusted.
- Private settings exports retain the saved choice, not native policies or
  recovery journals. After reviewed native removal, explicit model deletion
  targets only the verified private copy when selected; general Ollama stays
  intact. Unreviewed private data blocks deletion. See the [release evidence](releases.md).

## Stable 4.0.1 release scope, 1 October 2026

- **VERIFIED explicit owner approval:** finalise and release 4.0.1 after supplied
  successful interrupted recovery, legacy migration and voice/model readiness.
  The owner accepts the dedicated daemon's actual generation and IPv4/IPv6
  egress checks after release. Those checks were unverified at publication;
  subsequent supplied live reports close the tested generation/direct-network
  gates as recorded in the [release ledger](releases.md). Never present inventory
  or service properties alone as live network enforcement. Fresh-install coverage
  and the existing scoped V4 limitations remain unverified.
- Preserve the tested production code and dependency closure. Finalise short
  public release notes, exact archive/wheel payload and checksum verification,
  with resolved investigations retained in history.
