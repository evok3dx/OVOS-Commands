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
| Reading or dictation fails | Open **Open Speech Note and setup guide…** and confirm Speech Note is installed and configured. | Keep its existing models, voice and rules; do not reinstall or replace them as a first step. |
| Speech Note reading fades or changes volume at paragraph or hard-line boundaries | In Speech Note, open **Settings → Text to Speech** and turn off **Normalise audio**. | **VERIFIED live with Kokoro/Bella:** per-segment audio normalisation caused the audible fade. This is independent of Jarvis's clipboard hand-off; leave sentence splitting and the document's paragraph structure unchanged unless testing a separate issue. |
| YouTube Music will not resume after being idle | In Brave, open **Settings → System → Performance → Always keep these sites active** and add `music.youtube.com` and `youtube.com`. | Bring the music tab forward once and handle any YouTube confirmation. Jarvis uses Brave's MPRIS session but cannot revive a discarded tab or bypass a site inactivity check. |
| `Read this` repeatedly says reading is still starting | Wait for the current request setup to finish, then retry once. | On 3.8.0 or earlier, update to 3.8.1; an X11 clipboard owner or 2× monitor could retain the setup lock. Do not delete Speech Note settings or its speed file. |
| Control Centre remains on `Installing update` | Select **Stop update**, confirm, and wait for the page controls to return. | Reopen the Control Centre and compare the installed/latest versions. A completed command-line update can leave only the older GUI process stuck; do not run a second installer until the first process has stopped. |
| Tray icon is missing | The voice system can still run without the tray. Start `~/.local/bin/ovos-tray` from a terminal. | Check `~/.local/state/jarvis/ovos-tray.log`. |
| A problem began directly after a Jarvis update | Run the health check and view recent logs. | Use `jarvis-update rollback` only if the release caused the regression. |

## Service controls

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
