# Security review — idontMonitor v2.3.4

## Scope
Reviewed the full supplied v2.3.3 source archive, then updated current-version metadata and the password-hashing memory ceiling for v2.3.4. Focused review included `app/main.py`, `app/ops.py`, `install.sh`, `scripts/idontmonitor-ops`, `scripts/idontmonitor-update`, Telegram bot code, systemd units, static UI, and automated tests.

## Fix in this release
- Password reset failed on the target host with OpenSSL's `memory limit exceeded` error. Scrypt now uses an explicit 512 MiB OpenSSL ceiling in all current password derivation/verification paths. Scrypt work factors remain `N=32768`, `r=8`, `p=1`.
- Added a real scrypt derivation regression test so tests do not merely check for a source-code string.
- Updated active version labels and static asset cache keys to 2.3.4.

## Existing safeguards reviewed
- Random initial credentials and complexity policy.
- scrypt password storage; no plaintext password persistence.
- Single-use, time-limited server-side login challenges.
- Bounded login rate-limit structures and audit records.
- Restricted operational helper and command allowlists.
- Updater archive path/type checks, release version validation, service health check, and rollback flow.
- Sensitive account state stored separately with restrictive permissions and atomic replacement.

## Limitations / operator notes
- A 512 MiB `maxmem` value is an OpenSSL upper bound, not a request to allocate 512 MiB, but very constrained hosts can still fail due to actual memory pressure. Do not reset credentials during an OOM event.
- HTTPS must be configured for remote login; do not enable the insecure override on a public interface.
- BackPack package updates are not performed by this project updater unless a trusted upstream package source is configured; this release does not claim to update BackPack itself.
- Automated checks cannot prove absence of all vulnerabilities. No live VPS run, external penetration test, dependency vulnerability database scan, or production rollback drill was performed as part of this build.
