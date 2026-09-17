# Window focus and application integration

**Validated:** 16 September 2026  
**Platform:** Linux Mint 22.3 / Cinnamon X11

This document records the exact window-focus behaviour used by Jarvis desktop integrations and the troubleshooting process validated across the Brain and a second laptop.

## Why this exists

Jarvis application actions are intentionally not implemented with screen coordinates. The dispatcher resolves an approved application category, calls the fixed `jarvis-app-window` helper, focuses a reviewed X11 window, verifies focus, and only then sends any application-specific shortcut.

That creates a predictable chain:

```text
spoken command
    ↓
OVOS intent
    ↓
capability mapping
    ↓
jarvis-app-window
    ↓
X11 window discovery
    ↓
verified focus
    ↓
application-specific shortcut
```

A shortcut can be completely correct while the command still fails if window discovery or focus fails first.

## Validated Standard Notes behaviour

The current Standard Notes integration uses:

```text
new note     → Alt+Shift+N
search notes → Ctrl+Shift+Colon
```

The laptop validated on 16 September 2026 reported:

```text
WM_CLASS(STRING) = "standard notes", "Standard Notes"
```

and `wmctrl -lx` represented it as:

```text
standard notes.Standard Notes
```

Direct, explicitly targeted tests succeeded:

```bash
xdotool windowactivate --sync <WINDOW_ID> \
  key --clearmodifiers alt+shift+n

xdotool windowactivate --sync <WINDOW_ID> \
  key --clearmodifiers ctrl+shift+colon
```

This proved the application and shortcuts were healthy. The fault was in the helper's window-discovery logic.

## The multi-pattern bug

An older Brain deployment used one exact Standard Notes match:

```text
standard notes.Standard Notes
```

with this literal-substring matcher:

```awk
index(tolower($0), tolower(wanted))
```

That combination worked.

A later portable helper expanded Standard Notes to several accepted X11 spellings:

```text
standard notes.Standard Notes|standard-notes|standardnotes
```

but initially left the old single-literal matcher unchanged. `awk index()` does not interpret `|` as alternation, so it searched for the entire impossible string and could not find an already-open Standard Notes window.

The symptom was:

```text
Could not find the Notes window
```

while a separate check simultaneously showed Standard Notes was already the active window.

## Correct design

`window_match` remains an allowlisted `|`-separated list of literal X11 signatures. `find_window()` must split that value first and compare each candidate independently.

The matcher deliberately does **not** pass the values to an unrestricted regular-expression engine. The alternatives are fixed strings maintained in the helper, not profile-supplied commands.

This lets package variants coexist safely:

```text
pattern A | pattern B | pattern C
```

means:

```text
match A OR match B OR match C
```

not one literal string.

## Why the Brain worked while the laptop failed

The Brain and laptop were not actually exercising identical helper data:

```text
Brain
single exact Standard Notes class
+ single-literal matcher
= works

Laptop
multiple Standard Notes alternatives
+ single-literal matcher
= fails
```

The correct fix is therefore to make the matcher understand multiple reviewed alternatives, rather than reverting portability improvements to one machine-specific class.

## Troubleshooting procedure

When an application opens but a product-specific action does not work, test the layers in order.

### 1. Confirm the capability mapping

```bash
cat ~/.config/jarvis/capabilities.json
```

For Standard Notes, expect:

```json
"notes": "standard_notes"
```

For explicit Proton Mail, expect:

```json
"proton_mail": "proton_mail"
```

`capabilities.json` takes precedence over the legacy `profile.json` when present.

### 2. Confirm installed integration code

Examples:

```bash
grep -nE 'alt\+shift\+n|ctrl\+shift\+colon' \
  ~/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher/integrations/standard_notes.py

grep -nE 'send_focused_keys.*("n"|"slash")' \
  ~/.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher/integrations/proton_mail.py
```

### 3. Inspect the real X11 identity

```bash
wmctrl -lx | grep -i 'standard\|notes'
```

To inspect the currently focused window:

```bash
ACTIVE="$(xdotool getactivewindow)"
xprop -id "$ACTIVE" WM_CLASS
```

Do not assume `xdotool getwindowclassname` exists; some packaged versions do not provide that subcommand.

### 4. Test the helper directly

```bash
~/.local/bin/jarvis-app-window focus standard_notes
echo "exit=$?"

ACTIVE="$(xdotool getactivewindow)"
xprop -id "$ACTIVE" WM_CLASS
```

A healthy Standard Notes result is:

```text
exit=0
WM_CLASS(STRING) = "standard notes", "Standard Notes"
```

### 5. Only then test the application shortcut

A plain terminal command such as:

```bash
xdotool key --clearmodifiers alt+shift+n
```

sends the shortcut to whatever window currently owns focus, often the terminal itself. That is not a valid Standard Notes test unless Standard Notes is actually focused.

Prefer activating the known application window first or use the Jarvis helper.

### 6. Finally test the spoken command

Once direct focus and direct shortcut tests pass, test:

```text
new note
search notes
```

If they still fail, inspect OVOS transcription and intent matching. Do not patch application shortcuts until the lower layers are proven.

## Proton Mail impact

Proton Mail uses the same generic `jarvis-app-window` focus path before its own shortcuts:

```text
new email   → N
search mail → /
```

The multi-pattern fix is generic and therefore protects Proton Mail and future integrations if they acquire several reviewed X11 class variants. A Standard Notes failure does not automatically prove Proton is broken, because each application has its own window signatures.

## Adding a new application or packaging variant

Before adding another X11 signature:

1. Capture the actual `wmctrl -lx` and `WM_CLASS` output on the target machine.
2. Add only the minimum reviewed literal signature needed.
3. Use `|` only for independent fixed alternatives.
4. Verify `jarvis-app-window focus <integration>` on every known packaging variant.
5. Test the product-specific shortcut only after focus succeeds.
6. Run the repository validation and deployment tests.
7. Update the integration documentation when behaviour changes.

Do not use broad title-only matching when a stable application class exists. Do not accept arbitrary window-match strings from speech or capability files.

## Brain/laptop comparison checklist

When behaviour differs between machines, compare the actual deployed helpers instead of assuming the application differs:

```bash
sha256sum ~/.local/bin/jarvis-app-window

grep -nA6 -B3 'notes)' ~/.local/bin/jarvis-app-window
grep -nA30 '^find_window()' ~/.local/bin/jarvis-app-window
```

A matching source archive hash does not prove behaviour matches another machine running an older helper. Compare the deployed helper text and its real window classes.
