# Changelog

## 2.0.1

- Fixed Release updater to prefer the exact `idontMonitor-vX.Y.Z.tar.gz` asset and validate its GitHub-provided SHA-256 digest when available.
- Added a tag-archive fallback only when the release has no matching project asset.
- Hardened archive extraction against special files, traversal, and oversized expanded content.
- Made release directory creation staged and refused in-place overwrite of an existing version directory.
- Synchronizes updater, operations helper, systemd unit, and CLI version during update, with rollback backups.
- Fixed the CLI menu's stale update message and expanded usage help.
- Refuses installer in-place overwrite when the same version is already installed.
- Expanded update tests and documentation.


## v2.0.1
- Release-based updater now uses the GitHub release tag source archive (`tar.gz`) instead of requiring a ZIP asset.
- Added an explicit main-branch update path for development builds.
- Improved version consistency across source, installer, CLI, and release metadata.
- Kept safe port selection on fresh install and preserved existing port during upgrades.


## 1.9.9
- Added BackPack native metrics snapshot reader for per-instance `bytes_in` / `bytes_out` where snapshots are present beside recognized configuration paths.
- Added C-Tunnel interface mapping based on its source-defined `ct-<name>` device naming.
- Kept systemd IPAccounting as a per-unit source and Paqet mapping conservative unless an exact interface is present.
- Improved traffic source labels and unknown-data handling; totals sum only measurable independent tunnel instances.
- Reworked boot screen sizing and exit behavior for dynamic mobile viewports.
- Applied branded styling to form controls across all pages.

## v1.9.9
- Redesigned compact loading screen with safer mobile viewport handling.
- Added best-effort protocol/config metadata chips to tunnel cards (labels only; no secrets exposed).
- Refined tunnel card visual hierarchy and RX/TX panels.
- Fixed RTL toggle thumb direction to keep the switch inside its track.
- Versioned static asset cache keys to v1.9.9.

## 1.9.9
- Fix BackPack metrics path resolution using the exact config path from systemd ExecStart.
- Detect tunnel protocol from the actual service config path.
- Theme-aware tunnel card colors.
