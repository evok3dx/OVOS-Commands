# Focused Commands, Application Integrations and Runtime Isolation

## Purpose and scope

This report continues from `Post-Optimisation Modularisation and Voice-System
Operations`. It records the command and integration work completed after the
initial modular refactor, including focused editing, visible search, Standard
Notes, Proton Mail, Zoom and detached application launching.

The goal of this phase was to extend practical control without returning to a
monolithic dispatcher or allowing one optional application to disable the
whole command system.

## Status terminology

- **Confirmed live** means the behaviour was observed working on the Brain.
- **Installed** means it passed static validation and was deployed, but every
  voice route may not yet have been exercised.
- **Repository baseline** means the complete source and documentation are
  preserved together and can be deployed through the main deployment script.

## Architecture after this phase

The dispatcher now contains eleven root modules and four files in
`integrations/`, for fifteen Python modules in total:

```text
ovos_skill_jarvis_dispatcher/
├── __init__.py
├── agents.py
├── browser.py
├── conversation.py
├── desktop.py
├── dictation.py
├── helpers.py
├── profile.py
├── text_editing.py
├── vocabulary.py
├── wakeword.py
└── integrations/
    ├── __init__.py
    ├── proton_mail.py
    ├── standard_notes.py
    └── zoom.py
```

`text_editing.py` contains reusable focused-window behaviour. Application
shortcuts that are meaningful only in one product remain in guarded integration
modules. Each optional integration has a fail-safe replacement in
`__init__.py`, so a failed optional import reports only that feature as
unavailable.

## Deterministic inventory validation

The validator remains the source of truth rather than a manually remembered
count. The repository baseline is now:

```text
PASS: 15 Python modules compile
PASS: 63 intents match the expected inventory
PASS: 994 vocabulary registrations are present
PASS: 3 deployment profiles validate
PASS: package imports and create_skill() succeeds
```

An intended feature must update both implementation and expected inventory.
An unexplained addition, loss or rename fails validation.

## Focused editing and clipboard commands

The reusable focused-window layer gained:

- select all and delete selected text;
- clear all text with explicit confirmation and same-window verification;
- undo and redo;
- copy, cut, paste and save;
- Tab navigation to the next field;
- Shift+Tab navigation to the previous field.

Terminal-specific shortcuts are used where safe. Destructive or semantically
different editing actions are refused in Terminal rather than guessed.

The user confirmed the main focused editing additions worked on the Brain.

## Search opens before the spoken query

The original follow-up order asked for the query before opening the visible
search interface. It worked, but provided little visual evidence that the
command had started.

The order is now:

1. identify and retain the focused window;
2. open the appropriate search field;
3. ask, `What should I search for?`;
4. collect the response;
5. verify that the original window still owns focus;
6. type the query;
7. execute it only where the product requires Enter.

Generic pages and documents use `Ctrl+F`; Terminal uses `Ctrl+Shift+F`.
Standard Notes and Proton Mail use their verified application-specific search
interfaces. The user confirmed generic page search worked.

## Standard Notes integration

Standard Notes now provides:

- new note through `Alt+Shift+N`;
- current-note search through `Ctrl+F`;
- all-notes search through the universal `Ctrl+Shift+Colon` palette.

The vocabulary separates `search this note` from `search notes`. Recognition
aliases `search this node` and `find in this node` account for an observed
Whisper substitution without changing meaning.

Standard Notes 3.202.0 separately produced one `SIGBUS` and one `SIGTRAP` core
dump. Later Standard Notes searches worked, its own log contained no useful
failure, and the kernel showed neither an out-of-memory kill nor a storage
error. This remains an upstream Electron/AppImage issue to monitor rather than
evidence of an intent-routing failure.

## Proton Mail integration

Official Proton shortcuts were used instead of screen coordinates:

- `N` opens a new message;
- `/` focuses mailbox search;
- `Enter` executes the query.

The integration focuses Proton Mail, verifies its window, opens search before
the spoken follow-up and cancels if focus changes. Sending mail is intentionally
excluded because it needs recipient validation and explicit confirmation.

## Zoom copied-link integration

Zoom on the Brain registers:

```text
x-scheme-handler/zoommtg → Zoom.desktop → /usr/bin/zoom %U
```

Linux exposes no documented shortcut for opening Join Meeting. The integration
therefore accepts a copied Zoom invitation, permits only `zoom.us` or its
subdomains, extracts a numeric meeting identifier and optional `pwd` locally,
and invokes the registered `zoommtg` handler without browser redirection.

Links and embedded passwords are not spoken. Failure logging deliberately
omits exception objects that could include the generated meeting URI.

## Why Zoom mute and video commands were deferred

Zoom documents `Alt+A` and `Alt+V` as start/stop toggles. A command named
`mute microphone` could unmute an already-muted microphone; `disable video`
could enable an already-disabled camera. These names are unsafe until current
Zoom state can be verified through an accessibility or application API.

Safe interim names would be `toggle Zoom microphone` and `toggle Zoom video`,
but state-aware operations remain preferable.

## Flatpak Brave mismatch

The Brain had two Brave installations:

- the regular Flatpak, `com.brave.Browser`, containing the user's normal
  profile;
- `/usr/bin/brave-browser-stable`, a separate DEB installation hardcoded in
  `jarvis-app-window`.

When the existing Flatpak window was not matched, Jarvis launched the DEB and
appeared to open a different version of Brave. The helper now prefers
`flatpak run com.brave.Browser`, with the DEB retained only as a fallback.

This is a deployment-specific mapping and is documented so a future installer
does not silently reintroduce the wrong browser profile.

## Detached application launching

`nohup` prevented terminal attachment but did not remove applications from the
OVOS service control group. A Standard Notes core dump showed it within
`ovos-core.service` because Jarvis had launched it.

The helper now asks the user systemd manager to create a collected transient
service for each application launch. Consequently:

- restarting OVOS does not terminate an application launched by Jarvis;
- application crashes remain outside the OVOS command process;
- application lifetime and failure accounting are independent;
- the existing focus, minimise and close operations remain window-based.

The user confirmed that the corrected Brave launch worked.

## Feedback and safety conventions

- Successful low-risk key actions remain quiet.
- Search prompts provide both visible movement and one spoken question.
- Destructive clearing requires confirmation.
- A changed focused window cancels delayed text entry.
- Unsupported integrations fail locally and speak a concise error.
- No command accepts an arbitrary executable or shell fragment.
- Clipboard meeting links are strictly validated before use.

## Deployment and rollback

The main deployment script now installs all integration modules, not only
Standard Notes. It validates source and profile configuration before changing
live files, backs up the complete dispatcher and each helper, compiles the
installed result and performs one controlled Jarvis restart.

Incremental installers created during development remain useful forensic
history, but a clean deployment should use:

```bash
python3 scripts/validate_refactor.py
bash scripts/deploy-modular-refactor.sh
```

## Acceptance checks

1. Open the normal Brave profile with `Open Brave`.
2. Run `jarvis-restart` and confirm applications opened by Jarvis remain open.
3. Use `Search this page` and confirm the field appears before the question.
4. Use `Search this note`, then `Search notes` in Standard Notes.
5. Use `New email` and `Search mail` in Proton Mail.
6. Copy a non-sensitive test Zoom invitation and use `Join copied meeting`.
7. Test `Next field`, `Previous field`, copy, paste and save.
8. Run the validator and confirm the 15/63/994 baseline.

## Final state

This phase established a clearer extension model: reusable standard commands,
guarded product integrations and personal deployment profiles. Focused editing
and search now work consistently across applications, Standard Notes and Proton
Mail have contained integrations, copied Zoom meetings can bypass browser
redirection, and desktop applications no longer share OVOS process lifetime.

The remaining Zoom microphone/video work is intentionally deferred until it
can preserve requested state rather than blindly toggle it.
