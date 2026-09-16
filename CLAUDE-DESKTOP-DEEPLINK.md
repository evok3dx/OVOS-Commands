# Claude Desktop Deep-Link Messaging

This update keeps Claude Desktop separate from the local Claude Agent.
It includes the exact `message Claude` vocabulary and the observed `cloud`,
`clawed` and `called` speech-recognition variants.

## Voice flow

1. Say `Message Claude`, `Ask Claude`, `Tell Claude`, `Talk to Claude`,
   `Write to Claude`, `Type into Claude` or `Speak to Claude`.
2. Jarvis opens a clean Claude chat, verifies its window and asks for the
   message.
3. Speak the message once. Jarvis clears the composer, types the message and
   presses Enter automatically.

Claude Agent commands continue to require the word `agent`, for example
`Message Claude agent`.

The established Claude Agent verb variations also work for Claude without the
word `agent`: `message`, `ask`, `tell`, `talk`, `write`, `type`, `speak`,
`send to` and `give a task to`.

## Safety behaviour

- Uses Claude's supported `claude://` Linux deep link to open a fresh composer
  before listening.
- Clears the composer before typing so stale draft text is never appended.
- Types and presses Enter only when the same verified Claude window still has
  focus.
- Cancels if focus moves to another window.
- Creates a timestamped rollback copy before installation.

## Install

```bash
bash scripts/install-claude-desktop-deeplink.sh
```

Jarvis restarts once during installation.
