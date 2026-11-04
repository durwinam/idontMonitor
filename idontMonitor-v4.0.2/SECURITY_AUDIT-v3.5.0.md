# Security audit — idontMonitor v3.5.0

- All analyzer endpoints require the existing authenticated session.
- RAM bulk stop is bounded to 40 targets and requires explicit confirmation.
- Each PID is revalidated against current UID, process name, and kernel start ticks immediately before SIGTERM to mitigate PID reuse.
- Root-owned processes and named critical services (systemd, sshd, dockerd, containerd, PostgreSQL, Redis, idontMonitor) are protected.
- No SIGKILL escalation or arbitrary shell execution is exposed.
- Disk deletion accepts only the hard-coded idontMonitor managed-log allowlist, rejects symlinks, and checks the canonical parent directory.
- BackPack, C-Tunnel, Docker, database, operating-system, and configuration/data directories remain read-only.
