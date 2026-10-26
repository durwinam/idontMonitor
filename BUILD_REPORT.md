# Build report — idontMonitor v2.0.1

## Included changes
- Version metadata synchronized to `2.0.1` across source, installer, CLI, API health response, and visible web panel labels.
- Release update reads the latest stable GitHub Release Tag and prefers the exact `idontMonitor-vX.Y.Z.tar.gz` Release asset and verifies the GitHub SHA-256 digest when the API provides one; it falls back to the tag source archive only when the matching asset is absent.
- `sudo idontMonitor update-main` supports a separate main-branch source path with commit-specific immutable release directories, including updates where the semantic version remains unchanged.
- Source archive paths, member types, expanded size, and symlinks are validated before extraction; required project files and version consistency are checked.
- Python syntax is checked before activation; update stages immutable release directories, refreshes external updater/helper/systemd/CLI files with rollback copies, switches the active release atomically, and performs a health check with rollback attempt.
- Fresh installation probes for a genuinely bindable free port from 20000–45000. Upgrades preserve existing port and connection settings.
- Configuration and runtime state remain outside versioned release directories.
- Release archives exclude Python bytecode and pytest caches.

## Local validation
- `bash -n install.sh`: passed
- `bash -n scripts/idontmonitor-ops`: passed
- Python compile checks for app and updater: passed
- `pytest -q tests`: 18 passed
- Archive contents, version metadata and SHA-256 sums are checked during packaging.

A live installation/upgrade on an external VPS has not been performed by this build process.
