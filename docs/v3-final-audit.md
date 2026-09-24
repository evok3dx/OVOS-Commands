# V3 source reconciliation

This is the detailed evidence behind the [living audit](v2.4-audit.md).
**VERIFIED** means checked against source, an offline test, or the named Brain
snapshot; it does not imply a live V3 installation. **PLANNED** means an
acceptance check remains. **HISTORICAL** identifies earlier behavior retained
for context. This comparison was made while GitHub `main` was `3afc733` and
2.3.1 was published. The owner subsequently confirmed that both new plugins
work and authorised publication of V3. Other machine checks remain open.

## Inputs and completeness

| Supplied item | What was checked | Result |
|---|---|---|
| `brain-v3-audit-20260924-205107.tar.gz` and `.sha256` | Archive checksum; 17,299 safe archive members; the SHA-256 and size of all 17,298 inventoried extracted files. | **VERIFIED.** One other member is the inventory itself. The sanitised snapshot deliberately omits private configuration; eight source files and seven private files were skipped. It cannot prove byte-for-byte replication of hidden machine settings. |
| `Jarvis-Brain-Commands-Live(1).md` and `Jarvis-Brain-Final-Audit-Live(1).md` | Action catalogue, New Line/Enter separation, live GUI source and dynamic plugin phrase panels. | **VERIFIED in candidate source:** 88 Brain base actions including New Line remain; V3 adds `files.search` as action 89. The Qwen explicit list grows from 24 to 25; app actions still depend on the active profile. The Brain's 182 actions/2049 unique phrases used private enabled settings absent from the sanitised archive, so they cannot be reproduced exactly offline. |
| `jarvis-media-plugin-update-current.tar(2).gz`, `README(2).md`, `HISTORY(2).md` | Package skill and pipeline source, release history and seven GUI title examples. | **VERIFIED in package and V3 source.** The attached standalone installer, fixtures and baseline are reference material; V3 uses its integrated installer. A later installed plugin on Brain is not established by the final snapshot. |
| `jarvis-file-search-0.2.0(3).zip` | ZIP integrity, package source, 45 filename phrase templates, GUI examples, and reviewed Qwen patches. | **VERIFIED in package and V3 source.** Brain's installed version in the snapshot is 0.1.9. The attached standalone upgrade tool is historical; V3 installs the bundled 0.2.0 source. It never reads file contents for search. |
| Earlier Brain source archive and machine progress notes | Source/installed-file differences and the chronology of wake-word, Whisper, Bella, Qwen, media and GUI repairs. | **VERIFIED as recorded evidence.** Historical 0.2 → 1.0 Vosk timing was intermittent, not the final wake-word fix; see [OVOS voice](06-ovos-voice.md). |

The two bundled plugin packages register skill and pipeline entry points in an
isolated offline environment. That proves packaging and discovery, not a
working OVOS voice loop or an upgrade on either real workstation.

## Installed Brain versus V3 source

| Surface | Comparison | Treatment |
|---|---|---|
| 17 manifest-listed runtime helpers | 16 match Brain's **installed** files byte for byte. `jarvis-read-visible-text` contains the installed 2× Speech Note behavior plus a safe failure exit if Speech Note cannot start. `jarvis-health-check` includes Brain's installed summary. | **VERIFIED** by source comparison and isolated 2×/restoration/failure tests. Older copies inside the Brain source checkout are not the installed truth. |
| Tray and editor | Nine tray source files match Brain byte for byte. Brain has one enabled combined tray; its old microphone indicator entry is disabled. The Commands editor loads the live action catalogue and installed plugin patterns, not the stale saved phrase file. | **VERIFIED** in source and GUI data-path tests; visually test the actual V3 installation later. |
| Dispatcher and integrations | All six integration modules match Brain; 19 of 25 dispatcher modules match byte for byte. Six differ for reviewed local routing/media/new controls. Brain's old integrated `brave_media.py` is replaced by the supplied separate Media skill. | **VERIFIED** in comparison; run spoken behavior on both machines before release. |
| Scripts and profiles | All four profiles match. Eighteen shared scripts match, nine differ for V3 installer, routing, health and rollback work; there is no missing Brain source script. | **VERIFIED** in source; machine-specific private helpers are outside the managed inventory and are retained in place. |
| Whisper `small.en` | Brain's installed dynamic helper includes enabled app names **and** short media/writing cues. The candidate helper now matches it byte for byte; the installed plugin has the forwarding hook. Brain listener reported 21 names and 61 tokenizer tokens. | **VERIFIED** in snapshot/user listener evidence and 17 offline hint tests. A quiet-room false “Pause music” predates the newer hint; causation is unknown. Do not add more speech cues without evidence. |
| Fresh workstation | Installer uses the reviewed fresh-install baseline in `compatibility.json`, requires an already running Ollama, and prompts to download the reviewed Qwen model when missing. An existing Brain OVOS alpha stack and model are preserved. | **VERIFIED in installer code; PLANNED live acceptance.** This is portable behavior, not an exact installation of every Brain alpha package, model and private agent on every PC. |

## Corrections made during final review

- Restored Brain's actual Whisper media/writing cues to the bundled dynamic
  helper. `--check` no longer creates the Whisper state directory or lock file.
- Preserved Speech Note's previous speed and removed the temporary fast marker
  if starting the reader fails. The active-window guard remains in place.
- Added a pre-install check for missing local sources of previously installed
  Media or File Search skills. Without the old source, pip-based rollback cannot
  reinstall that previous package. The check stops before staging V3 and is
  listed in the deployment manifest. Existence alone cannot promise that an
  old package will reinstall; keep its installer until host rollback is tested.
- Corrected the published-release shell example so its version placeholder is
  an explicit variable and quoted filenames can be pasted safely.

## Offline verification

**VERIFIED:** `scripts/validate_refactor.py` passes 31 Python modules,
94 reviewed intents, 1,924 vocabulary registrations, four profiles and 17
packaged helpers. `scripts/test-deployment.sh` passes isolated fresh install,
upgrade preservation, failure recovery and rollback. The V3 routing/GUI checks,
Speech Note 2×/failure check and 17 Whisper tests pass. Every local Markdown
link in README and docs resolves. `scripts/build-release.sh` built a local
`3.0.0` archive with both plugin packages, the Whisper helper, the rollback
preflight and this audit; its `.sha256` sidecar verifies its final bytes.
These tests use isolated homes or offline imports and do not certify a real
desktop session, microphone, OVOS services or external media provider.

## Release decision and unresolved checks

**Publication authorised with known limits:** the owner confirms the two
plugins work after the older Brain snapshot, which does not itself verify their
upgraded installation. On Brain and the i7 laptop, still test a full V3
upgrade/rollback, the combined tray and GUI update button, Whisper recognition,
wake word, Bella, Qwen command → question → command and i7 latency, and spoken
Speech Note 2×/speed restoration/interruption. Repeat plugin voice checks on
the other computer. The older OCP/NPR unsolicited `skill.error` remains an
unresolved separate OVOS issue; supplied logs identify the failure path but
not the requester. The Brain's installed OCP and extractor edits remain outside
this Jarvis installer. Publication does not mark these checks as passed.

**Proposed meaningful deletions:** none in this final source pass. The
superseded 2.3.1 README and earlier V3 draft remain in `docs/history/`. Their
two-icon description is historical; it is not presented as the current tray.
No security decision or unresolved issue was removed. See the
[decision log](12-decisions.md) and [installer details](07-installer-updates.md).
