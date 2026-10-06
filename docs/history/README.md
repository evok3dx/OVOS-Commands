# Historical implementation records

These reports preserve the sequence, tests and reasoning behind earlier Jarvis
updates. Their package names, installer commands and validation totals describe
the point in time when each report was written.

The [2.3.1 README summary](readme-2.3.1.md) preserves the earlier release
direction without retaining machine-specific paths or obsolete operational
instructions.

Completed V2/V3 audits, V3.1 incident checklists, package inventories and the
V3 development record also live in this folder. They are evidence, not current
installation instructions. Their `PLANNED` labels describe their original
point in time and do not override current code, tests or the active release
record.

For current operation use the repository [README](../../README.md), the
[command reference](../command-reference.md) and the
[maintenance guide](../maintenance.md).

The [V4 development record](v4-development.md) preserves RC trials, weather
and media investigations, exact evidence and the original expanded stable
notes. The [4.0.1 recovery record](v4.0.1-recovery.md) preserves the resolved
guided-isolation startup and package-build incidents. Stable V4 scope and unresolved checks live in the current release ledger.

The [temporary V4 repair record](temporary-v4-repairs.md) summarises retired
delivery scripts, their maintained fixes and the immutable legacy source.

## Recording issues and solutions

Keep a short, sanitised record when an investigation provides a reusable
solution or explains an important design choice. Add it to the relevant
existing record; a new document is unnecessary for every small fix.

- **Symptom and versions:** what failed and which releases were affected.
- **Cause:** what the evidence established; label any remaining uncertainty.
- **Solution:** the safe remedy and fixed release, linking to maintained code
  or the current troubleshooting guide.
- **Verification and limits:** the relevant test/release evidence, distinguishing
  automated checks from live observations and retaining unresolved limits.

Keep earlier failed approaches only when they explain why the final remedy is
needed. Current operational instructions stay in troubleshooting; historical
records link there rather than asking users to apply an obsolete patch.
Exclude raw machine logs, transcripts, private paths, identifiers and temporary
download URLs. The useful history is the issue and solution, not the disposable
delivery files.
