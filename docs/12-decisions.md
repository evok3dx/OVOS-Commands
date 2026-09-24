# Decisions and constraints

**VERIFIED** means code or a recorded machine test supports the claim.
**PLANNED** means agreed intent with no completed implementation.
**HISTORICAL** retains older context without presenting it as current.
Contradictions stay visible in the [living audit](v2.4-audit.md).

| Decision | Why and limits | Revisit when |
|---|---|---|
| Preserve installed voice stack on Jarvis upgrades | Brain and laptop have different working OVOS versions; replacing either speech stack could break wake word, Bella or Whisper. Fresh-install pins remain in `compatibility.json`. | A separate upgrade has an exact tested migration and rollback. |
| Restrict optional local Qwen to reviewed actions | A model helps with varied phrasing but must not choose arbitrary shell, keys or disabled apps. Reuse existing local Ollama; no new listener port. | A different model and CPU/GPU profile pass the same voice safety and latency gates. |
| Keep Brain media on `ovos-audio` OCP | The experimental standalone `ovos-media` trial caused queue/control instability; provider/extractor access to YouTube is intermittent. A later repeated Common Play `skill.error` remains unresolved and blocks release verification. | Upstream daemon and providers pass end-to-end playback on both machines. |
| One tray icon and native GTK Control Centre | Service, update and Jarvis microphone state fit together; avoid a second polling icon or local web server. | GTK becomes unavailable on supported hosts. |
| Keep private Brain helpers outside managed release paths | Machine-specific code and secrets should survive portable Jarvis updates. | A helper becomes a reviewed cross-machine capability. |
| Documentation reflects evidence | Code/tests describe behaviour; this log records intent. Preserve unresolved requirements and show proposed deletions before removing them. | A verified source revision supersedes a documented decision. |

**HISTORICAL:** the original 2.3.1 fresh-install pins still describe the
previously reviewed baseline. They do not describe the Brain's upgraded media
and alpha voice stack. The broader five-reviewer model design belongs outside
this desktop-control release until there is an actual integration requirement.
