# Jarvis V4 laptop test: 4.0.0rc1

Owner-authorised **prerelease for laptop testing**. The stable update channel
remains 3.9.0. This release includes the complete separately downloaded,
hash-verified Linux x86_64 / Python 3.11 runtime. NumPy remains 2.4.6; the ONNX-only
wake plugin has no dependency exemption. It preserves existing configuration,
application choices, models, shortcuts and explicit auto-start preferences.

Automated checks cover routing, safe writing, temporary clipboard clearing,
transactional deployment and rollback. Reading has distinct **Speak selected
text** and **Speak highlighted text** alternatives. Real microphone confusion
between “read” and “write” still needs a laptop test; writing is not remapped.
The GUI provides separate auto-start-at-login and current Run/Stop controls.

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
immutable, hash-verified guard hotfix below before installation. `sudo -v`
authorises only the subsequent fixed native metadata check; Python and the
installer remain the normal desktop user. Existing native isolation policy
still blocks deployment and must be reviewed separately.

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
jarvis_hotfix_url='https://raw.githubusercontent.com/evok3dx/OVOS-Commands/5280ae9339584da040e5d1e4caff21abc1043c4e/scripts/isolation_services.py'
curl --fail --location --proto '=https' --proto-redir '=https' \
  "$jarvis_hotfix_url" -o scripts/isolation_services.py.hotfix || exit 1
printf '%s  %s\n' 563ceb016f71a3207f0e940d3168796a2447758ee2913a2dfe81235dcf2dc456 \
  scripts/isolation_services.py.hotfix | sha256sum --check - || exit 1
chmod 0755 scripts/isolation_services.py.hotfix
mv -- scripts/isolation_services.py.hotfix scripts/isolation_services.py
sudo -v || exit 1
bash scripts/install.sh --no-speechnote
```

The installer obtains the separate approximately 454 MB runtime asset and
checks its code-pinned digest and every wheel before installation. Retain the
installer output privately. If the deployment guard reports remaining native
isolation policy, follow the reviewed removal instructions before updating;
do not disable the guard.

After installation, open the Control Centre and confirm the installed version,
Run Jarvis, test normal commands, and choose Auto-start at login if wanted.
Test one fresh login separately. Run `jarvis-health-check` and report any failure
without posting raw logs or credentials publicly. Rollback is available through
`jarvis-update rollback`; native isolation must be deactivated first if enabled.
