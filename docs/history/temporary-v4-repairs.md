# Retired temporary V4 repairs

The owner authorised removal of these five one-off delivery scripts from the
current source on 6 October 2026. Their fixes are maintained in normal Jarvis
code. The scripts and their original tests remain in
[the immutable pre-cleanup tree](https://github.com/evok3dx/OVOS-Commands/tree/86d58c05298fe94330270569b638399c3cd69cca/scripts)
and unchanged historical release assets; Git history is not rewritten.

| Retired helper | Issue and solution | Maintained outcome |
|---|---|---|
| `apply-v4-lifecycle-fix.py` | Isolated startup/control readiness and direct Media routing needed guarded source corrections; the helper required stopped workers, known hashes and rollback on failed local registration. | The corrected control/worker and browser/Media paths shipped in stable V4; their current readiness, routing and lifecycle regressions remain. |
| `apply-v4-final-fix.py` | The cumulative V4 trial needed GUI action colours, CLI progress and queued Music/browser-search corrections. The handover installed only reviewed files and preserved settings/runtime policy. | Stable 4.0.0 incorporated the corrections; maintained GUI, installer, search and deployment tests remain. |
| `apply-v4-weather-fix.py` | Named-city Weather could use home coordinates; Media could later report a false handler timeout. The correction used per-request coordinates, completed handler feedback and measured Weather stages. | Stable V4 contains the fixes. Provider latency was measured, not claimed eliminated; current Weather and Media regressions remain. |
| `apply-v4-media-timing-fix.py` | Music could open too soon after finding a result. The correction added a cancellable three-second transition, preserving queued searches, immediate acknowledgement and Stop. | Media 0.3.5 and its maintained timing/cancellation tests retain this behaviour. |
| `apply-gui-update-lock-fix.py` | The 4.0.1/4.2.0 GUI held a control lock needed by its installer/recovery. The repair separated update and service-control locks and rejected pending recovery or unknown source. | Fixed in 4.2.1. Current isolated-update/recovery regressions remain; a reviewed legacy repair is still available from unchanged history or the 4.2.1 archive. |

Detailed original verification and unresolved live limits remain in the
[release ledger](../releases.md). Current instructions live in
[troubleshooting](../troubleshooting.md#isolated-gui-update-lock-conflict).
Retiring the delivery scripts also retires their script-only rollback test and
the two dedicated GUI-patch workflows; it does not remove production recovery,
isolation, privacy, routing or behaviour tests.

These historical helpers accept narrow source identities. Do not apply them
to a current or unknown deployment. If an older installation needs its exact
repair, deliver the reviewed historical copy privately with its SHA-256 and
preserve the original recovery, ownership and stopped-worker checks. New
temporary deliveries follow [AGENTS.md](../../AGENTS.md), rather than adding
another public one-off patch.
