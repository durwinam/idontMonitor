# Build report — idontMonitor v3.6.2

## Implemented
- BackPack per-instance deletion now stops/disables the exact tunnel and its scheduled-restart timer before cleanup.
- Parses the exact BackPack TOML and derives PCK guard IDs from its server/client/direct/L3 tokens.
- PCK firewall cleanup is scoped to tagged rules for those IDs in filter/raw tables, coordinated by a network-namespace lock, and checks packet-socket-owning BackPack processes for shared token ownership. Unknown ownership or inspection failures abort safely.
- Removes only this tunnel's `meta.json` entry and `node-pairs.json` pair while preserving other tunnels' records.
- Retires final traffic into `retired-traffic.json`, removes exact per-tunnel quota, schedule, TOML, metrics, and systemd unit files, then reloads systemd.
- API response and confirmation UI now accurately state that BackPack tunnel configuration is removed while global BackPack installation and other tunnels remain.
- C-Tunnel template-instance behavior remains separate and preserves shared configuration/state.
- Added dedicated systemd runtime directory for PCK lock coordination.

## Verification
- `python -m pytest -q`: 68 passed.
- `python -m compileall -q app scripts tests`: passed.
- `node --check` for app.js, operations.js, telegram-bot.js: passed.
- `bash -n` for install.sh, updater and privileged helper: passed.
- systemd unit syntax inspected; deployment-specific verification remains required.

## Deployment limitation
No destructive action was executed against the user's live VPS. A disposable BackPack tunnel is required for end-to-end verification of sudo, systemd sandbox, iptables backend, PCK cleanup, metadata cleanup, and daemon-reload on the target host.
- `systemd-analyze verify` parses the unit after correcting the inline-comment syntax; its only local warning is the expected missing deployment path `/opt/idontmonitor/venv/bin/uvicorn` in this build container.
