# idontMonitor v3.3.0 Release Notes

## Engine endpoint and ping corrections
- BackPack: read the native per-instance metrics snapshot from `/etc/backpack/<name>.metrics.json`. A fresh snapshot (`taken` age <= 90 seconds) with `connected=true` supplies the authoritative `peer` endpoint. A fresh `connected=false` snapshot is explicitly disconnected and is not overridden by static configuration.
- C-Tunnel: read the exact named tunnel from `/etc/ctunnel/state.json`. Normal mode uses `remote_ip` for underlay endpoint ICMP. Reverse mode uses `tun_remote4` through the exact `ct-<name>` interface when present, instead of trying to ping the listener sentinel `0.0.0.0`.
- API output distinguishes endpoint source, probe mode, interface, and BackPack native health. ICMP is not represented as application RTT or proof of end-to-end service health.
## Resource analyzer
- RAM attribution now includes root-owned daemons so databases and system services are visible. Root and protected processes remain ineligible for stop actions.
- Disk analysis remains bounded, no-symlink, read-only for service footprints. Cleanup remains limited to explicitly managed idontMonitor log files.
## Compatibility
- Five regression tests added for BackPack connected/disconnected peers and C-Tunnel normal/reverse endpoint selection.
- Frontend cache-buster advanced to 3300.
