# Security audit — idontMonitor v3.6.2

- Web application remains unprivileged; host mutations remain in the root-owned fixed-action helper.
- Tunnel identifiers are strictly validated; BackPack paths are derived from fixed directories; symlink/non-regular targets are rejected.
- PCK cleanup derives exact eight-hex IDs from tokens in the target TOML, uses an exclusive network-namespace lock, refuses a running engine referencing the exact config, and removes only rules with matching `backpack-pck-<id>-` comments in filter/raw tables.
- Metadata and node-pair JSON are atomically edited while preserving unrelated entries.
- Traffic is atomically added to the retired ledger before its per-tunnel metrics file is removed. Quota and schedule are per-instance only.
- No global BackPack files, services, other tunnel configs, or remote node tunnel are deleted.
- Live destructive testing was not performed.
