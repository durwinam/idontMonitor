# idontMonitor v3.5.0

## Resource Analyzer UI and cleanup controls
- Reworked RAM and Disk analyzer modal for responsive mobile use, improved spacing, hierarchy, readable action contrast, and contained scrolling.
- Added a confirmed bulk-stop action for eligible non-root user processes discovered in the RAM scan. Each PID is revalidated against its process start time immediately before SIGTERM; root and protected core/database/container processes are skipped.
- Kept per-process stop actions and added explicit explanation that RAM cannot be deleted: memory is reclaimed by stopping an eligible process or service.
- Kept per-file and bulk deletion for the explicitly managed idontMonitor log allowlist. The action now has clearer irreversible-operation wording and two confirmation steps.
- Updated the release version and cache-busting identifiers.

## Safety boundaries
- No arbitrary process kill, shell execution, or deletion of arbitrary files/directories is exposed.
- Service footprint scans remain read-only. BackPack, C-Tunnel, Docker, database, OS and configuration directories are not eligible for bulk deletion.
- Bulk process stop can interrupt user applications; only scanned, non-root, non-protected processes with matching start ticks are eligible.
