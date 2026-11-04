# idontMonitor v3.4.0 Release Notes

## RAM analyzer
- Attributes processes by decoding systemd escaped cgroup names and checking up to five parent processes. When `/proc/<pid>/exe` is unavailable, the command line is shown as a fallback.
- Displays service totals and per-process PID, UID, state, RAM, executable/command. Unknown ownership is kept honestly as unassigned rather than guessed.

## Disk analyzer
- Each service footprint now includes the largest immediate files/folders, with exact paths and sizes.
- Recursive sizing remains bounded and does not follow symlinks. Service directories remain read-only; deletion remains limited to explicitly managed idontMonitor logs.

## BackPack diagnostics
- Aligns `connected` interpretation with BackPack's own metrics contract: true=connected, false=disconnected, absent/null=unknown.
- Distinguishes ICMP timeout from native peer status. A connected BackPack peer with blocked ICMP is shown as connected, with ICMP probe failure explained separately.
- A stale snapshot is not treated as current engine state.

## UI
- Rebuilt RAM/Disk analyzer modal as a compact mobile-first interface with readable hierarchy and service/file detail cards.

## Validation
- 59 Python tests pass.
- Python compileall, JavaScript syntax checks and installer shell syntax pass.
- No live VPS integration test was possible in the build environment; verify service cgroups and BackPack snapshots on staging before production.
