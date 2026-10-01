# Jarvis 4.0.0

V4 brings the working Linux Mint/X11 voice-control stack together with reviewed
runtime hashes, clearer startup controls and optional service network isolation.
The dispatcher is 4.0.0, Media is 0.3.5 and File Search remains 0.3.0.

## Security and reliability

- Complete 296-package runtime with exact versions and enforced wheel hashes,
  zero dependency exemptions, retained NumPy 2 and an ONNX-only wake plugin.
- Optional native policy denies external IP traffic for core/listener/audio and
  Ollama while weather and browser music use separate online paths. Activation
  remains an explicit reviewed step; installation alone does not isolate core.
- Generic terminal writing/submission is blocked. Tool-capable private-agent
  prompts require readback and a single-use explicit confirmation.
- Selection reading clears its temporary clipboard text without restoring the
  previous clipboard. Support reports use private atomic publication and
  redact reviewed credential/location forms.
- HTTPS-only reviewed update hosts, bounded archive extraction and recoverable
  installation preserve settings, application choices, models and private helpers.

## Everyday improvements

- General separates starting the app minimised from starting voice services at
  login; Dashboard controls Run/Stop for the current session.
- Readiness follows actual worker replies. GUI status, icons, card layout,
  setup guide, update cancellation and CLI progress have been improved.
- Current-app window phrases and WM_CLASS targeting are consistent. Zoom's
  tray-only state receives honest feedback without restarting an active meeting.
- Music acknowledges immediately, uses the direct isolated-helper route with
  Qwen fallback, then waits three seconds after finding a result before opening.
  `Put on {title}` is an alternative to `Play {title}`.
- Named-city weather forecasts use resolved city coordinates and timezone.

## Accepted limits

Music can open another tab without stopping an earlier tab. Brave's idle-session
expiry remains outside Jarvis control. Provider requests have an 11-second
shared search gap; no timing guarantees avoidance of provider alerts.
New weather locations can take about 15 seconds; cached location lookups are
quicker. Weather Stop during retrieval remains unverified. City-time routing
and online Wikipedia/WikiHow answers are deferred and web skills remain disabled
in restricted core.

The local bus, desktop session and same-user plugins remain trusted. Full
acoustic/real-model coverage, all desktop/login variants, mediated/inherited
socket and native recovery acceptance, effective Hermes permissions and owner
account/repository protections are not certified by this release. Production
signatures, Flatpak and complete fresh-OS/model offline installation are later
work. The runtime ZIP contains wheels, not all voice/Qwen model data or OS tools.

## Install and update

Download `ovos-commands-4.0.0.tar.gz` and its matching `.sha256`. Normal setup
uses the separately hash-verified `jarvis-runtime-linux-x86_64-py311.zip` from
this release. A saved copy can be supplied with `--runtime-bundle PATH`.
Use [installation guidance](07-installer-updates.md).

An already patched laptop has the latest behaviour code. No reinstall is needed
merely to exercise the same fixes. The normal installer/updater refuses remaining
native isolation data; use the reviewed deactivation/removal path before a full
managed update. It does not silently replace active protected workers.
Original rc1/rc2 releases remain available. Source, automation and publication
evidence are recorded in [releases](releases.md).
