# Security audit — idontMonitor v3.6.0

- All analyzer and tunnel mutation routes continue to require the authenticated session and explicit confirmation.
- Log cleanup only accepts the hard-coded idontMonitor log allowlist, rejects symlinks, and verifies canonical parent paths. Active-file reopening occurs while holding the rotating handler lock.
- RAM process actions retain PID/start-time revalidation, UID checks, protected critical-process names, bounded bulk size, and SIGTERM only (no SIGKILL escalation).
- Tunnel actions remain allowlisted by exact service-name regex. C-Tunnel template instances are accepted only when the matching shared template exists in a trusted systemd directory. Core/relay/control-plane units are excluded in both API and root helper.
- The app does not try to execute the root-only helper as the web user; it verifies trusted file metadata and delegates execution to non-interactive sudo.
- The privileged helper remains root-owned and executable only through the validated sudoers rule; it does not evaluate shell input or accept arbitrary commands.
- Tunnel configuration/data, BackPack/C-Tunnel project directories, Docker, databases, and operating-system logs are not deleted by analyzer cleanup.
