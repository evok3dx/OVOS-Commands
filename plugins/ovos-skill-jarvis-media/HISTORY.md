# Jarvis Media plugin history

**HISTORICAL:** this records the separate plugin experiments and their
recovery steps. Jarvis V3 bundles the reviewed skill source and uses its main
installer; the commands for earlier standalone installers below are archival.

This document records how the Jarvis Media plugin evolved, what failed, how the
failures were diagnosed and which lessons must be retained in future releases.

## Objective

The original goal was simple: say a title naturally, open the first result in
the user's existing Brave browser, then control playback with ordinary phrases
such as pause, resume, next and previous. The solution also had to preserve the
existing Jarvis security model, application selection, Qwen fallback, Whisper
STT, Bella voice and rollback behaviour.

## 1. The initial OVOS media route

The first approach used the standard OVOS Common Play architecture:

- OCP intent routing;
- YouTube and YouTube Music providers;
- stream extraction through `yt-dlp`;
- VLC or another playback backend;
- optional experimental `ovos-media` service.

The Brain was moved to a coherent OVOS alpha stack and the media providers were
tested. The standalone `ovos-media` service was also trialled and rolled back.
It remained pre-release and introduced unnecessary queue and control complexity
for this personal assistant.

OCP produced several practical problems:

- provider searches sometimes exceeded their deadline;
- News could score unrelated music requests;
- YouTube extraction could be blocked by Google's bot challenge;
- VLC errors obscured the original extraction failure;
- browser sessions and OCP playback did not hand control to each other cleanly;
- unsolicited `skill.error` speech made failures disruptive.

One YouTube Music request played successfully, proving the stack could work,
but the route was not predictably simple or reliable.

## 2. Brave-first playback decision

The design was simplified:

1. Recognise `play <title>`, `put on <title>` or `listen to <title>`.
2. Ask `yt-dlp` only for the first flat YouTube search result.
3. Validate the returned video ID.
4. Build a fixed `youtube.com/watch` URL.
5. Open it in the user's existing Brave session.

This removed OCP provider ranking, stream extraction, VLC hand-off and Google
cookie handling from the active path. Brave handles normal website playback and
its own ad blocking. OCP was disabled in configuration but not uninstalled, so
rollback remained possible.

## 3. First standalone skill failure

The first browser-media package published an `opm.skill` entry point pointing to
a legacy `create_skill()` factory. The current OVOS Workshop loader called the
entry-point object with `bus` and `skill_id`, causing:

```text
create_skill() got an unexpected keyword argument 'bus'
```

The transaction recovery worked and restored the previous system.

### Solution

The entry point was changed to expose the skill class directly. The optional
legacy factory was retained with compatible `bus` and `skill_id` parameters.
Future installers must build the wheel, inspect its actual entry-point metadata,
load each entry point and confirm that it resolves to the object type expected
by the installed OVOS loader.

## 4. The skill loaded but did not receive play requests

The next version loaded and reported ready, yet exact requests such as
`Play Get Lucky by Daft Punk` still reached Qwen. The original implementation
used dynamically registered Adapt regex entities for the arbitrary title.
Those entities did not produce a selectable intent on the live upgraded stack.

The log established an important distinction:

- Whisper produced the intended sentence correctly.
- The skill was loaded.
- The request still matched `jarvis-qwen-pipeline`.

This was a routing failure, not an STT, search or browser failure.

### Interim solution

A narrowly anchored fallback handler claimed deliberate title requests before
Qwen and returned false for everything else. Later, the browser media logic was
integrated directly into the dispatcher and its Qwen pipeline so the routing
order was explicit and testable.

## 5. Wrong Brave installation and profile

One version opened a different Brave installation. It appeared in light mode
under another profile instead of using the already-running Flatpak Brave.

### Root cause

The media code independently searched for a Brave executable. On a system with
both native and Flatpak candidates, that logic could select a different browser
from the application chosen in Jarvis.

### Solution

Media playback now uses the same application registry and launcher as ordinary
Jarvis app commands. Flatpak Brave remains Flatpak Brave; native Brave is used
only when it is the selected or available integration. The plugin no longer
maintains a competing browser-discovery policy.

## 6. Media transport and dynamic MPRIS names

Pause worked through `playerctl`, but the browser exposed a generated player
name such as `brave.instance2`. Hard-coding that name would fail after browser
or session changes.

### Solution

The media backend enumerates MPRIS players at runtime, validates their names and
prefers the active Brave or Chromium instance. If Brave is absent, generic
MPRIS control remains available for VLC and other compatible players.

## 7. Wider commands, Qwen and Whisper

The deterministic Media vocabulary was expanded across:

- play, resume, continue and unpause;
- pause and hold;
- stop;
- next and skip;
- previous and back;
- music, media, song, track and video alternatives.

Bare words such as `stop`, `next` and `back` were deliberately excluded because
they collide with global stop, ordinary conversation and navigation.

The Commands GUI derives its Media group from the registered action vocabulary,
so the phrase list is not duplicated in a second interface.

Restricted Qwen was retained as an optional fallback for unfamiliar wording.
It may select only approved action IDs and cannot invent or execute commands.
The installation works without Qwen.

The existing dynamic Faster-Whisper helper received the short hint:

```text
Pause music. Next track. Previous track. Resume playback.
```

Observed `pose music` and `hose the music` transcriptions were also handled by
narrow deterministic phrases and Qwen examples. Whisper hints remain optional;
the plugin does not patch an unknown third-party STT installation.

## 8. Installer test output looked like a real failure

The media optimisation installer initially printed its internal transaction
tests. Those tests deliberately simulated failed live checks and rollbacks, so
the user saw temporary backup paths, an automatic failure report and restoration
messages before the real installation began.

The installation itself succeeded, but the output was unnecessarily alarming.

### Solution

Successful internal test output is now suppressed. A real test failure still
includes its captured diagnostic output. User-facing installation output shows
only the actual transaction.

## 9. Song titles containing negation words

`Play Don't Push Me by 50 Cent` repeatedly fell through to Qwen, even when
Whisper produced the exact title. Media revision 2 rejected any utterance
containing `don't`, `do not`, `never` or `not`, regardless of where the word
appeared.

That blocked dangerous or unwanted requests correctly:

```text
Don't play Get Lucky
```

But it also blocked legitimate titles:

```text
Play Don't Push Me by 50 Cent
Play Not Afraid by Eminem
Play Never Gonna Give You Up
Play Do Not Disturb
```

### Solution: Media revision 3

Negation is now evaluated according to its relationship to the operation. A
negation before `play`, `put on` or `listen to` rejects the request. Words after
an affirmative command verb are title text. The parser also accepts the comma
boundary observed in the real transcription:

```text
Play , do not push me by 50 cents
```

Compound requests such as `Play Get Lucky and close Firefox` still fail closed.
The user installed revision 3 and confirmed that `Play Don't Push Me by 50 Cent`
worked end to end.

## 10. Understanding next and previous

Next and previous initially appeared broken. The actual behaviour depended on
the player context:

- A standalone YouTube video has no playlist neighbour.
- A YouTube playlist or queued MPRIS player can expose next and previous.
- Pause and resume work for a standalone video because those operations do not
  require a queue.

No keyboard simulation was added. The plugin respects the player's advertised
queue instead of inventing browser history semantics.

## 11. Final unified plugin

The working media backend was then separated from the dispatcher into one real
OVOS component: `ovos-skill-jarvis-media`.

The final ownership boundary is:

### Jarvis Media plugin

- title parsing;
- first-result YouTube lookup;
- validated YouTube URL construction;
- configured Brave launching;
- MPRIS player selection;
- play, pause, stop, next and previous execution;
- the pre-Qwen Media routing pipeline.

### Jarvis dispatcher

- approved action IDs and permissions;
- deterministic phrase inventory;
- Commands GUI grouping;
- restricted Qwen selection;
- delegation of the five fixed media operations.

### Optional recognition layer

- Faster-Whisper media hints when the reviewed helper exists;
- no dependency on those hints for deterministic command operation.

The plugin publishes:

```text
opm.skill: ovos-skill-jarvis-media.openvoiceos
opm.pipeline: jarvis-media-pipeline
```

The pipeline is inserted immediately before `jarvis-qwen-pipeline`. This makes
title ownership explicit while allowing every non-media utterance to continue
through the existing OVOS and Qwen path.

## Validation record

Before live plugin installation, the migration passed:

- ten focused plugin and transaction tests;
- clean wheel construction;
- verification that both installed entry points resolve to classes;
- title and genuine-negation cases;
- fixed-host YouTube result validation;
- active-Brave and generic MPRIS selection;
- dispatcher delegation and pipeline ordering;
- transactional installation and rollback;
- complete recovery from a forced live failure;
- the complete Jarvis validation covering 32 Python modules, 93 intents,
  vocabulary consistency, personal phrase collision checks, application action
  coverage, deployment profiles, runtime helpers, systemd templates, imports
  and skill construction.

The integrated Media revision 3 path was verified live before packaging. The
standalone unified plugin migration still requires its own live installation
and everyday command check before it should be marked release-ready.

## Permanent engineering lessons

| Problem | Retained rule |
| --- | --- |
| Virtualenv Python is a normal symlink | Validate its resolved executable target; do not apply a blanket data-file symlink ban. |
| Entry point imported in a unit test | Also build the wheel, inspect metadata and load the installed entry point through the target OVOS environment. |
| Skill reports ready | Still test that the intended utterance selects its handler before Qwen. |
| Exact transcription but wrong handler | Diagnose routing separately from STT and model behaviour. |
| Multiple Brave installations | Reuse the central application registry and selected launcher. |
| Generated MPRIS instance names | Discover and validate them at runtime. |
| Safety word appears inside a title | Parse its grammatical position; do not reject a word globally. |
| Standalone video has no next item | Respect real player capabilities; do not simulate misleading behaviour. |
| Internal rollback test prints a failure | Capture successful test output and show details only when the test actually fails. |
| Optional Qwen or Whisper component absent | Skip that enhancement cleanly; deterministic Media commands must remain functional. |

## Current status

- Brave-first YouTube playback: verified live.
- Existing Brave profile selection: verified live.
- Title containing `Don't`: verified live with revision 3.
- Pause/resume through MPRIS: verified live.
- Next/previous: understood and dependent on a real queue or playlist.
- Unified plugin package: built and validated offline.
- Unified plugin live installation: pending.
- Git repository publication: pending.
