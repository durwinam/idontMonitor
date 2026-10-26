# Build report — idontMonitor v2.0.0

## Included changes
- Version metadata synchronized to `2.0.0` across source, installer, CLI, API health response, and visible web panel labels.
- Release update reads the latest stable GitHub Release Tag and downloads its GitHub source `tar.gz`; it does not require a custom ZIP asset.
- `sudo idontMonitor update-main` supports a separate main-branch source path and only activates a newer semantic version.
- Source archive paths and symlinks are validated before extraction; required project files and version consistency are checked.
- Python syntax is checked before activation; update switches the active release atomically and performs a health check with rollback attempt.
- Fresh installation probes for a genuinely bindable free port from 20000–45000. Upgrades preserve existing port and connection settings.
- Configuration and runtime state remain outside versioned release directories.
- Release archives exclude Python bytecode and pytest caches.

## Local validation
- `bash -n install.sh`: passed
- `bash -n scripts/idontmonitor-ops`: passed
- Python compile checks for app and updater: passed
- `pytest -q tests`: 16 passed
- Archive contents, version metadata and SHA-256 sums are checked during packaging.

A live installation/upgrade on an external VPS has not been performed by this build process.
