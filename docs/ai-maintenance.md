# AI-assisted maintenance

Create a private diagnostic bundle with one command:

```bash
jarvis-report --issue "Firefox opens, but Jarvis cannot focus it"
```

The command writes `jarvis-ai-report-<time>.tar.gz` to `~/Downloads`, or the
current directory when Downloads is unavailable. Attach that archive to a
coding AI. `AI_INSTRUCTIONS.md` inside the archive provides the repository
purpose, review order, security boundaries, validation contract and requested
patch format, so the handoff does not depend on a long custom prompt.

The normal bundle contains:

- the exact safe source snapshot;
- the supplied problem description;
- repository validation and compatibility results;
- OVOS and Python versions;
- user-service state;
- a SHA-256 manifest covering the bundle.

It does not contain audio, transcripts, clipboard contents, messages, prompts,
credentials or raw logs. Nothing is uploaded automatically.

## Optional logs

Warning-level OVOS journal entries can help diagnose an intermittent failure:

```bash
jarvis-report --issue-file problem.txt --include-logs
```

Obvious home paths, usernames, email addresses and credential-shaped values are
redacted, but automated redaction cannot guarantee that arbitrary log messages
are private. Review the archive before sharing whenever `--include-logs` is
used. Treat every generated bundle as private even when optional logs are not
included.

## Patch boundary

The receiving AI is asked to return a unified patch and patch notes, not deploy
anything. Apply a proposed patch only to a clean checkout, rerun validation and
the isolated deployment test, then build a new release. Verify its checksum
through a trusted channel; SHA-256 alone does not authenticate the publisher.
Privileged helpers, sudo configuration and release trust require separate
security review.
