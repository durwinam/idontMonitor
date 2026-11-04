# idontMonitor v2.3.3 — Security hardening

## Security changes
- Fresh installs generate a random five-digit account ID instead of the default `admin` username.
- Fresh install and CLI reset passwords are generated with 24 characters and guaranteed lowercase, uppercase, numeric, and special-character classes; password hashes use scrypt with N=32768.
- User-selected password changes require 16–128 characters and all four character classes.
- Login CAPTCHA answers are stored server-side, expire after three minutes, are single-use, and are bound to the requesting IP; CAPTCHA answers are no longer placed in the readable signed session cookie.
- Remote sign-in over plain HTTP is rejected by default; HTTPS is required. Local loopback access remains available for recovery. An explicit `IDM_ALLOW_INSECURE_REMOTE_LOGIN=1` override exists only for deliberate break-glass scenarios and is not recommended.
- Login rate-limit state is bounded to mitigate memory exhaustion from many source IPs; password hashing runs for invalid usernames as well to reduce timing leakage.
- Account username/password changes persist in `/var/lib/idontmonitor/account.json` with mode 0600, atomically, and are loaded at startup. This fixes the previous undefined account-state path / non-persistent account update behavior.
- Existing credentials are preserved during normal upgrades to avoid lockout. The CLI password reset rotates the default `admin` username to a random five-digit ID and prints the new password only once.

## BackPack note
The idontMonitor updater updates idontMonitor code only; it does not silently replace the separate BackPack installation. This release hardens the BackPack monitoring/operations integration, but does not install or upgrade the external BackPack package without a trusted, explicitly configured upstream source/version.

## Validation
Automated tests and source-level checks are included in the build report. A live VPS penetration test, HTTPS certificate validation, and BackPack upstream upgrade were not performed by this package build.
