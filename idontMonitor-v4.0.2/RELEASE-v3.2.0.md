# idontMonitor v3.2.0

## Resource intelligence
- RAM results are grouped by the process's actual systemd cgroup, with per-process details nested under the owning service.
- Disk analysis reports bounded directory footprints for known BackPack, C-Tunnel, and idontMonitor data/config/log roots. Symlinks are not followed; service directories are read-only.
- The mobile analyzer modal now renders its result rows, individual eligible process actions, and the managed-log cleanup list. It refreshes after a completed action.
- Bulk deletion is limited to the separately listed, explicitly named idontMonitor managed logs. Service directories and arbitrary files cannot be deleted from this analyzer.

## Tunnel intelligence
- C-Tunnel endpoint discovery now reads the canonical `/etc/ctunnel/state.json` `tunnels[].remote_ip` record and the per-instance `/etc/ctunnel/tunnels/<name>.env` `REMOTE_IP` value.
- BackPack discovery follows the source-defined `backpack-<name>.service`, `/etc/backpack/<name>.toml`, and `<name>.metrics.json` naming convention.
- BackPack TOML parsing supports `[client].remote_addr` and endpoint values with ports; its native snapshot health is surfaced separately from ICMP.
- ICMP remains explicitly labelled as endpoint reachability, not data-plane tunnel RTT. Stale or unavailable native state is not represented as a successful ping.

## Validation
- Python test suite and syntax checks are listed in `BUILD_REPORT-v3.2.0.md`.
- Upstream C-Tunnel catalog and tunnel package tests passed. The `conntest` package test timed out in this environment.
- BackPack Go package tests could not run because the required Go 1.26.9 toolchain was not available and network access was blocked.
- Live VPS behavior, remote ICMP reachability, and Telegram delivery are not claimed as tested.
