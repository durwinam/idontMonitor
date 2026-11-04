# Build Report — idontMonitor v3.3.0

## Source inputs
- idontMonitor v3.2.0 source archive
- BackPack-main source archive (metrics Snapshot and health source)
- C-Tunnel-main source archive (catalog TunnelConfig, Store state, tunnel device naming)

## Changes
- Added source-specific endpoint resolution and metadata.
- BackPack peer resolution uses `peer`, `connected`, and `taken` from the exact native snapshot.
- C-Tunnel resolution handles normal and reverse modes separately; reverse checks use the configured tunnel-side peer through the source-defined device name.
- Ping API now returns source/mode/interface/native health; UI differentiates tunnel-peer ICMP from underlay endpoint ICMP.
- RAM analyzer includes root-owned daemons for accurate service totals while retaining action restrictions.
- Added `tests/test_engine_endpoint_resolution.py`.

## Validation
- pytest: 56 passed
- Python compileall: exit code 0
- `node --check static/operations.js`: passed
- `node --check static/app.js`: passed
- `bash -n install.sh`: passed
- `bash -n scripts/idontmonitor-ops`: passed

## Limitations
- No live VPS test was possible. ICMP may be filtered; `unavailable` does not mean tunnel offline.
- C-Tunnel reverse ping depends on `tun_remote4` being configured and the `ct-<name>` device existing.
- BackPack peer probing depends on a fresh native snapshot with an explicit connected state.
