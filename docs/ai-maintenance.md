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

- the canonical `AGENTS.md` contract and current release/decision/support
  records;
- the exact safe source snapshot;
- the supplied problem description;
- repository validation and compatibility results;
- OVOS and Python versions;
- user-service state;
- a SHA-256 manifest covering the bundle.

It does not contain audio, transcripts, clipboard contents, messages, prompts,
credentials or raw logs. Nothing is uploaded automatically.

## Optional five-minute diagnostics

In **General → Logging**, select **Diagnostics for 5 minutes**, then reproduce
the issue. View the fixed technical events in **Maintenance → Recent logs**,
or include the currently enabled capture in a private report:

```bash
jarvis-report --issue-file problem.txt --include-logs
```

The option includes only bounded in-memory technical fields, not raw journal
messages, transcripts, dictation, queries or tracebacks. Capture stops and
clears after five minutes even if the GUI closes; repeated selection does not
extend a running window. No logs is the default, and an off/expired capture
returns that status instead of recovering older logs. Recent Activity is a
separate list of fixed action labels and works with logging off.

4.4 adds reviewed fixed failure reasons and relative capture time, plus explicit
collector availability. It excludes unknown informational traffic and never
formats original failure messages. If these fields are insufficient, request a
targeted content-free status check; silence is not evidence of success.

Historical journals and pre-4.3 reports can still contain speech or private
content. They are not erased by the new mode and are not collected by this
option. Treat every report as private and review the supplied issue description,
source and diagnostic metadata before sharing. See the
[logging limits](security-and-updates.md#application-logging-in-43).

## Patch boundary

The receiving AI is asked to return a unified patch and patch notes, not deploy
anything. Apply a proposed patch only to a clean checkout, rerun validation and
the isolated deployment test, then build a new release. Verify its checksum
through a trusted channel; SHA-256 alone does not authenticate the publisher.
Privileged helpers, sudo configuration and release trust require separate
security review.
