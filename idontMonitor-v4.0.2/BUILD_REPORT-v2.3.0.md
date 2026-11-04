# Build report — idontMonitor v2.3.0

- Fixed Telegram panel-login URL resolution to read idontMonitor's own installer metadata (`/var/lib/idontmonitor/install-mode`) and runtime environment (`/etc/idontmonitor/environment`).
- HTTPS installations now link to the configured domain on standard HTTPS, rather than exposing the loopback-only application port.
- HTTP installations use the dedicated public HTTP port recorded by the installer.
- Removed guessed `WEB_PUBLIC_PORT`/`IDM_WEB_PORT` defaults and external public-IP lookup from URL resolution; if authoritative installation metadata is unavailable, the bot reports that the panel address could not be detected.
- Preserved the final single-button red panel-link row, left/right button styling, Premium emoji fallback, and real newline formatting in status text.
- No changes to monitoring calculations, tunnel statistics, payment logic, or other core behavior.
- Production Telegram delivery and VPS-specific proxy/DNS behavior still require validation on the target server.
