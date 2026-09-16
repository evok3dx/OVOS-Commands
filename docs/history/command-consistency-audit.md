# Command Consistency and Universal Reading Audit

> Historical record. Use the current README and validator for live behaviour.

## Result

The configured applications share one generated control vocabulary. Every
alias for Brave, Firefox, Signal, Zoom, Terminal, Standard Notes, ONLYOFFICE,
Claude, Hermes, Proton Mail and Proton Calendar receives the same actions:

- Open: `open`, `launch`, `start`
- Focus: `focus`, `show`, `go to`, `bring up`, `switch to`
- Minimise: `minimize`, `minimise`, `hide`, `put away`
- Close: `close`, `quit`, `exit`

Validation now checks every action against every app alias so a future edit
cannot silently leave one application behind.

## Universal local reading

`Read page`, `read window`, `read app`, `read screen` and their included
variants always run through Jarvis. They do not ask Claude, Hermes or another
application's AI to interpret or read the interface.

The reader uses this order:

1. Brave and Firefox: copy the page and reduce semantic HTML to useful main
   content while excluding navigation, headers, footers, forms and buttons.
2. GTK, Qt and Electron applications: read the focused application's AT-SPI
   accessibility tree while excluding menus, toolbars, buttons and status UI.
3. Applications without useful accessibility content: use the existing safe
   clipboard shortcut fallback.
4. Terminal: use terminal-safe selection and copy shortcuts so `Ctrl+C` never
   interrupts a running command.

Hermes and Claude Desktop start with renderer accessibility enabled, allowing
Jarvis to read their visible conversations independently of either model or
provider. Both receive a 30-second cold-start allowance before Jarvis reports
that their window could not be found.

Speech Note remains the local reader. OVOS listening is muted during playback
to prevent self-triggering, then restored when reading ends. Wake-word or
hotkey interruption cancels Speech Note through D-Bus without spoken success
feedback.

## Deliberate boundaries

- `Read selected text` reads only the current selection.
- `Read it back` reads the last text Jarvis typed.
- `Read it to me` remains reserved for the latest agent response.
- Close commands retain confirmations because they are destructive.
- Routine focus, minimise, maximise, restore and navigation actions remain
  quiet.
