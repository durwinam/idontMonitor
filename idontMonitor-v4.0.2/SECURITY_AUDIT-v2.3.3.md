# Security review — idontMonitor v2.3.3

## Addressed
1. **Predictable initial username** — fresh install now generates a random five-digit account ID.
2. **Weak password alphabet** — initial/reset passwords are 24 characters with guaranteed lowercase, uppercase, digit, and special character; scrypt work factor increased to N=32768.
3. **Weak custom password policy** — password changes require 16–128 characters and all four character classes.
4. **CAPTCHA answer in client cookie** — answer is now server-side only, one-time, short-lived, and IP-bound.
5. **Account persistence bug** — mutable account state was written through an undefined `ACCOUNT_STATE_PATH`; it now has a defined service-state path and is loaded at startup. Writes are atomic and mode 0600.
6. **Remote HTTP credential exposure** — remote login is denied unless HTTPS is detected, unless an explicit unsafe override is configured. Loopback recovery remains possible.
7. **Rate-limit memory growth** — per-key rate-limit buckets are pruned and bounded.
8. **Username timing side-channel** — password hash verification is performed even for invalid usernames.

## Remaining risks / deployment requirements
- A compromised root account or VPS host can still read or replace application code and credential hashes.
- The login limiter is per process and does not coordinate multiple workers or multiple hosts; deployment remains configured for one worker. For scaled deployments, use a shared rate-limit store and external reverse-proxy throttling.
- HTTP mode cannot provide confidentiality. Configure TLS/Caddy; do not set `IDM_ALLOW_INSECURE_REMOTE_LOGIN=1` on a public interface.
- The updater verifies GitHub asset SHA-256 when GitHub supplies a digest; the GitHub tag-tarball fallback does not have an independent signed digest. For higher supply-chain assurance, publish signed releases or require a verified digest for every artifact.
- No live penetration test or host-level malware scan was performed.
- BackPack is a separate package and is not automatically upgraded by idontMonitor's updater; no official BackPack update source was configured in this project.
