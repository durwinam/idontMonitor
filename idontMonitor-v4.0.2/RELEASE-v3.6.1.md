# idontMonitor v3.6.1

## Fixed
- Fixed tunnel deletion failure caused by systemd's `RestrictSUIDSGID=true`, which blocked sudo from switching to root GID and triggered the `sudoers_audit` initialization error.
- Reworked BackPack tunnel removal to follow BackPack's native deletion lifecycle instead of only removing a systemd unit.

## BackPack deletion behavior
- Stops and disables the selected tunnel service.
- Disables and removes that tunnel's scheduled restart timer/service, if present.
- Removes the tunnel's own systemd unit, TOML configuration and quota file.
- Preserves lifetime traffic totals by atomically retiring its final metrics into `retired-traffic.json`.
- Leaves the BackPack installation, global settings, monitor, web UI, Telegram settings and other tunnels intact.

## Validation
66 tests passed, plus Python compile, JavaScript syntax and shell syntax checks. VPS execution remains to be verified after deployment.
