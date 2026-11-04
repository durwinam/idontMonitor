# Security notes — idontMonitor v3.0.0

- New API endpoints use the existing session-authentication guard.
- RAM scan reads `/proc` metadata, does not invoke a shell, and has no mutation endpoint.
- Disk scan is limited to four explicitly named idontMonitor log files. It checks canonical parent directory, rejects symlinks/non-regular files, and never deletes.
- Log Manager settings are atomically persisted with mode 0600; changing settings does not truncate or unlink any file.
- Endpoint probe host values are extracted only from validated service config paths under known config directories; `ping` uses an argument array and bounded timeout. It is clearly described as endpoint ICMP, not tunnel latency.
- Telegram bot tunnel monitoring uses a strict service-name allowlist, bounded `systemctl` calls, a two-observation transition check, and configured admin IDs.
- No shell evaluation, arbitrary command endpoint, process termination, or automatic deletion was added.
- Production permissions, real Telegram delivery, and all installed BackPack/C-Tunnel configuration variants require staging/VPS verification. Static checks do not prove production safety.
