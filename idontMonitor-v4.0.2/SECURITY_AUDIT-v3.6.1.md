# Security audit — idontMonitor v3.6.1

- Web process remains unprivileged (`User=idontmonitor`).
- `NoNewPrivileges=false` is required for sudo's setuid/setgid transition; no broad capabilities are granted. The web process still has an empty `CapabilityBoundingSet` and `AmbientCapabilities`. `/etc/systemd/system` and `/etc/backpack` are writable only within the service mount namespace; Unix ownership/permissions still prevent the unprivileged `idontmonitor` UID from writing these root-owned files directly.
- Privileged operations remain confined to the root-owned `/usr/local/sbin/idontmonitor-ops` helper and sudoers allowlist. No arbitrary shell execution was added.
- BackPack deletion accepts only the existing strict `backpack-*.service` unit naming pattern and refuses protected management services. It requires a regular non-symlink unit file and matching regular non-symlink `/etc/backpack/<name>.toml` config.
- Only exact per-tunnel files are removed. Global BackPack settings, binary, monitor/web UI services, Telegram config and other tunnel files are not touched. Metrics are validated and atomically folded into `retired-traffic.json` before the source metrics file is removed.
- Scheduled restart timer is disabled before its exact unit files are removed. If stop/disable or validation fails, the helper exits with an error rather than claiming deletion.
- No destructive action was run against a live VPS during this build.
