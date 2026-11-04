# Build report — idontMonitor v3.2.0

## Source inputs
- idontMonitor v3.1.0 source archive
- BackPack source archive supplied in this conversation
- C-Tunnel source archive supplied in this conversation

## Implemented
- Replaced the incorrect BackPack `backpack-client-*` naming assumption with the source-defined `backpack-<name>.service` convention.
- Added canonical BackPack TOML and native metrics snapshot discovery.
- Added C-Tunnel catalog and environment-file endpoint resolution.
- Added BackPack native connection state alongside ICMP endpoint checks.
- Fixed analyzer modal population and refresh behavior.
- Grouped RAM by `/proc/<pid>/cgroup` systemd unit and exposed per-process detail.
- Added bounded, no-symlink disk usage scans for known product roots; directory footprints are read-only.
- Kept deletion constrained to explicitly named idontMonitor managed log files.

## Checks
- `python -m pytest -q`: 51 passed.
- `python -m compileall -q app scripts tests`: passed.
- `node --check static/operations.js`: passed.
- `node --check static/app.js`: passed.
- `bash -n install.sh scripts/idontmonitor-ops scripts/idontmonitor-update`: passed.
- C-Tunnel `go test ./pkg/catalog ./pkg/tunnel`: passed.
- C-Tunnel `pkg/conntest` test run timed out.
- BackPack Go tests could not start because Go attempted to download toolchain 1.26.9 and outbound network access was unavailable.

## Limitations
- No access to the target VPS; exact installed unit names, config locations, ICMP policy, and native snapshots must be verified on the host.
- BackPack health uses its source-defined native metrics snapshot; older engines without a fresh snapshot are marked stale/unknown.
- Disk footprint roots are intentionally an allowlist, not a whole-filesystem scan. Unlisted install/data roots are not attributed.
- Tunnel RTT through the data plane is not inferred from ICMP.
