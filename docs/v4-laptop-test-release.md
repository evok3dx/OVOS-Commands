# Jarvis V4 laptop test: 4.0.0rc1

**Historical guarded handover:** stable 4.0.0 now includes these changes.
Use [current release notes](release-v4.0.0.md) for installation and limits;
keep the original prerelease/patch instructions below for their exact versions.
RC1/RC2 release cards are now retained as drafts. Their old public download
commands are historical; install from the stable V4 release instead.

Owner-authorised **prerelease for laptop testing**. The stable update channel
remains 3.9.0. This release includes the complete separately downloaded,
hash-verified Linux x86_64 / Python 3.11 runtime. NumPy remains 2.4.6; the ONNX-only
wake plugin has no dependency exemption. It preserves existing configuration,
application choices, models, shortcuts and explicit auto-start preferences.

Automated checks cover routing, safe writing, temporary clipboard clearing,
transactional deployment and rollback. Reading has distinct **Speak selected
text** and **Speak highlighted text** alternatives. Real microphone confusion
between “read” and “write” still needs a laptop test; writing is not remapped.
The updated source GUI labels Overview as Dashboard and puts independent tray
and voice-service login options in General, separate from current Run/Stop.
The frozen prerelease archive predates that refinement; use its matching source
update rather than expecting the initial single-file picker fix to add General.

**Not yet verified on this laptop:** startup after a fresh login, positive wake
and microphone behaviour, selected-text reading and typing/focus, actual
OVOS/Ollama isolation and model identities. Installing this candidate does not
activate the reviewed native isolation policies automatically. See
[V4 acceptance](v4-acceptance.md) and [core isolation](core-isolation.md).
Do not claim that the installed core is internet blocked until that separate
activation and actual-service verification pass.

The installer brings Jarvis/OVOS dependencies and local voice models. It uses
the existing Ollama installation. It does not install Hermes, Claude, Codex or
other agent platforms. Speech Note setup is optional and requires approval;
the command below keeps the current application installation.

Brave's expired music sessions remain an accepted limitation: reopen the tab or
request another song. Response speed as in 3.9 is accepted; no GPU tuning is
required. Production signing is deferred by the owner for this one-client test;
checksums verify bytes, not publisher identity. Native notices and the remaining
broader-redistribution review are recorded in `RUNTIME-NOTICES.md`.

## Install as your normal desktop user

Close the Control Centre before updating. Do not run the installer with sudo.
Download and verify the explicit prerelease; the ordinary GUI update channel
continues to offer stable releases only.

The initial archive has a guard bug on protected polkit directories. Apply the
immutable, hash-verified, password-free guard hotfix below before installation.
It checks the exact native worker states without sudo or an authentication
prompt. Active receipts, installed/loaded workers, visible rules and Ollama
policy still block deployment. A hidden rule is not assumed missing: every
fixed worker must be not-found/inactive with no fragment or drop-ins. Native
isolation setup/removal remains a separate administrator operation.

A second small hotfix makes exact reviewed prerelease verification independent
of the existing host's packaging version. It changes no runtime pins, hashes,
constraints or dependency exemptions. A third fixes GUI restoration of saved
default-app labels after icon rows were added; it changes no saved choice.
All three fixes below are needed with the original frozen release archive.
At `Review application selection now? [y/N]`,
press Enter to keep existing app choices; selecting `y` intentionally opens setup.

```bash
test "$(id -u)" -ne 0 || exit 1
mkdir -p "$HOME/Downloads"
jarvis_test_dir="$(mktemp -d "$HOME/Downloads/jarvis-v4-test.XXXXXX")"
cd "$jarvis_test_dir" || exit 1
jarvis_test_url='https://github.com/evok3dx/OVOS-Commands/releases/download/v4.0.0rc1'
curl --fail --location --proto '=https' --proto-redir '=https' \
  "$jarvis_test_url/ovos-commands-4.0.0rc1.tar.gz" -o ovos-commands-4.0.0rc1.tar.gz || exit 1
curl --fail --location --proto '=https' --proto-redir '=https' \
  "$jarvis_test_url/ovos-commands-4.0.0rc1.tar.gz.sha256" -o ovos-commands-4.0.0rc1.tar.gz.sha256 || exit 1
sha256sum --check ovos-commands-4.0.0rc1.tar.gz.sha256 || exit 1
tar -xzf ovos-commands-4.0.0rc1.tar.gz || exit 1
cd ovos-commands-4.0.0rc1 || exit 1
jarvis_hotfix_url='https://raw.githubusercontent.com/evok3dx/OVOS-Commands/ee07b82d1d50a9edaa25c43d7a8dff351f1ad2c7/scripts/isolation_services.py'
curl --fail --location --proto '=https' --proto-redir '=https' \
  "$jarvis_hotfix_url" -o scripts/isolation_services.py.hotfix || exit 1
printf '%s  %s\n' cd217b562dee0c635dfb16a46233a2d913045f606f387ce3fcd782787a646231 \
  scripts/isolation_services.py.hotfix | sha256sum --check - || exit 1
chmod 0755 scripts/isolation_services.py.hotfix
mv -- scripts/isolation_services.py.hotfix scripts/isolation_services.py
jarvis_dependency_fix='https://raw.githubusercontent.com/evok3dx/OVOS-Commands/8df0002e2aa3e57b0e178681827bb648933376c6/scripts/dependency-lock.py'
curl --fail --location --proto '=https' --proto-redir '=https' \
  "$jarvis_dependency_fix" -o scripts/dependency-lock.py.hotfix || exit 1
printf '%s  %s\n' 8b032f679e1c3ac87305e7f4fbbfc8e902b54797dd523c738b997a6848d433c5 \
  scripts/dependency-lock.py.hotfix | sha256sum --check - || exit 1
chmod 0755 scripts/dependency-lock.py.hotfix
mv -- scripts/dependency-lock.py.hotfix scripts/dependency-lock.py
jarvis_gui_fix='https://raw.githubusercontent.com/evok3dx/OVOS-Commands/0c705c77f357bf5c1a803094cc9c9aa4c8caa7c6/scripts/setup.py'
curl --fail --location --proto '=https' --proto-redir '=https' \
  "$jarvis_gui_fix" -o scripts/setup.py.hotfix || exit 1
printf '%s  %s\n' 059510eeed465406325615344e72feac323a809a29b68d04bb82a5cfe03323f7 \
  scripts/setup.py.hotfix | sha256sum --check - || exit 1
chmod 0755 scripts/setup.py.hotfix
mv -- scripts/setup.py.hotfix scripts/setup.py
bash scripts/install.sh --no-speechnote
```

The installer obtains the separate approximately 454 MB runtime asset and
checks its code-pinned digest and every wheel before installation. Retain the
installer output privately. If the deployment guard reports remaining native
isolation policy, follow the reviewed removal instructions before updating;
do not disable the guard.

After installation, open the Control Centre and confirm the installed version,
Run Jarvis, test normal commands, and choose the required login options in
General in the updated source candidate (the initial archive has one combined
auto-start switch).
Test one fresh login separately. Run `jarvis-health-check` and report any failure
without posting raw logs or credentials publicly. Rollback is available through
`jarvis-update rollback`; native isolation must be deactivated first if enabled.
