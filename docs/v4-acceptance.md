# V4 laptop acceptance and dependency handover

Status: **owner-authorised stable V4 publication** using existing passed source,
recovery and clean-copy checks plus exercised laptop results. See
[release record](releases.md) for the current evidence and explicit limits.
No additional laptop tests are requested for this release.

Completed evidence includes full 296-package pins/hash installation with zero
exemptions, scoped actual core/listener/audio/Ollama IPv4/IPv6 controls, exercised
reading/writing/clipboard/window/weather actions, startup/lifecycle controls and
the accepted three-second post-result music transition.

Full acoustic/real-model 350-case coverage, all GUI/Zoom/login/focus variants,
weather interruption, mediated/inherited socket/native recovery acceptance,
Hermes permissions and owner account/repository protections remain unverified.
Production signing, city-time/web-answer restoration, Flatpak and full fresh-OS
model offline installation are deferred. These are limits, not passing tests.

## Historical acceptance procedure

The sections below preserve earlier candidate collection and prototype steps.
Their old blocking statements describe those historical checkpoints; the stable
scope decision above supersedes their publication instruction. They are not
new requests to rerun successful probes or rebuild the working runtime.

## First checkpoint: read-only laptop evidence

**Received and closed for feasibility:** the supplied version-2 capability
report and temporary system-manager probe have been assessed. Preserve them
unchanged; do not ask for the identical probe again. The workspace reset lost
the current v2 checker/probe source and ZIPs. The unversioned handover restored
with the checkout is older and must not be described as the reviewed v2 artifact.
The commands below describe that earlier collection step, not a new requested
laptop action. Actual-service acceptance uses the distinct version-3 collector
described in [the isolation candidate](core-isolation.md).

Use the small `jarvis-v4-laptop-check.zip` handover, which contains only the
read-only tools and reviewed manifests. Extract it in Downloads and run as the
normal desktop user:

```bash
unzip -n "$HOME/Downloads/jarvis-v4-laptop-check.zip" -d "$HOME/Downloads"
"$HOME/.venvs/ovos/bin/python" "$HOME/Downloads/jarvis-v4-laptop-check/scripts/v4-laptop-check.py"
```

Share `Downloads/jarvis-v4-laptop-check.json` after reviewing it. It contains
full package pins and safe non-index source identities, reviewed-version
mismatches, user-service state and system-level Ollama state, literal bus/voice
settings as booleans, Hermes sandbox/socket indicators, and the configured
Qwen digest when the fixed loopback API supplies one, and voice/tray login
enablement plus the saved auto-start preference. It excludes raw URLs,
configuration, hostnames, addresses, paths, credentials and model names. It
never installs, restarts, loads models or contacts an external service. Loopback
requests use no proxy and refuse redirects. Missing capabilities remain
unverified rather than aborting the entire report. An existing output is never
overwritten; choose a fresh `--output` filename when repeating.

The report is inventory, not live voice, packet-level isolation, effective
merged OVOS configuration or upstream model authenticity. If needed, run the
strict standalone capture from the Jarvis checkout:

```bash
~/.venvs/ovos/bin/python scripts/dependency-lock.py capture --output /tmp/jarvis-v4-runtime.json
python3 scripts/core-isolation-preflight.py
```

The capture contains package names/versions and target identifiers only. It
excludes environment values, credentials, configuration, paths, hostnames and
messages, and creates a private file without overwrite. It must match the
reviewed pins and include the actual tested yt-dlp version. If it stops, review
the mismatch; do not install a guessed version just to pass. This first step
does not install, restart or enable anything. Share the capture and the small
preflight result for the next implementation pass, after reviewing them.

## Complete hashed wheel candidate

**VERIFIED rebuilt candidate:** run `36765769244` passes complete 296-package
hash-enforced offline and staged installation, three first-party plugin imports,
real ONNX silent-frame inference and final archive-byte verification. The exact
new wheel lock, artifact manifest and bundle policy are adopted in the source
candidate after independent proof-digest and unchanged metadata/version checks.
The nine source-built wheel hash differences remain explicit in
`voice/runtime-rebuild-evidence.json`. NumPy 2.4.6 and zero exemptions remain.
This closes runtime recovery and candidate hash installation; actual laptop
voice, models, service isolation and staged switch/recovery remain open.

The candidate installer accepts `--runtime-wheelhouse PATH` to install this
verified closure into its unpublished stage. It rechecks staged bytes and the
exact lock, disables indexes/dependencies/source builds, requires complete
installed parity and rejects a live virtualenv as its target. A missing or
altered wheel stops the transaction without online fallback. Source installation
requires explicit `--runtime-source-build` for investigation; it is not the
full-hash release mode. Default installation requires a separate code-pinned
bundle; `--runtime-bundle PATH` supplies a reviewed local copy. The restored
builder verifies packaged bytes and private staging on real fixture wheels.
Use the exact reviewed rebuilt archive and its matching canonical policies for
live stage-switch/model tests. Do not rerun resolution or rebuild merely to
repeat already successful candidate checks.
Keep the code updater's 100 MB extraction limit unchanged.

Use a private workspace and the complete capture. Do not substitute the
incomplete direct-package manifest for a full runtime inventory.

1. Generate inputs with `scripts/dependency-lock.py inputs --inventory CAPTURE
   --output INPUTS`. It retains the reviewed PhōnNX source commit/archive hash
   and spaCy model wheel hash. All captured packages have exact versions.
2. Use a reviewed uv build tool to compile hashes for **those exact pins** with
   `uv pip compile --no-deps --generate-hashes --python-version 3.11
   --python-platform x86_64-unknown-linux-gnu --output-file HASHED INPUTS`.
   `--no-deps` prevents the resolver from substituting NumPy 1.x; it does not
   excuse missing transitives. The later wheel-closure check supplies that gate.
3. Build/download wheels into an empty private wheelhouse using the reviewed
   build interpreter and `python -m pip wheel --no-deps --no-build-isolation
   --require-hashes -r HASHED --wheel-dir WHEELS`. Record that interpreter's
   complete build-tool pins. Missing build dependencies or native headers must
   stop for review; never fall back to unpinned build isolation or root pip.
   OS/compiler prerequisites are host compatibility, outside the OVOS lock.
4. Run `scripts/dependency-lock.py wheel-lock --inventory CAPTURE --wheelhouse
   WHEELS --output LOCK`. It checks complete inventory parity, wheel identity,
   hashes, platform, transitives and requested extras. Every conflict fails;
   the V4 candidate retains NumPy 2 with the reviewed ONNX-only downstream wake
   plugin and has no metadata exemption. Preserve its
   artifact manifest and the separate original laptop capture. Build the
   separately versioned plugin from `extras/ovos-ww-plugin-openwakeword-onnx`
   with the hashed build tools, `--no-index --no-deps --no-build-isolation
   --no-cache-dir` and its recorded `SOURCE_DATE_EPOCH`; include that wheel in
   the complete wheelhouse before closure validation. Its repository source
   fingerprints and upstream source identity are in `PROVENANCE.json`.
5. Use the captured Python patch version to run the fail-closed disposable probe:

   ```bash
   ~/.venvs/ovos/bin/python scripts/probe-offline-runtime.py \
     --inventory CAPTURE --wheelhouse WHEELS --lock LOCK --output RESULT
   ```

   It copies wheels into private staging, rechecks complete closure and every
   hash against the exact lock, then creates a disposable environment. Tampered
   wheels or injected requirement options stop before installation. The
   install uses no index, dependency resolution, cache or source build, and
   reports full installed inventory parity separately from local ensurepip
   bootstrap tools. It checks the reviewed versions, dependencies, entry points
   and launchers, then removes the disposable environment. This mechanism and
   a real offline fixture-wheel install pass. The full 296-package laptop
   wheelhouse now also passes this probe; live native ABI/model acceptance and
   production staged-installer hash enforcement remain required.

   The underlying install is
   `python -m pip install --no-index --find-links WHEELS --no-deps
   --require-hashes -r LOCK`. A deliberately altered wheel must be rejected.
   No online fallback, dependencies, source builds or edits to the live venv.
6. Separately test model inference and the Adapt/native routing probe in an
   isolated environment that has passed the same install checks. Record build-tool
   provenance separately; final wheel hashes do not freeze unrecorded build inputs.
7. Run the separate bundle builder and stage verifier against that complete
   validated wheelhouse. Confirm packaged byte identities and the full runtime
   install/parity checks. Then test the unpublished staged installer and its
   receipt, switch/recovery and live voice behaviour. A receipt records hash-
   enforced installation; it does not prove current installed-file integrity.
   Until all gates pass, the existing laptop deployment remains and V4 is blocked.

Embedding a reviewed wheelhouse is feasible but affects archive size, licences
and platform support. The current updater has a 100 MB safety limit; do not
raise it blindly or bundle native dependencies/models into its code archive.
Use a separately validated distribution/bundle if the wheelhouse exceeds it.
Flatpak and a full offline installer remain later projects.

## Managed sources and model identity

PhōnNX, the bootstrap source and spaCy model already have source/artifact hashes
in `compatibility.json`. The model acceptance pass must record the installed
Hey Jarvis, Whisper, Bella and Qwen identities against reviewed upstream
revisions/digests where supported. Verify files before loading; a local baseline
alone is not upstream authenticity. Preserve existing caches and user choices.
Mutable tags remain labelled tag-pinned, never hash-verified. No new model
revision or digest is guessed in this candidate.

## Core isolation acceptance

The preflight is inventory, never proof that a service rule works. The supplied
temporary comparison rejects user-manager filtering and passes system-manager
feasibility. It does not prove actual OVOS or Ollama enforcement. No laptop
service isolation has been enabled by this work.

The source candidate separates Weather/Media and blacklists known network-backed
skills/stages in the core's process-local configuration. Review custom enabled
skills and the actual provider before activation. Follow the private review,
ordinary-user activation and owned removal path in [core isolation](core-isolation.md).
Keep the runtime artifact prerequisite explicit. For actual-service acceptance,
review actual provider/configuration without exporting secrets. Keep fixed
desktop handoffs to Brave, Zoom and the updater outside restricted cgroups so
they do not inherit the core's network denial. Do not blanket-block the desktop
user, add a permanent privileged daemon or guess provider permissions.

For each service, require failed external IPv4/IPv6 and applicable UDP/DNS probes,
working loopback/messagebus/Ollama, process-specific socket/packet evidence,
working wake/STT/TTS, File Search, reading/writing, browser/music and weather.
Test rule removal, update and rollback before claiming **Core isolated**.

## Other acceptance gates

- GTK desktop: wide/narrow cards, long-guide/banner bounds, accessible icons,
  successful/unchecked/offline update states, Copy rule clearing and Results space.
- Commands: native phrase tests and a separate 350-case **real Qwen** run using
  `scripts/routing-benchmark.py`; no actions are dispatched. Live microphone,
  typing, selected-text reading/2× and window focus need separate tests.
- Zoom: visible, native/Flatpak tray-only and cold-start identities. Feedback is
  implemented; no speculative tray clicking, kill or unsupported switch.
- Agents: actual private helper permissions and tool access in Hermes/Claude
  Desktop. Preserve normal desktop capture unless evidence requires confirmation.
- Hermes: review Podman socket access and test sandbox restoration on the real
  installed build. The current launcher exception is unchanged pending evidence.
- Signatures: the disposable Minisign prototype passes, but production keys,
  bootstrap trust, client verification, rotation/recovery, install/update and
  rollback must pass before adopting signing. Keep private keys off the repository.
- Owner/repository settings: review the agreed account and GitHub policy tasks;
  ask for approval immediately before individual settings changes. No account
  credentials or settings were read or changed during this source pass.

The three dependency stages remain V4 work. If full hashes or core isolation
cannot pass safely, the owner must decide **delay V4** or **accept the precisely
documented exception** before release. Elapsed time and successful unit tests
do not constitute that decision. Do not mark final 4.0.0, install live, tag, push
or publish a stable release until the relevant gates and immediate approval pass.
The owner has separately authorised the named 4.0.0rc1 laptop test prerelease,
with the exact verified runtime and these live checks explicitly outstanding.
Production signing is deferred for the one-client test. See the
[test release instructions](v4-laptop-test-release.md); this testing approval
does not certify live isolation or silently waive remaining stable acceptance.
