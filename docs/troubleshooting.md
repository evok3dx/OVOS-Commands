# Troubleshooting Jarvis

Start with the smallest check that matches the symptom. These commands inspect
or restart Jarvis only. They do not reinstall the voice stack, replace models,
change shortcuts or overwrite personal commands.

## First safe check

Run:

```bash
jarvis-health-check
```

If it passes, test the failing action again. If the tray says `starting`, allow
the skill to finish loading first. If it says `stopped`, select **Start voice
system**. If it says `failed`, inspect the recent logs before changing files.

## Common symptoms

| Symptom | First action | Next check |
|---|---|---|
| A newly installed command is not recognised | Select **Restart Jarvis commands** or run `jarvis-restart`. | Run the health check and retry the exact documented phrase. |
| Wake phrase does not respond | Check that the microphone indicator is green and that the listener is active. | Open **Wake phrase…**, then use **Restart full voice system**. |
| Manual-listen shortcut does nothing | Open **Keyboard shortcuts…** and confirm the bindings. | Run `jarvis-health-check`; the update preserves existing bindings. |
| An app opens but an action targets the wrong window | Run `jarvis-app-window focus APP_NAME`. | Follow the [window-focus guide](window-focus-and-app-integration.md); do not change shortcuts until focus works. |
| Reading or dictation fails | Use **Open Speech Note** and **Setup guide…** in Voice and confirm Speech Note is installed and configured. | Keep its existing models, voice and rules; do not reinstall or replace them as a first step. |
| `Read this` is heard as `Write this` | In V4, use **Speak selected text** or **Speak highlighted text**. Cancel an unintended writing prompt first. | Compare the listener's raw transcription with the selected intent. A wrong transcript needs acoustic testing; do not remap a legitimate writing command to reading. |
| Speech Note reading fades or changes volume at paragraph or hard-line boundaries | In Speech Note, open **Settings → Text to Speech** and turn off **Normalise audio**. | **VERIFIED live with Kokoro/Bella:** per-segment audio normalisation caused the audible fade. This is independent of Jarvis's clipboard hand-off; leave sentence splitting and the document's paragraph structure unchanged unless testing a separate issue. |
| YouTube Music will not resume after being idle | Bring the music tab forward or choose a new song. A discarded tab or expired session can remove Brave's MPRIS player. | Jarvis controls the session Brave exposes. It cannot guarantee that a performance setting preserves playback or bypass YouTube inactivity checks; no automatic tab clicking or forced workaround is provided. |
| `Read this` repeatedly says reading is still starting | Wait for the current request setup to finish, then retry once. | On 3.8.0 or earlier, update to 3.8.1; an X11 clipboard owner or 2× monitor could retain the setup lock. Do not delete Speech Note settings or its speed file. |
| Control Centre remains on `Installing update` | Select **Stop update**, confirm, and wait for the page controls to return. | Reopen the Control Centre and compare the installed/latest versions. A completed command-line update can leave only the older GUI process stuck; do not run a second installer until the first process has stopped. |
| Control Centre fails with `set_active_id` / `set_text(choice.get_label())` / `Argument 1 does not allow None` | Apply the reviewed V4 GUI source fix and reopen. | The icon row is a custom GTK child, so `get_label()` is empty; saved app choices must remain intact. Gdk screen-size deprecation warnings are not the cause. |
| Tray icon is missing | The voice system can still run without the tray. Start `~/.local/bin/ovos-tray` from a terminal. | Check `~/.local/state/jarvis/ovos-tray.log`. |
| Voice works manually but does not start after login | In the updated V4 candidate, turn on **General → Start voice services at login**. Use **Dashboard → Run Jarvis** for the current session. | **Start app minimised at login** controls the tray separately. Verify after a fresh login; changing either setting does not start/stop current services. Active service status alone does not prove auto-start. |
| A problem began directly after a Jarvis update | Run the health check and view recent logs. | Use `jarvis-update rollback` only if the release caused the regression. |

## Service controls

For slow named-city weather, compare transcription, intent-match and first
`Speak` timestamps. The observed post-rc2 delay is after matching. The source
correction logs `Weather intent/location`, `forecast`, `display`, `speech
submission` and fixed provider-operation durations; use those measurements
before changing timeouts or blaming the laptop. The exact pinned upstream
skill also used home coordinates for a named-city forecast; the guarded adapter
corrects that per request without changing your saved home location.

Wikipedia and WikiHow package installation does not mean their online skills
are enabled in isolation. They are blacklisted in the core and have no reviewed
standalone helper yet. General questions can consequently reach local Qwen.
Preserve network isolation while investigating those compatibility gaps.

V4 restores direct title routing to the separate
Media worker; Qwen still handles semantic fallbacks. A new music request during
the owner-selected 11-second shared search gap waits locally and says only
"Let me spin that track". Stop cancels the pending request, and another title
replaces it. After finding a valid result, Media waits three seconds before
opening the browser. Stop or a replacement title cancels this transition. This is pacing, not playback paused or search disabled. Actual
YouTube/429 refusal is still reported without automatic retries.

The reviewed Padacioso cleanup adapter serialises concurrent registration and
detach mutations. Unknown upstream source fails review instead of applying an
unverified patch. Deprecation warnings and background intent compilation are
retained; a compile duration alone does not prove a failed service.

The isolation boot-readiness adapter checks enabled local services and skills.
It excludes blacklisted IDs only from the default inventory, preserves explicit
owner readiness/announcement settings and cancels its callback on skill
shutdown. If a journal logs normal main cleanup followed by a systemd stop
kill, that proves incomplete process exit, not slow skill unloading. Keep the
failure visible and verify the corrected callback on the laptop; do not clear
failure metadata or relax network filtering to turn the icon grey.


If the Control Centre reports a readiness timeout but Commands subsequently
works and the microphone remains paused, inspect the current invocation's load
times. The corrected V4 control wait allows up to three minutes, with continued
loading feedback every 15 seconds and an immediate exit for a failed worker.
It still requires the reviewed ready markers, never declares an active process
ready by state alone and never auto-restarts a deliberately paused listener.
This is a startup wait; it does not extend systemd's separate shutdown deadline.

Restart command handling after a Jarvis code or vocabulary change:

```bash
jarvis-restart
```

Restart the listener and audio path as well:

```bash
jarvis-restart --full
```

Inspect service state without changing it:

```bash
systemctl --user status \
  ovos-core.service ovos-listener.service ovos-audio.service
```

Follow recent service output:

```bash
journalctl --user \
  -u ovos-core.service \
  -u ovos-listener.service \
  -u ovos-audio.service \
  -n 200 -f
```

Press `Ctrl+C` to stop following the logs.

In V4 native isolation mode, user units are compatibility relays;
their active state alone does not prove that a voice worker is running. The
Control Centre and fixed restart/microphone helpers query the actual mapped
workers. See [service isolation](core-isolation.md) for the version-3 read-only
worker collector, native review and owned removal sequence. It never unmutes
a deliberately muted listener for a test.

If selected-text reading and focused-window controls fail together after
isolation, inspect the actual worker's desktop environment and the effective
`EnvironmentFiles` property. A correctly saved session file is not proof that
the worker loaded it. In systemd 255 an enclosing quote on the
`EnvironmentFile=` filename makes it non-absolute and the parser ignores it.
The corrected generator uses a literal absolute path, with doubled percent
signs for specifiers. Existing native data needs a bounded owner-terminal
repair with stopped workers and a backup before reload/start. Keep the IP
restrictions and configuration intact; do not reinstall the runtime or replace
the clipboard helper. Exact old candidates remain usable for removal only.

If update, rollback or uninstall refuses an isolation receipt or remaining
native policy, stop the actual workers and follow that candidate's reviewed
deactivation/native removal instructions first. Do not delete only the receipt
or disable the guard: rules must not continue referencing replaced code.

The V4 source candidate now has a complete rebuilt, hash-verified runtime bundle.
The initial 4.0.0rc1 archive can stop before installation with `Cannot inspect
native isolation policy` on systems whose polkit rules directory is protected.
This is not evidence that a Jarvis rule exists. The current source hotfix keeps
routine deployment password-free. When the rules directory is protected, it
reads only system-manager state for the five fixed account-specific workers,
using no sudo or authentication prompt. Every worker must be not-found/inactive
with no fragment or drop-ins, and other native deployment paths/receipts must
be absent. The hidden rule itself is uninspected, not asserted missing.
Installed/loaded workers, visible rules/dangling links, Ollama policy, denied or
incomplete checks and timeouts remain blocked. Apply the immutable hash-verified
hotfix in [the testing instructions](v4-laptop-test-release.md). Do not use the
superseded sudo-stat proposal, chmod the directory or sudo the installer.
Native isolation setup/removal retains its separate administrator review.

Use the exact archive named in `voice/runtime-bundle.json`; the installer checks
its size, digest and all 296 wheel identities before staging. Older recovery
checkouts may still report **REBUILD REQUIRED**. Updating the checksum alone or
using an incomplete wheelhouse cannot resolve that state. Keep the working
laptop deployment until the [live acceptance gates](v4-acceptance.md) pass.

## Runtime staging and saved app choices

If the first V4 test installer rejects `phoonnx -> ovos-number-parser>=0.4.0`
during runtime staging, use the verified dependency-lock hotfix in the current
testing instructions. Older host packaging libraries reject the selected OVOS
alpha in an implicit membership check. The hotfix makes prerelease handling
explicit for the exact reviewed inventory; all constraints and hashes remain
enforced. Do not downgrade OVOS, change the lock or skip dependency validation.

At `Review application selection now? [y/N]`, Enter keeps the saved selection.
Choosing `y` intentionally opens setup; choosing Recommended there recalculates
the selected apps. Failed runtime staging leaves those staged app choices
unapplied, so the retry can keep the original configuration.

The upstream [packaging documentation](https://packaging.pypa.io/en/stable/specifiers.html)
records the version-26 change to default prerelease membership. The candidate
verifier explicitly allows only prereleases already selected in the exact
reviewed inventory, with every version constraint still checked.

## Application focus

When one application-specific action fails, verify the application mapping and
focus helper before changing Jarvis or the app shortcut:

```bash
cat ~/.config/jarvis/capabilities.json
wmctrl -lx
~/.local/bin/jarvis-app-window focus standard_notes
echo "exit=$?"
```

Replace `standard_notes` with the affected integration name. Exit status `0`
means that Jarvis found and focused the reviewed window. The complete safe
diagnostic sequence is in the
[window-focus and app-integration guide](window-focus-and-app-integration.md).

## Updates and recovery

Check for a published release without installing it:

```bash
jarvis-update check
```

An update changes release-managed Jarvis code, helpers and desktop assets. It
preserves OVOS configuration, enabled apps, personal commands, keyboard
shortcuts, the listening sound, private unlisted helpers, voice packages and
downloaded models.

Restore the latest pre-update Jarvis snapshot if a confirmed update regression
cannot be resolved:

```bash
jarvis-update rollback
```

Rollback restores Jarvis-managed deployment files. It is not a general system
restore and does not undo an unrelated OVOS, application or operating-system
update.

## Private support report

If the cause is still unclear, create a bounded report:

```bash
jarvis-report --issue "Briefly describe what failed"
```

The archive is saved in `~/Downloads`. It includes versions, validation,
service state and integrity information. It excludes raw logs, audio,
transcripts, clipboard contents and messages by default, and is never uploaded
automatically. Review it before sharing.

## V4 release follow-ups

Choosing another song can open a new tab while the earlier tab keeps playing.
Stop/pause existing playback explicitly or close the earlier tab; automatic
previous-tab replacement is deferred. `Put on {title}` is an existing longer
alternative when recognition mishears `Play`.

New weather locations can spend roughly 13 seconds in search/reverse lookup
before the forecast request. Repeated locations reuse the lookup. The durations
include wrapper/network/provider work, so do not assume a CPU or provider fault.
Collect the three fixed worker units with `journalctl -u ...` without forcing
`--system`; accessible per-user journal output may otherwise be omitted.

For a full upgrade with native isolation already installed, the guarded normal
installer refuses the native state. Use the exact reviewed deactivation/removal
path before the transaction and reprepare against the new source afterward.
Do not remove policies broadly or bypass source identity checks.
