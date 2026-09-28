# V3.6 release development record · HISTORICAL

**Current status: 3.6.0 is built and validated locally, but is not yet pushed,
tagged or published.** It includes the two separate Media and File Search plugins, the
reviewed OVOS package baseline, one combined tray and Control Centre, local
Qwen routing, dynamic Whisper hints, Speech Note integration, transactional
installation and rollback. The [living audit](v2.4-audit.md) is the current
evidence record. The [V3.0 source reconciliation](v3-final-audit.md) is retained
as a historical baseline rather than presented as current acceptance.

| Feature | Current evidence | Remaining release check |
|---|---|---|
| Combined tray and Control Centre | **VERIFIED in source and isolated tests:** one tray, Overview health, Apps/Defaults/Commands/Voice/Maintenance/Updates, guarded update and uninstall paths. | Live visual check of status, icons, app selection, update refresh and tray recreation after closing it. |
| Local Qwen | **VERIFIED in source and laptop diagnostic:** model remains bounded to request-specific actions. The compact prompt distinguishes polite action requests from genuine questions. The seven-case diagnostic had no eight-second timeout, zero model-load time and a 2.66-second warm median. A title is accepted only after Qwen selects the bounded Media action. | The complete 340-case real-model benchmark and older 16 GB i7 test remain useful post-release evidence. |
| Whisper `small.en` hints | **VERIFIED in installed reference evidence and source checks:** dynamic enabled-app names are forwarded only when the supported plugin source is recognised. | Continue observing live app-name recognition and quiet-room false transcriptions. |
| Media and file search | **VERIFIED in source, isolated tests and prior owner testing:** Media 0.2.0 uses enabled Brave with enabled Firefox as its bounded fallback; deliberate title requests run before Padatious, and model-approved title-only wording remains bounded. File Search 0.3.0 performs bounded filename/metadata search and asks a local follow-up when a bare files/documents request has no query. | Retest provider behavior and live voice dispatch on the final candidate. |
| Writing and reading | **VERIFIED offline:** literal one-shot writing, strict Full Stop/Period insertion, a distinctive same-capture “insert a period” cue, New Line, temporary 2× reading and exact speed restoration. Rc3 distinguishes an already-running read request from an actual Speech Note startup failure. | Speak each path on the laptop, including standalone punctuation, the distinctive same-capture cue and a manually selected Speech Note speed. |
| Installer, preservation and recovery | **VERIFIED in deployment tests:** clean staged OVOS, custom app/command/settings preservation, rollback, export and component-scoped uninstall. | Final live update, rollback preview and login/autostart check. |

A fresh installation stages the complete reviewed OVOS package set rather than
copying an old virtual environment. Existing configuration, models, saved apps,
personal commands, shortcuts and private helpers remain machine-owned and are
preserved. Ollama must already be installed and running; setup asks before
downloading the reviewed Qwen model. An unfamiliar speech-plugin revision is
left untouched instead of being patched speculatively.

The historical Vosk `time_between_checks` change from `0.2` to `1.0` was an
intermittent experiment. The reference system later used an explicitly validated
OpenWakeWord ONNX model at threshold `0.4`; it is not a universal V3 default.

**Post-release checks:** complete the 340-case Qwen run and older i7 timing
comparison, continue quiet-room Whisper observation, and exercise the published
GUI update path when a later version exists. The older unrelated OCP/NPR
`skill.error` remains historical unresolved evidence; working Media and File
Search plugins do not establish a fix for that separate OVOS path.

Details: [installer and rollback](../07-installer-updates.md),
[local routing](../04-local-routing.md), [OVOS voice](../06-ovos-voice.md),
[media and file search](../10-media-files.md), and
[previous draft](v3-draft-before-final-snapshot.md).
