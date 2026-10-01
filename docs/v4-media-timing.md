# V4 music result timing

Media 0.3.5 acknowledges an accepted title immediately, performs one bounded
lookup and waits three seconds after finding a valid result before opening it.
Stop or a replacement title interrupts that final wait. The shared 11-second
search gap and Qwen fallback remain. This is a comfortable transition, not a
promise about provider bot detection. Weather, native network policy, models
and frozen dependencies are unchanged.

The normal-user patch is for the existing isolated installation with the
reviewed Media 0.3.4 weather/handler correction already applied. It verifies
known installed and downloaded hashes, requires all five workers stopped,
backs up privately in Downloads and updates two source files. Media registration
uses existing local tooling without dependency resolution or an index. A
registration failure restores source and attempts the prior registration.
Unknown/custom source is preserved for review. The published rc2 archive/tag
is unchanged.

Source commit `6dd4283e080160a640aa358d61a44b1d40772412` passes all six
validation jobs in run `36819524368`, including fast/slow lookup timing,
cancellation, full deployment/recovery and 350/350 clean-copy policy cases.
The guarded handover is commit `884259cf18c4df25819d630e78dcbee921fb700f`;
its separate validation is recorded in [releases](releases.md).

Stop Jarvis in the Control Centre, close it, and run as your normal user:

```bash
(
  set -e
  test "$(id -u)" -ne 0
  mkdir -p "$HOME/Downloads"
  jarvis_music_dir="$(mktemp -d "$HOME/Downloads/jarvis-v4-music.XXXXXX")"
  curl --fail --location --proto '=https' --proto-redir '=https' \
    'https://raw.githubusercontent.com/evok3dx/OVOS-Commands/884259cf18c4df25819d630e78dcbee921fb700f/scripts/apply-v4-media-timing-fix.py' \
    -o "$jarvis_music_dir/apply-v4-media-timing-fix.py"
  printf '%s  %s\n' \
    'ad24a3b373fc949292f9c4ff9a85e22dac9bdd6969aac46c932afb2328902644' \
    "$jarvis_music_dir/apply-v4-media-timing-fix.py" | sha256sum --check
  "$HOME/.venvs/ovos/bin/python" -I "$jarvis_music_dir/apply-v4-media-timing-fix.py"
)
```

Reopen the Control Centre and choose Run Jarvis. Test a title, then test Stop
and a replacement title during the post-result pause. Browser opening timing
still requires a live retry; automated checks do not prove desktop playback.
