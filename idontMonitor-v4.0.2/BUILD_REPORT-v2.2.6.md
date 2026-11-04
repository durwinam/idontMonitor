# idontMonitor v2.2.6 — Build & Test Report

## Changes
- Advanced theme-aware glass surfaces and readable theme-specific text colors while preserving all eight themes.
- Added an authenticated, server-generated CAPTCHA flow for root VPS password changes. Challenges expire after three minutes, are single-use, and are bound to the requesting IP and login session.
- Added rate limits for CAPTCHA requests and password-change attempts.
- Localized VPS password/reboot modal labels, CAPTCHA controls, and common error messages for Persian and English. Persian and Arabic-Indic numerals are accepted for CAPTCHA answers.
- Added Telegram custom emoji MessageEntity support for mapped IDs, with a Unicode retry after explicit Telegram entity rejection. Custom mappings can be overridden through `IDM_TELEGRAM_CUSTOM_EMOJI_IDS`.
- Added baseline HTTP security headers and no-store policy for API/login responses.
- Updated version metadata, asset cache keys, documentation, and regression tests.

## Validation performed
- `python3 -m compileall -q app scripts tests` passed.
- `bash -n install.sh` passed.
- `node --check` passed for all static JavaScript files.
- Every `tests/test_*.py` script passed.
- Runtime smoke checks passed for challenge creation/binding, UTF-16 emoji offsets, and live ASGI security headers.
- Archive root layout and SHA-256 integrity are checked during packaging.

## Not tested live
No live VPS root-password change or reboot, live Telegram token rendering, or real browser/iPhone visual test was performed. CAPTCHA state is in-memory and intended for the default single-worker deployment; multi-worker deployments need shared state.
