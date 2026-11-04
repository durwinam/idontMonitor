# Build report — idontMonitor v2.2.5

Base source: `idontMonitor-v2.2.4.zip`.

Implemented:
- Added server-side arithmetic CAPTCHA to the administrator login flow.
- CAPTCHA answer is held only in the signed session, expires after five minutes, and is invalidated on submission.
- Added constant-time comparisons for challenge token/answer and rate limiting for challenge refresh requests.
- Refreshes the challenge after a failed login attempt.
- Updated release version metadata, changelog, and packaging test expectations.

Preserved:
- Existing authentication/password hashing, login rate limits, login audit, dashboard, metrics, tunnel/operations modules, installer modes, and updater/rollback flow.

Validation:
- Automated source tests are run during packaging. Real browser behavior, mobile-device layout, Telegram bot behavior, and privileged VPS operations are not claimed as live-tested in this environment.
- Premium Telegram custom emoji rendering is not yet implemented in this build; it remains an outstanding requested feature rather than being represented as complete.
