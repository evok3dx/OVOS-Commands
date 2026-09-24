# Automatic desktop application discovery

This version replaces the earlier fixed-list discovery limitation. Additional
apps no longer require a new code entry. The existing setup screen scans desktop
menu entries in XDG application directories, user and system Flatpak export
directories. User overrides, Hidden/NoDisplay, OnlyShowIn/NotShowIn, Type and
TryExec are respected. Settings entries are allowed if visible on this desktop;
there is no blanket category blacklist. Terminal-only tools without desktop
entries are outside this launcher scope.

Application IDs are hashes of desktop IDs. The capabilities file stores selected
IDs, not arbitrary launch commands. Profiles resolve selected IDs against current
installed desktop entries. Missing/uninstalled entries are skipped without
invalidating other choices. All-detected mode adds new discovered entries at
Jarvis startup; custom mode does not. Reopening setup rescans the app list.
The installer preserves existing choices; use setup to choose new apps.

The existing generic Jarvis intents register discovered names and unambiguous
executable/Flatpak aliases. Duplicate menu names receive package-type qualifiers;
ambiguous aliases are removed. Longest matching app name wins, so Sticky Notes
does not accidentally select the Notes integration. Discovered apps are excluded
from Qwen's catalog in that original release. The app-fallback update below supersedes this restriction.

GIO launches the full desktop entry in a detached user systemd service. Desktop
Exec paths, quotes, arguments and field codes are not truncated or evaluated by
a shell we create. DBus-activatable entries are accepted. Native and Flatpak
apps use the same desktop launch path. Locally installed desktop entries are
trusted, as when launching them from the normal desktop menu.

Named focus/minimise/maximise/close use exact StartupWMClass or Flatpak identity
when available. No fuzzy title match or process killing is used for discovered
apps. With no reliable class match, named window operations decline; open still
launches and may create another instance. GIO acceptance is not proof that an
app displayed a working window. Existing named integrations keep their reviewed
window helpers and verification.

Existing built-in names, including disabled integrations, are reserved and
specialised Hermes/Claude/ChatGPT/Proton paths are not replaced by generic menu
entries. Default Mail remains distinct from Proton Mail. Existing native/Flatpak
launch helpers and user choices remain intact. Basic Calculator, Settings and
Files remain in their existing rows. Additional apps appear automatically.

The setup list scrolls, reflects existing selections and preserves unrelated
configuration, including conversation, wake phrase and shortcuts. Saving app
choices restores previously active audio/core/listener services even when core
stops dependent services, and checks readiness. The installer separately backs
up source/configuration and restores services on failed installation/rollback.
Rollback will not overwrite later edits.

## Upstream reuse and licence

The previously bundled two methods, parse_desktop_file and launch_app, remain
unchanged from OpenVoiceOS application-launcher 0.13.2a1:
https://github.com/OpenVoiceOS/ovos-skill-application-launcher/blob/0.13.2a1/__init__.py
Git blob: 58163bee8d8a0b5c1405cb6046d2bb976a4e2d28.
Apache-2.0 licence: OVOS-LAUNCHER-LICENSE.txt.
Authors/contributors: OpenVoiceOS application-launcher project.

The complete standalone upstream voice skill is not installed. Local discovery,
selection and GIO launching adapt its desktop-file discovery approach to preserve
Jarvis integration and handle Flatpak exports and full launch commands. No OVOS
package or Workshop upgrade is needed. There is no additional speech pipeline.

## Validation and desktop check

Focused tests cover generic discovery, Flatpak entries, hidden overrides,
duplicate names, disabled built-in protection, automatic versus custom selection,
voice vocabulary, restricted Qwen catalog, exact window identity, setup settings
preservation, staging permissions and service/failure rollback. Source,
deployment and release gates must pass before packaging.

These are isolated tests; app process execution, live GTK interaction and voice
recognition require the user's desktop. After saving selections, try opening a
new native app and a Flatpak, then check existing Mail/Hermes and volume/read/stop.
No extra model benchmark is required. Whisper hints and Bella are untouched.
Git publication remains a separate, later step.


## Launcher and chooser repair

The user confirmed a live regression after automatic discovery loaded at
20:08:28 on 23 September: Calculator, Zoom and Firefox commands matched, but
the shared window helper returned failure. The launch-service journal recorded
GIO starting; it did not establish an app window appeared or identify every
underlying cause. Save also blocked the chooser during the restart.

Existing integration launch paths are restored to their pre-launcher versions.
Calculator/Settings/Files and generic discovered apps keep GIO launching, now
with Type=exec and ExitType=cgroup. This follows systemd's documented support
for graphical apps without a stable main process. The service tracks children
after GIO exits. Normal launch requests do not use --wait (which would wait for
app termination). They wait for the service startup result and log startup
errors. Legacy helper errors are now retained in the OVOS log, without adding
utterance, clipboard, audio or transcript logging.

Reference inspected: systemd/systemd, man/systemd.service.xml, ExitType section:
https://github.com/systemd/systemd/blob/main/man/systemd.service.xml
ExitType=cgroup was introduced in systemd 250. The installer checks the actual
fork/child lifetime in the user's service manager before changing code; it does
not assume a working desktop based on that check. The existing upstream parser
is still used for known desktop entries. The bundled upstream launch method is
retained but the active startup path uses checked subprocess execution instead.

Tray > Setup already launches jarvis-setup --gui; no new tray handler is needed.
The chooser is now Jarvis Applications, sized to 720x640 or smaller screens,
resizable, searchable, alphabetical and scrollable, with Application/Say this
columns and a selected count. Examples come from registered aliases rather than
invented commands. Checkbox edits are available in Choose applications mode.
Save runs configuration/service work in a worker, returning UI updates through
GLib. Progress and errors remain visible. It prevents concurrent saves, and does
not restart for unchanged choices. GTK itself is only touched on the main thread.
The previously active voice services and readiness are still verified.

The repair installer only replaces code. It neither rewrites app selections nor
reverts later app-selection changes on rollback. Rollback returns to the source
immediately before this repair, which can include the reported regression.

Validation includes real-thread worker scheduling, error delivery, spoken-name
examples, unchanged-save behaviour, restored Firefox/Zoom shell paths, Calculator
backend selection, new service options and failure handling, plus the existing
source/deployment/build gates. No real GTK render or desktop launch can be
verified in the build environment. Final confirmation remains the user's brief
Calculator/Firefox/Flatpak test. No AI payloads, allowlists or voice settings change.

## Configure Jarvis and spoken names

The user confirmed the preceding launcher/chooser repair works. The next local
update merges Setup and Commands into Tray > Configure Jarvis, with Applications
and Custom commands tabs. It reuses the existing GTK phrase editor as a widget;
old command-editor shortcuts open the Commands tab in this same window.

Applications show desktop-entry icons where available, theme icons for known
apps, and a generic fallback with text labels. The resizable, screen-clamped
window has scrolling on both tabs. The Spoken name column is editable and the
Say this example updates immediately. Save applies both tabs on a worker thread
with one voice restart; unsaved changes are flagged on closing. Generated action
phrases refresh when entering the Commands tab without discarding draft phrases.

Additional spoken names live in capabilities.json under spoken_names, keyed by
integration ID. Original aliases are retained. Clearing an override restores
defaults. Names cannot claim another integration's aliases, including disabled
integrations, reserved control words, built-in phrases or personal phrases.
If a newly installed app conflicts with an older override, runtime ignores that
override and keeps the original app aliases, rather than disabling the profile.
Saved names generate the existing five native app-command operations. They never
become executable paths, shell strings or arbitrary actions.

Both configuration and personal phrases validate before writing; a second-file
write failure restores the first file. External changes since opening the window
block a save. A restart failure reports that settings were saved and directs the
user to Restart Voice System. Removing an app with personal phrases is blocked
until the user removes those phrases, preserving them instead of silently
losing commands. Unchanged saves skip the restart.

Files gains the alias “my files”, so “open my files” reaches its existing native
handler. The model is not retrained. Files, Calculator, Settings and discovered
apps are still excluded from Qwen; that explains why the previous AI fallback
could not propose their actions. The update does not change AI permissions.

The installer constructs the actual GTK widgets on the user's desktop in a
read-only preflight, compares installed/staged router catalogs, stages source
validation and retains backup plus voice-service restoration. Build tests do not
claim visual rendering or real voice success. No desktop launch paths, Whisper,
Bella, volume/read/stop settings, model packages or Git publication are changed.


## Enabled apps in the Qwen fallback (qwen.apps.1)

After the Configure update was confirmed working, the app-fallback update connects
its enabled applications and saved spoken names to the existing local Qwen router.
This supersedes the earlier exclusion of Files, Calculator, Settings and discovered
apps. No model training, new model, dependency installation or prompt tuning is
involved. Existing deterministic commands still run before the fallback.

Qwen can choose open, focus, minimise or maximise for the explicitly named,
enabled app. Discovered apps without usable window identity expose opening only.
Disabled apps, conflicting names and multiple named targets decline. Original
aliases and saved spoken names remain available; Mail and Proton Mail remain
distinct. Each model request contains just the named app's permitted actions,
plus applicable existing search actions, rather than every installed app.

AI closing, typing, Enter/Escape, deleting and sending remain excluded. Native
commands retain their existing permissions. Existing profile/focus checks,
cancellation, expiry and single-use dispatch remain in force. The current app
profile is checked again before execution. All-detected mode resolves discovered
apps consistently in both the skill and router after restart.

The installer changes code only, compares the existing and proposed permissions,
and performs a short classification-only command/question/command check against
the user's existing Ollama model before installation. It reports warm-up and
model loading separately; it opens no app and plays no speech. A failed check
stops before source changes. Service restoration and rollback remain available.

The isolated regression suite and source/deployment/release checks establish code
behaviour, not live recognition or app success. Final confirmation is a brief
spoken request using an enabled app's saved name. This package does not change
Whisper, TTS, wake word, model options, desktop helpers or the Configure dialog.
