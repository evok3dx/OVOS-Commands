# V4 service isolation candidate

**Status: implemented and tested as a source candidate; live enforcement and
full V4 acceptance remain open. No laptop migration has been performed.**

The owner-supplied v2 experiment passed temporary system-manager filtering.
External IPv4/IPv6 TCP timed out and direct DNS/UDP was denied only in the
restricted round. Controls before/after and existing bus/Ollama TCP worked.
Every temporary worker verified ordinary-user identity, empty effective
capabilities, NoNewPrivileges and its expected cgroup; cleanup completed.
The ineffective user-manager v1 method is rejected. Do not repeat that
experiment instead of implementing and testing actual services.

The supplied v2 report is immutable historical feasibility evidence. Its
collector hash is `471b0acfcca5a67097065fd7648cd5355d1ca9de688c65e314d9f07c20af15ea`.
The later workspace reset removed that collector's source/archive and later
commits. They must not be reconstructed under the same fingerprint. The new
actual-worker collector identifies itself separately as version 3.

## Process boundaries

| Component | Candidate ownership | Remaining evidence |
|---|---|---|
| Core, listener, audio | Three static system-manager units, ordinary desktop UID/GID, no capabilities, NoNewPrivileges; deny any IP except `127.0.0.1` and `::1` | Actual cgroup IPv4/IPv6/UDP and application/voice acceptance |
| Weather | Reviewed standalone Weather plugin; fixed Open-Meteo forecast and Nominatim city/reverse/details operations | Actual plugin/cache/city/failure compatibility |
| Media | Existing separate plugin, standalone ordinary-user worker with network access | Search/play/MPRIS and browser handoff acceptance |
| Desktop apps | Existing fixed GIO/Flatpak launcher through the user session manager | Cold/warm Brave, Zoom, reading, writing and File Search |
| Ollama | Separate network-only drop-in candidate for the existing ordinary-user system daemon | Actual daemon policy, cgroup denial, local inference and recovery |
| Updater | Existing manually approved user-space HTTPS path outside restricted workers | Exact full runtime artifact, live stage/update/rollback |

The core's process-local configuration overlay blacklists the known hosted or
network-backed skills and removes known common-query, persona and OCP stages.
It retains native intents, reviewed Media handoffs and local Qwen. Unknown
settings and the user's disk configuration are preserved. Custom enabled
skills/stages still require review; unclassified network code may stall even
when the kernel prevents direct traffic. Standalone workers retain explicit
user-disabled skill choices. Local Whisper and PhōnNX are required.

Weather validates fixed HTTPS URLs and operation-specific parameters. It
disables redirects, proxy inheritance, authentication, cookies and custom
transport hooks, requires TLS verification, limits decoded replies to 2 MiB,
and bounds each request with connect/read limits and a 14-second child timeout.
Only public weather/location requests leave that helper. This adapter is not
a sandbox against malicious same-user plugin code.

## Prepare and review before native changes

First install the verified full runtime and candidate code through the reviewed
staged path. Isolation preparation requires complete version parity and the
private installation receipt, including the ONNX-only wake plugin and NumPy 2.
The complete rebuilt runtime and adopted policies pass ordinary-user CI; actual
laptop installation and activation remain unverified. Do not install a guessed
wheelhouse or use the source-build experiment as release proof.

After stopping Jarvis, prepare private candidate data as the ordinary user:

```bash
"$HOME/.venvs/ovos/bin/python" \
  "$HOME/.local/src/ovos-skill-jarvis-dispatcher/scripts/prepare_core_isolation.py" prepare
```

The command prints a new private candidate directory under
`~/Downloads/jarvis-v4-isolation-candidates`. Inspect its units,
manifest and `REVIEW.md`. It changes no service, firewall or login setting.
The generated administrator commands install root-owned service **data only**.
Never sudo Python, pip, extraction, repository code or a whole generated script.

The exact-account polkit rule permits only start/stop/restart for the five
static candidate units. It grants no enablement, property changes, generic
transient units, arbitrary command, group privilege or root Python execution.
The units have no boot-enable section and bind to the existing user manager.

After native data is separately reviewed and installed, activation verifies
the root-owned unit contents/identity, public rule checksum, account, current
source hashes and stopped state. Some systems hide `rules.d`; the helper uses
only fixed native stat/checksum commands with cached owner sudo authorisation.
It never reads a password. Activation writes three exact user compatibility
drop-ins, the X11 session environment and a private mapping receipt, then reloads
the user manager. Failed activation restores those files. Voice remains stopped.

Run/Stop, microphone, restart and GUI readiness query/control the physical
workers. General separates quiet tray login from voice-service login. The quiet
voice login refreshes session data and requests stopped workers once; tray
opens, explicit voice off and a running/muted stack stay
unchanged. Root units are not enabled at system boot. Fresh-login ordering,
audio-session access and journal visibility still need laptop acceptance.

## Actual-worker evidence

Run only after reviewed activation and starting all three workers:

```bash
"$HOME/.venvs/ovos/bin/python" \
  "$HOME/.local/src/ovos-skill-jarvis-dispatcher/scripts/verify_core_isolation.py" \
  --test-network --output "$HOME/Downloads/jarvis-v4-actual-workers.json"
```

The normal-user collector takes unrestricted before/after controls. A private,
short-lived single-use ticket authorises fixed socket tests inside each actual
worker over the existing local bus. Workers recheck identity/cgroup and report
their startup source fingerprint. It starts no service and never unmutes the
microphone. Muted/stopped/missing workers, failed controls, unavailable IPv6,
wrong source or missing local ports remain inconclusive. Reports contain safe
verdicts, not raw logs, identities, settings, credentials or transcripts.

A passing socket report does not prove Ollama, full DNS/proxy mediation,
inherited sockets, desktop functionality, positive wake recognition or
application-layer voice operation. The receipt never changes into an isolated
badge merely because it exists. The local bus and same-user desktop session
remain trusted; this is not a defence against a compromised desktop user.

## Ollama and recovery

`prepare_model_isolation.py` prepares data only after observing the existing
system daemon as a non-root process and checking its root-owned base unit. It
refuses unavailable identity or pre-existing custom IP policy. Its private
review instructions restrict only IP/accounting properties, preserving the
daemon account, executable, environment, models and CPU/GPU settings. Native
activation/restart/removal remains an explicitly reviewed owner-terminal step.
New model candidates go directly to private directories under
`~/Downloads/jarvis-v4-model-isolation-candidates`. Existing private-state core
and model candidates remain supported; do not move a candidate without updating
the reviewed native source paths. Model pulls will be blocked while that network policy is enforced. No extra
Ollama control privilege is granted. Actual daemon evidence remains required.

Stop workers, then normal-user deactivate the exact reviewed core candidate.
Deactivation verifies only owned data, clears stopped compatibility relays,
removes its exact drop-ins/receipt/session and restores them if reload fails.
It remains available when worker source is damaged. Then use the reviewed
native removal commands for the five units and rule, and any owned Ollama
drop-in. Install, rollback and uninstall refuse active or remaining native
isolation files. They never silently leave rules referencing removed code.
Settings, models, unrelated drop-ins and login choices remain intact.

See [V4 acceptance](v4-acceptance.md) and the current [release record](releases.md).
Primary implementation references: [OVOS standalone skills](https://openvoiceos.github.io/beta-technical-manual/composable-deployments/),
[systemd IP policy](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html),
and [systemd D-Bus authorisation](https://www.freedesktop.org/software/systemd/man/latest/org.freedesktop.systemd1.html).
