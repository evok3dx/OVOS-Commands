# V3 release and known limits

Version **3.0.0** bundles the Brain-derived Jarvis changes and the two
separate plugins. The owner has confirmed that Media and File Search work.
See [Releases](https://github.com/evok3dx/OVOS-Commands/releases/latest) for
the published archive and checksum. Other live checks remain open below.
The [living audit](v2.4-audit.md) records the open issues and the
[final source reconciliation](v3-final-audit.md) records what was compared.

| Feature | Verified in source or Brain | Still to verify |
|---|---|---|
| Single tray and Control Centre | **VERIFIED on Brain:** one enabled autostart entry and one status icon showing service, update and microphone state. The former mic indicator autostart is disabled. V3's installer retires that legacy entry after backup. | Visual check after a V3 upgrade and rollback. |
| Local Qwen | **VERIFIED on Brain:** reviewed `qwen3:4b-instruct-2507-q4_K_M` model and successful app actions. V3 registers two local pipelines and adds the Media pipeline before the command router. Installer reuses an installed model, otherwise asks to download it before changing Jarvis. Existing model choices and OVOS packages are preserved. | Command → question → command, cancellation, focus guard and latency on the older i7. Ollama must already be installed and running. |
| Whisper `small.en` hints | **VERIFIED on Brain:** active listener reported 21 names and 61 tokens. The bundled helper now matches Brain's installed app-name and short media/writing cues. The V3 installer checks exact supported Faster-Whisper source and uses a separate backup; an unfamiliar revision is left untouched and reported. | Live recognition after V3 on both computers; monitor the previous quiet-room false media transcription without assuming its cause. |
| Media and file search | **VERIFIED in source and reported working by the owner:** Media opens the first YouTube result and controls an active player; File Search 0.2.0 offers 45 native filename patterns, read-only results and bounded Qwen routing. The Commands GUI shows installed patterns for both. | The final Brain snapshot predates these plugin updates; repeat checks on other computers before assuming the same behavior there. |
| Writing and interruption | **VERIFIED in candidate code and isolated test:** New Line, Brain's installed Speech Note 2× helper with speed restoration, Speech Note barge-in, media stop and a quiet no-player response. The initial candidate had the spoken 2× intent but omitted the newer installed reading helper; that gap is fixed locally. | Spoken 2× and normal speed, stop and interruption with actual listener and desktop windows. |
| Installer and recovery | **VERIFIED in isolated tests:** backup, fresh install, upgrade preservation, failure recovery and rollback. V3 bundles the two plugin source packages and retains host configuration and private helpers. | Live host checks and a GUI-initiated published update. |

A fresh install keeps the separately reviewed OVOS voice baseline. The Brain's
manually tested alpha stack is recognised and preserved on upgrade, not installed
on every machine. A new computer also needs Ollama installed and running before
the required Qwen model can be downloaded. V3 does not install an unfamiliar
third-party speech-plugin revision or silently replace voice packages.

The historical Vosk `time_between_checks` change from `0.2` to `1.0` was an
intermittent experiment. The Brain later used an explicitly validated
OpenWakeWord ONNX model at threshold `0.4`; it is not a universal V3 default.

**Still open:** check complete V3 voice behavior and installation/rollback on
Brain and laptop, model response time on the i7, and a GUI-initiated update.
The older OCP/NPR unsolicited `skill.error` is unresolved; working Media and
File Search plugins do not establish a fix for that separate OVOS path.
Treat these as known limits when installing V3, not as passed tests.

Details: [installer and rollback](07-installer-updates.md),
[local routing](04-local-routing.md), [OVOS voice](06-ovos-voice.md),
[media and file search](10-media-files.md), and
[previous draft](history/v3-draft-before-final-snapshot.md).
