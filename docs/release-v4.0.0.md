# Jarvis 4.0.0

## Changes

- Hash-verified 296-package runtime, zero dependency exemptions and retained NumPy 2.
- Optional core/voice and Ollama network isolation, with separate online weather and music paths.
- Safer writing, private-agent confirmation, temporary clipboard clearing and private support reports.
- Independent tray and voice startup options, worker-based readiness, clearer GUI status and update recovery.
- Media 0.3.5 acknowledges before searching and waits three seconds after a result. `Put on {title}` is an existing alternative to `Play`.
- Named-city weather uses the requested location. File Search remains 0.3.0.

## Verification

Existing behaviour, deployment, rollback and hash checks passed. Stable packaging
verified all 11 public assets and the tag. Scoped laptop functions were exercised;
full acoustic, desktop and recovery coverage remains unverified.

New weather locations can be slow; music may leave an earlier tab playing.
Brave idle expiry remains outside Jarvis control. Signing and complete offline
fresh-machine installation are deferred. Installation alone does not activate
network isolation.

See the [release record](https://github.com/evok3dx/OVOS-Commands/blob/main/docs/releases.md),
[install and upgrade guide](https://github.com/evok3dx/OVOS-Commands/blob/main/docs/07-installer-updates.md)
and [security notes](https://github.com/evok3dx/OVOS-Commands/blob/main/docs/security-and-updates.md).
