# Build report — idontMonitor v3.6.1

## Scope
- Fixed systemd sandboxing that prevented the web service from invoking the narrowly-scoped root helper through sudo. `NoNewPrivileges=false` remains explicit; the `RestrictSUIDSGID=true` restriction that blocked sudo's setgid transition is removed. `/etc/systemd/system` and `/etc/backpack` are added to the service mount namespace write allowlist so the privileged helper can complete the exact unit/config lifecycle.
- Implemented BackPack per-tunnel deletion using the upstream BackPack `internal/manage/core/tunnel.go` `Delete` lifecycle as the behavioral reference.
- BackPack deletion now stops and disables the exact tunnel unit, disables its per-tunnel scheduled-restart timer, removes the exact unit/config/quota/schedule files, and retires its final metrics into `retired-traffic.json` atomically. The global BackPack binary, web UI, monitor, Telegram configuration, other tunnels and unrelated files are preserved.
- Added strict name/path/type/symlink checks and preflight validation. C-Tunnel template deletion behavior remains unchanged.

## Verification
- `python -m pytest -q`: 66 passed.
- `python -m compileall -q app scripts tests`: passed.
- `node --check` for app.js, operations.js and telegram-bot.js: passed.
- `bash -n` for install.sh, idontmonitor-ops and idontmonitor-update: passed.

## Deployment note
The fix is packaged but has not been executed on the user's VPS. Apply the release as root using the official updater/installer, then verify the service unit contains no `RestrictSUIDSGID=true`, `sudo -n /usr/local/sbin/idontmonitor-ops ...` succeeds through the application context, and a disposable BackPack tunnel is removed. No real VPS tunnel was deleted during build tests.
