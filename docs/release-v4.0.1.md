# Jarvis 4.0.1

## Changes

- Guided optional isolation, recommended for new installs; upgrades preserve existing choices.
- Dedicated local Ollama and a private verified Qwen copy; general Ollama is unchanged.
- Safer isolated upgrade/recovery, corrected worker startup and exact source restoration after package builds.
- Saved isolation choices in private exports and private-only model removal.

## Verification

All six CI jobs passed, including clean-archive recovery, 350 policy cases and
all 296 hash-verified dependencies. Supplied laptop recovery, installation and
readiness passed with zero health-check failures or warnings.

Dedicated-model generation and IPv4/IPv6 egress checks are accepted for testing
after release. Signing and complete offline fresh-machine setup remain deferred.
Media stays 0.3.5 and File Search 0.3.0.

See the [release record](https://github.com/evok3dx/OVOS-Commands/blob/main/docs/releases.md),
[upgrade guide](https://github.com/evok3dx/OVOS-Commands/blob/main/docs/07-installer-updates.md)
and [security notes](https://github.com/evok3dx/OVOS-Commands/blob/main/docs/security-and-updates.md).
