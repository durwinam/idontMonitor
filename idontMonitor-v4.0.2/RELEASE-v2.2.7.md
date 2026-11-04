# idontMonitor v2.2.7

## Fixes
- Fixed dashboard version label reporting an obsolete version.
- Prevented overlapping telemetry refresh requests, with a guaranteed lock release on success, error, or redirect.
- Added centralized theme-aware surfaces and control colors for cards, forms, dialogs, status panels, and dynamic utility boxes.
- Removed an `@font-face` URL that referenced a font file not included in the source archive.
- Bumped static asset cache keys to avoid stale browser CSS/JavaScript after update.
- Kept the existing monitoring and network-counter collection logic intact.

## Security review
- Reviewed privileged helper invocation paths and checked that shell commands are passed as argument arrays rather than constructed from user-controlled shell strings.
- Reviewed archive extraction path/type validation in the updater, authentication gates, password-change CAPTCHA state, and response security headers.
- Scanned project source for common embedded-secret and obvious malware indicators; none were found in this static review. See `SECURITY_AUDIT-v2.2.7.md` for scope and limitations.

## Validation
- 18 pytest checks passed.
- Python compile checks, JavaScript syntax checks, and Bash syntax checks passed.
- No live VPS upgrade/reboot/password change, browser visual QA, or live Telegram custom-emoji rendering test was performed in this build environment.
