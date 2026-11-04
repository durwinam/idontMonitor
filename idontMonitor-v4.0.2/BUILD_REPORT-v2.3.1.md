# Build report — idontMonitor v2.3.1

- Bumped runtime, installer, UI, and package version metadata from 2.3.0 to 2.3.1.
- Bumped static asset cache keys to avoid stale UI assets.
- Preserved the panel-login URL resolver using idontMonitor's installer/runtime metadata and its safe no-guess fallback.
- No intended changes to monitoring calculations or tunnel statistics.
- Automated tests: **32 passed** (`python -m pytest -q`).
- Archive integrity: ZIP and TAR.GZ validated successfully; SHA-256 checksums generated for the three deliverables.
- Live Telegram delivery and VPS-specific public routing were not tested in this build environment.
