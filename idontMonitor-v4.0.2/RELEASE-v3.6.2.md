# idontMonitor v3.6.2

## BackPack tunnel lifecycle
- Per-instance stop/disable, scheduled restart cleanup, exact token-derived PCK guard cleanup, metadata/node-pair cleanup, quota removal, traffic retirement, and exact unit/config removal.
- Global BackPack configuration, binary, web UI, monitor, proxy, Telegram settings and other tunnel records remain untouched.
- UI now describes destructive BackPack removal accurately; C-Tunnel template-instance removal continues to preserve shared config/state.
- Dedicated `/run/backpack-pck` runtime directory coordinates safe PCK lock ownership.

## Safety
- No recursive or wildcard file deletion is used in the BackPack path.
- Symlink, path, TOML, JSON, token, lock, and metrics validation are required. Uncertain PCK ownership or invalid state aborts cleanup rather than broadening deletion.
- Live VPS deletion was not performed; verify first with a disposable tunnel.
