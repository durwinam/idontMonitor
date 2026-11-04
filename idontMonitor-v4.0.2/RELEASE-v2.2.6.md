# idontMonitor v2.2.6

## Highlights
- Theme-aware glass surfaces and improved readability across the existing eight themes.
- Authenticated, server-generated, one-time CAPTCHA for root VPS password changes, bound to the client IP and login session, with three-minute expiry.
- Rate limits for CAPTCHA issuance and password-change attempts.
- Persian/English translations for CAPTCHA, password-change, and reboot feedback.
- Telegram custom emoji entities for mapped glyphs (including the supplied CPU/RAM/Disk IDs), with Unicode fallback after explicit Telegram entity rejection.
- Baseline HTTP security headers and no-store cache policy for API/login responses.

## Compatibility
The release retains existing monitoring, persistent traffic counters, tunnel operations, updater workflow, and theme selection. The installer targets Debian/Ubuntu.

## Validation limits
Automated source tests and syntax checks are run during packaging. No live VPS password change/reboot, real Telegram token rendering, or physical mobile-device visual test is performed in the build environment.
