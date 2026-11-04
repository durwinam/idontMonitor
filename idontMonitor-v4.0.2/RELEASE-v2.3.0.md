# idontMonitor v2.3.0

## Fixes
- Telegram panel login now reads the panel's own deployment metadata from `/var/lib/idontmonitor/install-mode` and runtime configuration from `/etc/idontmonitor/environment`.
- HTTPS mode links to the configured domain using standard HTTPS, instead of incorrectly using the internal loopback app port.
- HTTP mode uses the public IP and dedicated port saved by idontMonitor's installer.
- Removed fallback guessing from unrelated `WEB_PUBLIC_PORT`/`IDM_WEB_PORT` variables and removed external IP lookup. If local installation metadata is unavailable, the bot reports that it cannot determine the panel URL instead of generating a potentially incorrect link.
- Preserved keyboard button colors/layout, the red single-button final panel-link row, Premium emoji fallback, and proper status-message newlines.

## Scope
No intentional changes to monitoring calculations, tunnel statistics, installation state, or other core behavior.

## Validation
- Automated test suite: 32 passed.
- Archive integrity and extracted-source tests are checked during packaging.
- Live Telegram rendering and target VPS DNS/proxy behavior cannot be verified from this build environment.
