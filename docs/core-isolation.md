# V4 service isolation

**Status: optional native isolation is implemented; scoped actual-worker and
Ollama network probes and exercised local voice/desktop functions pass. Broader
mediated/inherited socket, every desktop/login variant and native recovery
acceptance remain unverified. Stable publication does not close those checks.**

System-manager filtering is used because the earlier user-manager experiment
was not enforced on the reviewed host. Actual core/listener/audio probes cover
external IPv4/IPv6 TCP and direct DNS/UDP with unrestricted controls and working
local TCP. Separate actual Ollama evidence preserves loopback inference and
rejects external IPv4 and IPv6 traffic. Temporary feasibility alone is not proof
of actual-service enforcement. The version-3 collector remains available for
future diagnostics; no repeat is requested for this release.

## Process boundaries

| Component | Ownership | Remaining evidence |
|---|---|---|
| Core, listener, audio | Three static system-manager units, ordinary desktop UID/GID, no capabilities, NoNewPrivileges; deny any IP except `127.0.0.1` and `::1` | Scoped actual IPv4/IPv6 TCP/DNS and exercised voice pass; broader paths remain |
| Weather | Reviewed standalone Weather plugin; fixed Open-Meteo forecast and Nominatim city/reverse/details operations | Named-city/cached lookup exercised; interruption/failure variants remain |
| Media | Existing separate plugin, standalone ordinary-user worker with network access | Title search/open exercised; full queue/Stop/browser variants remain |
| Desktop apps | Existing fixed GIO/Flatpak launcher through the user session manager | Cold/warm Brave, Zoom, reading, writing and File Search |
| Ollama | Dedicated ordinary-user Jarvis daemon with private model data and kernel IP filtering; general Ollama unchanged | Local generation and actual external IPv4/IPv6 TCP denial with outside controls pass; broader paths remain |
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

## Control Centre status and checks

Dashboard shows the running state of Speech, Listener and Commands. Under
isolation these are the actual system-manager workers; inactive compatibility
user units do not mean voice is off. Run/Stop, restart and microphone controls
use that same mapping. Current readiness remains separate from logging.

Maintenance's **Isolation** card shows the configured core and private-model
network policy as **Isolation active**, **Isolation off** or **Needs attention**.
**Refresh status** inspects current native properties and the selected endpoint.
Isolation active can remain visible while Jarvis is stopped: it describes the
installed restrictions, not running services or a passed egress test.

**Check isolation** explicitly probes the current workers and dedicated model.
Start Jarvis first. The check changes no service or microphone setting, shows
stages, has a five-minute GUI timeout and writes a private timestamped
`Jarvis-Isolation-Check-YYYY-MM-DD_HH-MM-SS` folder in Downloads. Results appear
under **Results and details**. Missing workers, failed outside controls or a
timeout stay inconclusive rather than becoming a pass.

The current combined check covers worker IPv4/IPv6 TCP and direct DNS/UDP,
private-model local generation and private-model IPv4 denial. Its model IPv6
result is explicitly **NOT TESTED** because the numeric registry probe is
rejected by model-name validation. Separately recorded actual-daemon IPv6
evidence in the [release record](releases.md) does not make this GUI check test
IPv6. No broader mediated/inherited-socket or fresh-install claim is made.
Treat the generated report as private and review it before sharing.

## Guided installer (4.0.1)

New installations offer **Enable network isolation (recommended)** selected
by default. The short explanation says administrator approval is needed to block
internet access for Jarvis voice processing and its local model; Weather and
Media retain their separate online workers. Declining keeps the ordinary model
path. Unattended first installs must explicitly choose `--isolation` or
`--no-isolation`; they never silently request a password. Upgrades preserve the
existing choice without presenting the first-install question again.

Selected isolation adds only an account-specific private Ollama service on
`127.0.0.1:11435`, with its model files under user-owned Jarvis data and cloud
features disabled. The normal Ollama executable is reused. Only the reviewed
Qwen model is copied, with every manifest/blob hash verified; the general model
store and service are not modified. Jarvis never falls back to port 11434 when
its private service is unavailable. A previously installed restriction on general
Ollama remains unchanged and needs its own separately reviewed removal if wanted.

During upgrades the native IP policy and relays remain installed. A private,
process-bound journal permits only the managed install/recovery while workers
are stopped. Previous source identity and native data are restored on failure;
an incomplete recovery blocks startup instead of starting unrestricted workers.
First enablement or a native-data migration needs bounded administrator approval.
Repeated upgrades with unchanged native data do not. Worker/model execution remains
ordinary-user; the grant covers six exact units and three control verbs only.

The automated suite passes. Supplied laptop output confirms interrupted
recovery, legacy migration, private-model availability and voice readiness.
**VERIFIED post-release on 1 October 2026:** dedicated-daemon local generation
and actual external IPv4/IPv6 TCP denial pass, with unchanged daemon identity
and working outside controls before/after. All three voice workers also pass
current-source IPv4/IPv6 TCP and direct DNS/UDP comparisons with local bus/model
connections preserved. Fresh-install coverage and broader mediated/inherited
paths remain unverified. Raw reports stay private; see the
[release evidence](releases.md). Separate
instances protect the selected daemon's direct networking, not every same-user
program, mediated request or filesystem path. Reusing an installed executable
does not bundle/authenticate upstream Ollama or provide complete offline setup.

After a killed or interrupted coordinator, workers remain guarded. Use the
verified new source's `scripts/isolation_install.py -- --recover` as the desktop
user to restore the recorded previous deployment. Do not delete the journal or
run recovery with sudo. Unknown or changed native files stop recovery for review.

Download the archive and matching checksum from the stable release. Run these
as your ordinary desktop user from the download directory:

```bash
sha256sum --check ovos-commands-4.0.1.tar.gz.sha256
tar -xzf ovos-commands-4.0.1.tar.gz
cd ovos-commands-4.0.1
bash scripts/install.sh --no-speechnote
```

Existing isolation is preserved. First native-model migration asks for bounded
administrator approval; do not sudo the installer. An existing general-Ollama
restriction is left in place. Check the dedicated unit and local inference on
port 11435, then run the actual-worker collector before calling protection live
verified. The stable updater offers the published release; an older installed
updater may still require the reviewed full-installer upgrade procedure.

## Manual native review and older 4.0.0 deployments

First install the verified full runtime and release code through the reviewed
staged path. Isolation preparation requires complete version parity and the
private installation receipt, including the ONNX-only wake plugin and NumPy 2.
The complete rebuilt runtime and adopted policies pass ordinary-user CI;
installation and activation have been exercised on the reviewed laptop. Do not install a guessed
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
Ollama control privilege is granted. Scoped actual-daemon denial/local-inference evidence is recorded in the release
ledger; removal/recovery remains separate acceptance.

Stop workers, then normal-user deactivate the exact reviewed core candidate.
Deactivation verifies only owned data, clears stopped compatibility relays,
removes its exact drop-ins/receipt/session and restores them if reload fails.
It remains available when worker source is damaged. Then use the reviewed
native removal commands for the five units and rule, and any owned Ollama
drop-in. Install, rollback and uninstall refuse active or remaining native
isolation files. They never silently leave rules referencing removed code.
Settings, models, unrelated drop-ins and login choices remain intact.

For an update, use the helpers from the verified new release when older helper
APIs differ. Restore the model policy before running voice again, and prepare
a new core candidate against the installed source rather than reusing an old
source fingerprint. An exact reviewed native-file repair must be compared and
backed up; arbitrary candidate differences are not accepted. See the current
[isolated-upgrade procedure](07-installer-updates.md#upgrading-an-isolated-installation).
Successful installation does not itself prove restored isolation or live
network denial. Broader recovery acceptance remains separately scoped.

See [V4 acceptance](v4-acceptance.md) and the current [release record](releases.md).
Primary implementation references: [OVOS standalone skills](https://openvoiceos.github.io/beta-technical-manual/composable-deployments/),
[systemd IP policy](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html),
and [systemd D-Bus authorisation](https://www.freedesktop.org/software/systemd/man/latest/org.freedesktop.systemd1.html).
