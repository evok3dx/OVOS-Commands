# Modular refactor runtime tests

Do not merge the draft pull request until these tests pass on the Brain.

## Before deployment

```bash
git switch modular-refactor
git pull --ff-only
python3 scripts/validate_refactor.py
```

## Deploy

```bash
bash scripts/deploy-modular-refactor.sh
```

The deployment script creates a timestamped copy of the installed package before
changing it, compiles every module, restarts Jarvis and shows core status.

## Existing voice-command regression test

Run each command by voice and confirm the visible action and spoken response:

1. `Hey Jarvis, open Firefox`
2. `Hey Jarvis, search Firefox`, then provide a query
3. `Hey Jarvis, new tab`
4. `Hey Jarvis, close tab`
5. `Hey Jarvis, open Brave`
6. `Hey Jarvis, search Brave`, then provide a query
7. `Hey Jarvis, scroll down`
8. `Hey Jarvis, open note`
9. `Hey Jarvis, write this`, dictate short text, confirm it, then say `send it`
10. `Hey Jarvis, start writing`
11. `Hey Jarvis, pause writing`
12. `Hey Jarvis, continue writing`
13. `Hey Jarvis, stop writing`
14. While Jarvis is speaking, say `Hey Jarvis` and confirm speech stops immediately
15. `Hey Jarvis, close window`

## Log check

```bash
journalctl --user \
  -u ovos-core.service \
  -u ovos-listener.service \
  -u ovos-audio.service \
  --since "15 minutes ago" \
  --no-pager -o cat |
rg -i \
  'raw transcription|parsing utterance|intenthandlermatch|speak:|traceback|error|failed'
```

Expected results:

- Commands match `ovos-skill-jarvis-dispatcher.openvoiceos`.
- No import errors, tracebacks or missing-module errors appear.
- Browser, desktop, writing and dictation behaviour matches the pre-refactor build.
- Wakeword barge-in still stops TTS immediately.

## Rollback

If any runtime test fails, do not merge. Restore the timestamped backup path
printed by the deployment script, then run `jarvis-restart`.

