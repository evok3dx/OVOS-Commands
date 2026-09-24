# Historical V3 draft before final Brain snapshot

**HISTORICAL:** This plan predates the final Brain archive and the two packaged
plugins. It contains superseded claims, including that Qwen and Whisper hints
would remain optional and file search was out of scope. See the current
[V3 status](../v3-update.md) and [living audit](../v2.4-audit.md).

**Status: local `3.0.0rc1` candidate, not a published release.** Use the
[published releases](https://github.com/evok3dx/OVOS-Commands/releases)
for an install today. This page describes the intended
upgrade on an existing Jarvis workstation. **Candidate** means the source is
present locally; **Brain verified** means it worked on the Brain before this
combined release; **Pending** means the complete V3 update has not passed on
both machines. See the [living audit](../v2.4-audit.md) for the problems, their
solutions and release gates.

## What V3 brings together

| Area | Intended behaviour | Current evidence and limit |
|---|---|---|
| Control Centre | One tray icon combines service, microphone and update status. A native window groups applications, commands, voice, settings export and maintenance. | **Candidate:** source and isolated GUI update handoff test. Confirm the real tray and an approved update on each desktop. The updater sees published stable releases, not draft pull requests. |
| Local Qwen instruct | Optional `qwen3:4b-instruct-2507-q4_K_M` via the existing local Ollama service. A setup check verifies the exact model and both OVOS routing stages before enabling it. | **Brain verified:** app commands routed to reviewed actions. **Candidate:** setup is explicit; it does not install Ollama, download a model or overwrite a different configured model. Jarvis also works without Qwen. |
| Qwen speed and safety | Compact action IDs and prompts, requested model residency, and a catalog limited to enabled apps and approved actions. No model-generated shell command. | **Brain verified:** median correct-action response in a small paired Ultra 9 sample improved from 3.25 to 1.46 seconds. **Pending on the older 16 GB i7:** real response and eight-second timeout check; no claim of matching speed. |
| Whisper recognition | Optional reviewed `small.en` prompt hints from enabled app names and saved spoken names; no retraining or model replacement. | **Brain verified:** seven reported voice checks; patch has 16 offline tests. **Candidate:** patch checks the installed `ovos-stt-plugin-fasterwhisper 0.4.0` source first and refuses an unknown revision. It is not applied silently by the main installer. |
| Applications and daily use | Installed-app discovery, controlled launching and selection, personal commands, focused-window checks, writing readiness cue, and existing special app helpers. | **Candidate plus separate Brain checks.** Mere detection does not grant Qwen permission to open every discovered app. Test the combined routing order, writing and reading on both machines. |
| Updates and recovery | Replace release-managed Jarvis files after backup; retain rollback and a separate settings export. Preserve OVOS configuration, apps, personal commands, hotkey, sound, models, voice packages and unlisted private Brain helpers. | **Candidate:** isolated install, preservation and rollback checks. An exported settings archive may include secrets; it is not yet an automated merge import or a full-system backup. |
| OVOS voice | Recognise Brain's tested alpha versions while retaining its installed speech stack; keep the previously reviewed fresh-install pins separately. | **Candidate:** doctor recognises alpha versions. It does not upgrade the laptop or install Brain's alpha stack on a fresh PC. Brain's explicit OpenWakeWord ONNX setup must be preserved and separately tested for any new install. |
| YouTube and media | Include the finished, tested Brave/YouTube work and its safe integration with existing commands. | **Pending:** browser work is still being completed. A working search result is not proof that audio played. OCP/Common Play and VLC require a separate decision after their remaining error is understood; this draft does not assume they can be removed. |

## Brain changes the candidate must still absorb

The verified Brain source snapshot exposed four differences that would regress
if this candidate simply replaced the working installation:

1. Keep the wake detector listening during Speech Note reading and serialise
   wake-word/hotkey D-Bus cancellation, so spoken interruption still works.
2. Send `ovos.common_play.stop` with spoken Stop to halt active media.
3. Bring across double-speed selected-text/page reading phrases and handlers.
4. Keep the quiet response when no media player is available, and use the
   functional Bella unknown-word check rather than a source-text check.

These are **Pending in the combined candidate**. The source comparison and
historical fixes are recorded in the [living audit](../v2.4-audit.md) and
[voice/media record](../06-ovos-voice.md). Machine-specific commands and private
helpers remain outside release-managed paths.

## Wake-word history: the `0.2 → 1.0` trial

That change adjusted Vosk's `time_between_checks` in seconds, not microphone
volume. It triggered three times and later became intermittent. Brain then used
an explicitly validated OpenWakeWord ONNX model with a `0.4` threshold and
confirmed wake activation. This is **historical troubleshooting**, not a V3
default: the candidate's custom Vosk phrase setup still uses `0.2`; its normal
install does not provision the Brain's ONNX model. Existing Brain configuration
and model files must survive the upgrade. A new-machine wake setup needs its
own compatibility and checksum check before claiming the same result.

## Release checks

- Finish the Brave/YouTube work, reconcile Brain's newer source, and check that
  no personal or voice setup is overwritten.
- Resolve or explicitly gate the repeated unsolicited Common Play
  `skill.error`. The available log shows rejected NPR playback requests, but
  does not identify what requested them.
- Pass fresh install, existing-machine upgrade, failure recovery and rollback;
  then try wake phrase, interruption, Stop, Bella, Whisper, Qwen
  command/question/command, writing, tray and GUI update on both target PCs.
- Publish V3 only after reviewing the complete result together. The draft
  branch and this page are not a release or a request to install it yet.

Technical detail lives in [installer and updates](../07-installer-updates.md),
[local Qwen routing](../04-local-routing.md),
[Whisper app-name patch](../../extras/whisper-hints/README.md), and
[settings export](../09-backup-export.md).
