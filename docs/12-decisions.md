# Decisions and constraints

**VERIFIED** means code or a recorded machine test supports the claim.
**PLANNED** means agreed intent with no completed implementation.
**HISTORICAL** retains older context without presenting it as current.
Contradictions stay visible in the [living audit](v2.4-audit.md).

| Decision | Why and limits | Revisit when |
|---|---|---|
| Preserve installed voice stack on Jarvis upgrades | Brain and laptop have different working OVOS versions; replacing either speech stack could break wake word, Bella or Whisper. Fresh-install pins remain in `compatibility.json`. | A separate upgrade has an exact tested migration and rollback. |
| Require the reviewed local Qwen model for V3 guided installation | A model helps with varied phrasing but must not choose arbitrary shell, keys or disabled apps. Prompt before downloading a missing model; preserve an installed model and existing timeout. Reuse local Ollama; no new listener port. An absent Ollama service or different saved model stops for review. | The older i7 fails a real latency or safety test and a different routing profile is approved. |
| Bundle Media and File Search as separate local OVOS skills | The final Brain snapshot contains integrated Media and file-search 0.1.9. Supplied reviewed packages separate bounded title routing and read-only filename search from core commands. Keep core's action allowlist and one current GUI command source. | Live upgrades fail Brain/laptop acceptance or the packages' dependencies become excessive. |
| Keep Brain media on `ovos-audio` OCP | The experimental standalone `ovos-media` trial caused queue/control instability; provider/extractor access to YouTube is intermittent. A later repeated Common Play `skill.error` remains unresolved and blocks release verification. | Upstream daemon and providers pass end-to-end playback on both machines. |
| One tray icon and native GTK Control Centre | Service, update and Jarvis microphone state fit together; avoid a second polling icon or local web server. | GTK becomes unavailable on supported hosts. |
| Keep private Brain helpers outside managed release paths | Machine-specific code and secrets should survive portable Jarvis updates. | A helper becomes a reviewed cross-machine capability. |
| Match the installed Brain Whisper prompt without expanding its cues | The final installed helper includes dynamic app names and a short media/writing list. Match that reviewed behavior in the candidate and test the plugin source exactly. A false “Pause music” event was recorded before the newer hint, but its cause is unknown. | A measured recognition or false-trigger result supports a narrower prompt; do not add commands speculatively. |
| Stop if an older plugin's local installer source is missing | The current rollback reinstalls the prior Media/File Search package from pip's recorded direct URL. A deleted local source would leave rollback incomplete after an upgrade. Check its presence before changing Jarvis. | A self-contained backup of the exact prior wheel or a tested different rollback mechanism is implemented. |
| Publish V3 with documented remaining machine checks | The owner confirmed both new plugins work and expressly requested publication. Keep the older unrelated OCP/NPR error, i7 latency, and full live upgrade/rollback checks visible; source and isolated tests do not prove those paths. | A live check exposes a regression; prepare a small corrective release and update the evidence. |
| Documentation reflects evidence | Code/tests describe behaviour; this log records intent. Preserve unresolved requirements and show proposed deletions before removing them. | A verified source revision supersedes a documented decision. |

**HISTORICAL:** the original 2.3.1 fresh-install pins still describe the
previously reviewed baseline. They do not describe the Brain's upgraded media
and alpha voice stack. The broader five-reviewer model design belongs outside
this desktop-control release until there is an actual integration requirement.
