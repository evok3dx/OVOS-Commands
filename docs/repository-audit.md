# Repository audit and consolidation

This audit started from the validated v21 release archive and preserved its
working command behaviour as the regression baseline.

## Findings

- Twenty-two one-feature installers accumulated as successive patches. Many
  copied overlapping subsets of the same modules and helpers.
- Compiled Python cache files were included in the release.
- The main README referenced missing microphone, tray, recovery and
  conversation files.
- Current and historical guides were mixed at the repository root.
- `ReadFullPageIntent` duplicated `ReadVisiblePageIntent`; both called the same
  local reader.
- Deployment inventories were repeated manually across shell and Python.
- The main installer backed up files but offered no single rollback command.

## Changes

- Replaced feature-patch installers with one manifest-driven installer.
- Retained the old deployment filename as a compatibility wrapper.
- Added preflight, complete backups, explicit rollback and release packaging.
- Made the manifest the shared inventory for installation and validation.
- Merged all full-page wording into the universal reading intent without
  removing a spoken phrase or changing its action.
- Restored the optional tray icons and microphone indicator files described by
  the repository, with separate installers.
- Added CI across supported Python versions, archive inspection and a weekly
  compatibility check against current OVOS APIs.
- Added transactional failure recovery, a portable profile, read-only health
  checks and a privacy-bounded AI support report.
- Replaced visible profiles with detected all/core/custom capability setup.
- Added tray setup, health, report and supervised update entry points.
- Added OS-default Mail, ChatGPT Desktop and explicit Claude/ChatGPT websites.
- Removed private agent helpers and vocabulary from normal installation.
- Moved implementation reports to `docs/history/` and rewrote current guidance.
- Excluded caches, logs, secrets, local configuration and release output.

## Compatibility retained

- Existing Brain-specific agent vocabulary can remain active only when an
  already-customised legacy Brain profile is migrated.
- Every enabled application alias has open, focus, minimise, maximise and close
  coverage.
- Hermes rootless Podman isolation and secure launcher repair.
- The accessibility-first local reader and clipboard fallback.
- Confirmation, timeout and focus-verification boundaries.
- Legacy profiles remain validated migration inputs, not setup choices.

Hard-coded executable paths in helpers are intentional allowlists for the
tested Linux Mint workstation, not general configuration inputs. Generalising
them into arbitrary profile commands would weaken the security boundary.
