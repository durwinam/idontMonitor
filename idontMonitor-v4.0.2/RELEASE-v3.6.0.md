# idontMonitor v3.6.0

## Resource Analyzer and operations reliability

- Managed log cleanup now safely flushes, closes, and reopens the active `RotatingFileHandler` under its lock. A fresh `idontmonitor.log` is immediately available for new records after cleanup.
- Bulk cleanup clears only the explicit idontMonitor log allowlist; rotated files are removed and the active log is recreated. BackPack, C-Tunnel, Docker, database, system and configuration files remain outside the cleanup scope.
- Tunnel deletion now supports verified C-Tunnel shared-template instances (`ctunnel@…` and `ctunnel-engine@…`) instead of incorrectly requiring a standalone unit file for every instance.
- Fixed the false “helper not installed” result: the web process no longer uses `os.access(X_OK)` on a deliberately root-only `0750` helper. It validates root ownership/mode and lets `sudo -n` perform the privileged execution check. The installer/updater also install/refresh the helper and validate sudoers policy.
- RAM/Disk analyzer actions use branded idontMonitor confirmation dialogs and in-panel feedback instead of browser/OS alert dialogs. Protected RAM processes are explicitly labelled; eligible user processes have per-process and bulk stop controls.
- Analyzer cards and mobile spacing are refined for better readability.

## Safety

- RAM is reclaimed by stopping processes, never by deleting memory. Root-owned and critical services remain protected; process identity is revalidated before SIGTERM.
- Tunnel removal stops/disables the selected supported instance and preserves tunnel configuration/data. Management, relay and core units remain protected.
- Log cleanup remains limited to named idontMonitor log files with symlink and canonical-path checks.

## Validation

- `python -m pytest -q tests`: 63 passed
- Python compileall: passed
- `node --check static/operations.js`: passed
- `node --check static/app.js`: passed
- `bash -n install.sh scripts/idontmonitor-ops scripts/idontmonitor-update`: passed

No live VPS service stop, tunnel removal, or log deletion was performed during this build. Validate on a staging host before production rollout.
