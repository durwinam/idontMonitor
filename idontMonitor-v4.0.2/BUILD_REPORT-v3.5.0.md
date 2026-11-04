# Build report — idontMonitor v3.5.0

## Scope
Mobile-first redesign of the RAM and Disk analyzer, explicit per-item actions, bulk actions, and safer backend validation.

## Changes
- Redesigned analyzer modal with a fixed header/action bar, independently scrolling content, clearer service/process cards, improved mobile spacing and readable high-contrast action buttons.
- RAM rows show a stop action for eligible user processes. Added bulk stop for eligible non-root processes shown by the current scan.
- Bulk stop requires two user confirmations in the UI and authenticated API confirmation. The backend limits the batch, checks process UID/name/start ticks immediately before sending SIGTERM, skips protected/root processes, and audits the result.
- Disk analyzer retains per-file and bulk delete for the explicit idontMonitor managed-log allowlist only. Bulk delete has two confirmations.
- UI clarifies RAM is not a deletable file; memory is reclaimed by stopping a process. Service directories and configuration/data are not deletable through this tool.
- Bumped application and asset cache version to 3.5.0.

## Validation
- `python -m compileall -q app scripts tests`: passed
- `python -m pytest -q`: 59 passed
- `node --check static/operations.js`: passed
- `node --check static/app.js`: passed
- `bash -n install.sh scripts/idontmonitor-ops scripts/idontmonitor-update`: passed

## Not claimed
No live VPS action was executed. Runtime behavior of process termination and file removal must be verified on a staging VPS before production use.
