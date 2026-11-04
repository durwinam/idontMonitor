# idontMonitor v2.2.3 — Build & Test Report

## Changes
- VPS Management route now resolves correctly in the dashboard navigation.
- Added live host information (hostname, OS, kernel, uptime, CPU/load, memory and disk) with loading/error fallbacks.
- Added root-password change endpoint protected by panel authentication, confirmation, password policy, and a root-owned allowlisted helper.
- Added Telegram admin actions for root password changes and VPS reboot with confirmation, inline back/cancel navigation, and message editing rather than duplicate messages.
- Password input messages are deleted on receipt where Telegram permits; the password is held in memory only and never written to logs/config files.
- Improved mobile layout and theme-aware VPS cards.

## Checks
- Python compileall, JavaScript syntax checks, shell syntax checks, source tests and archive integrity checks run during packaging.

## Not tested
- No live VPS reboot or real root password change was executed in this build environment.
- No live Telegram token was available, so real Telegram API message editing/deletion and callback delivery could not be verified.
- Mobile browser screenshot testing against the production VPS was not available.
