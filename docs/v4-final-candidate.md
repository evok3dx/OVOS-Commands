# Jarvis V4 cumulative update: 4.0.0rc2

**Historical guarded handover:** stable 4.0.0 now includes these changes.
Use [current release notes](release-v4.0.0.md) for installation and limits;
keep the original prerelease/patch instructions below for their exact versions.

This cumulative laptop candidate includes the V4 installer, GUI, independent
login options, desktop-session repair, readiness/lifecycle fixes and Media
0.3.3. The complete 296-wheel, hash-verified runtime is reused byte for byte;
NumPy stays at 2.4.6 with zero dependency exemptions. Models and saved policy
are preserved. Hermes and other agent platforms are not installed.

The update button has white text and icon on its green background. Clear song
titles use the separate ready Media helper directly; Qwen retains semantic
fallback. The owner-selected 11-second gap is between separate searches, not
a delay on every command. A repeated music request acknowledges once, waits
cancellably and performs one lookup; a newer title replaces pending work and
Stop cancels it. Brief pacing and provider challenge handling remain; no timing
guarantees avoidance of provider alerts. Concurrent Padacioso cleanup uses a
source-hash-guarded mutation adapter. The default boot sound uses the existing
listening cue, while custom choices remain. CLI runtime download/verification
shows measured progress and continuing activity through slow phases.

Automated checks and exercised laptop evidence are recorded in
[releases](releases.md). New music queue timing/cancellation, weather interruption
and broader isolation mediation/recovery acceptance remain live checks. This
is a prerelease; the stable channel remains 3.9.0. It does not silently mark
those checks complete or activate native policy during installation.

## Existing isolated V4 laptop

Use the small immutable, checksum-guarded `scripts/apply-v4-final-fix.py`
handover with Jarvis stopped. It checks exact current sources and five stopped
workers, makes private Downloads backups and registers only first-party Media
locally, offline and without dependency resolution. A failure restores source
and prior registration; unknown/custom files reject before mutation. It changes
no native units, network policy, models or preferences. This patch retains the
installed dispatcher version label; the full cumulative archive is 4.0.0rc2.

Stop Jarvis in the Control Centre, then close the Control Centre and run:

```bash
(
  set -e
  test "$(id -u)" -ne 0
  mkdir -p "$HOME/Downloads"
  jarvis_fix_dir="$(mktemp -d "$HOME/Downloads/jarvis-v4-final.XXXXXX")"
  curl --fail --location --proto '=https' --proto-redir '=https' \
    'https://raw.githubusercontent.com/evok3dx/OVOS-Commands/cc35fd7484d96dee05544082809549a8b8ee30da/scripts/apply-v4-final-fix.py' \
    -o "$jarvis_fix_dir/apply-v4-final-fix.py"
  printf '%s  %s\n' \
    'd45039137946df746645d1c89fefc7688c8079ba8c10465f5582bbacedb9b95c' \
    "$jarvis_fix_dir/apply-v4-final-fix.py" | sha256sum --check
  "$HOME/.venvs/ovos/bin/python" -I "$jarvis_fix_dir/apply-v4-final-fix.py"
)
```

Reopen the Control Centre and choose Run Jarvis. Test one clear song title,
a second title within 11 seconds, and Stop during that wait. Confirm there is
one acknowledgement and only the latest uncancelled title opens. Test Stop
during weather separately. A source mismatch stops before changing anything;
retain the named file for review rather than bypassing the hash guard.

Do not run the full installer against active native isolation. The existing
reviewed deactivation/removal guard still applies before full update, rollback
or uninstall.

## Fresh or safely deactivated deployment

Download `ovos-commands-4.0.0rc2.tar.gz` and its `.sha256` from this release;
check the digest before extraction. Run `bash scripts/install.sh --no-speechnote`
as your normal desktop user. Enter at the app-selection review prompt preserves
existing choices. The separate runtime archive downloads only when needed;
it is the same verified runtime, not a new dependency stack.

Production signing remains deferred by the owner for this one-client deployment.
Checksums verify bytes, not publisher identity. Native licence notices ship with
the retained runtime. Raw laptop logs, reports, account details and credentials
are excluded from the release.
