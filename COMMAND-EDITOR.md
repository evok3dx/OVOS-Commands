# Jarvis command editor

The tray's **Commands…** item opens a small editor for personal voice phrases.

- Search or filter the approved actions.
- Review every existing built-in phrase for the selected action.
- Select an action.
- Add one or more phrases.
- Choose **Save & Reload**.

Built-in commands remain read-only. Personal phrases are stored privately in
`~/.config/jarvis/custom-commands.json`. The editor cannot add shell commands or
new behavior; new phrases can only call actions already implemented by Jarvis.

The editor opens at 820 × 720 and keeps the action list at a useful minimum
height. Saving reloads only Jarvis commands and does not create a second tray
process.

Install:

```bash
bash scripts/install-command-editor.sh
jarvis-command-editor
```

Install `scripts/install-ovos-tray.sh` as well to open the editor from the
tray's **Commands…** item.

Rollback:

```bash
bash scripts/uninstall-command-editor.sh
```
