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

Validation and immutable handover details will be recorded in
[releases](releases.md) after the checks complete.
