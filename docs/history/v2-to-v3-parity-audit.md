# V2-to-V3 behavior parity audit · HISTORICAL

This is the line-by-line continuity record requested after live laptop testing
exposed behavior that file and inventory counts did not catch.

## Evidence and status

| Evidence | Role | Status |
|---|---|---|
| Git tag `v2.3.1` | Last published 2.x baseline | **VERIFIED** |
| Commit `072d9d0` and the refactor history leading to 2.3.1 | Earlier working behavior that may have been lost before the tag | **UNDER REVIEW** |
| Privacy-filtered reference archive from 24 September | Installed stack/source evidence, excluding raw private configuration | **VERIFIED WITH LIMITS** |
| Current 3.1.1 candidate and tests | Proposed implementation | **UNDER REVIEW** |
| Laptop and reference voice logs | End-to-end behavior | **AUTHORITATIVE FOR THE TESTED PATH** |

`v2.4` was the improvement-programme name. There is no `v2.4` release tag; the
last published 2.x release is `v2.3.1`.

## Why the previous continuity result was insufficient

The earlier comparison established that no published 2.3.1 action ID, intent
ID, application integration, alias or packaged helper disappeared. That result
remains useful, but it measured inventory rather than outcomes. A handler can
still be present while its timing, external setting, event order or called API
changes behavior.

Every parity item now needs both:

1. a source/configuration mapping; and
2. an outcome test at the real boundary it controls.

## Confirmed dictation finding

| Layer | 2.x/reference behavior | Current finding | Required gate |
|---|---|---|---|
| Jarvis event hook | Wake word and record-begin call the Speech Note interruption handler. | The hook remains present. Presence alone previously produced a false pass. | Verify the stop action is accepted before further dictation text is inserted. |
| Speech Note rule | A manually configured STT rule replaces `Hey Jarvis` with a space. | This machine-specific rule was excluded from the privacy-filtered archive and was not recreated by setup. | Preserve all existing rules and add or guide one exact Jarvis rule without replacing the list. |
| OVOS command capture | A later capture can still hallucinate `Pause music`. | Separate from wake-phrase removal. | Empty/noisy capture must not execute an action; a real `pause music` command must remain available. |

Speech Note 4.7 and later officially provide sequential text-transformation
Rules. The reviewed public D-Bus API exposes actions, task state and models but
does not expose rule creation or editing. Speech Note stores rules as a Qt
`QVariantList` in `settings.conf`. Jarvis must not manufacture or replace that
opaque value with a shell edit. Safe automation requires either an upstream
rule API or a tested Qt-native merge. The current setup therefore opens Speech
Note and shows the exact non-destructive GUI step: retain every existing rule,
enable Rules, and add one case-insensitive STT regular-expression replacement
covering `Hey Jarvis`, `Hey, Jarvis` and the optional final full stop. The
published V2 source contained no punctuation-removal rule; that behaviour was
an external Speech Note setting.

## Published 2.3.1 inventory result

- All 86 base action IDs remain represented.
- All 90 intent IDs remain represented.
- Every published application integration and alias remains represented.
- All 16 packaged runtime helpers remain represented; V3 adds one helper.
- The legacy machine-specific profile was renamed to `profiles/reference.json`; it was not
  deleted functionally.
- The old separate microphone tray was intentionally folded into the combined
  tray. Its upgrade/rollback artifacts remain available.

These statements are **VERIFIED inventory facts**, not blanket claims of live
behavioral parity.

## Historical behavior requiring explicit review

The pre-2.2 working checkpoint registered a second wake handler that emitted
`mycroft.audio.speech.stop` immediately. It was removed when 2.2 replaced that
registration with a common `record_begin` Speech Note interruption path. It was
already absent from published 2.3.1, so a tag-only comparison could not flag
it. This is **HISTORICAL**, not automatically approved for restoration: current
OVOS owns normal barge-in, and a duplicate speech-stop event could have side
effects. Retest the outcome before deciding.

## Remaining review matrix

- [ ] Diff every changed dispatcher method for changed side effects, feedback,
  focus checks, timeout behavior and external API calls.
- [ ] Compare every 2.3.1 vocabulary phrase and collision rule with the current
  native and Qwen paths.
- [ ] Compare every helper's arguments, exit codes, state files, permissions
  and rollback behavior.
- [ ] Compare installer preservation boundaries for application selection,
  personal commands, aliases, shortcuts, models, private helpers and Speech
  Note settings.
- [ ] Compare old tray actions with the combined tray and Control Centre.
- [ ] Exercise continuous dictation start, wake interruption, pause, resume and
  stop; confirm the wake phrase is absent from the document.
- [ ] Exercise writing, messaging, search, reading 1x/2x restoration, media,
  volume, wake/hotkey, Qwen and unmatched feedback on the laptop.
- [ ] Classify every difference as **VERIFIED**, **PLANNED** or **HISTORICAL**;
  do not silently infer intent.

No 3.1.1 release is ready until this matrix and the live acceptance matrix in
[`v3.1.1-checklist.md`](v3.1.1-checklist.md) are both closed.
