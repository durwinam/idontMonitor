# Security notes — v4.0.1

- Request telemetry is application-layer only and retained for 24 hours in SQLite.
- The protection toggle is persisted under `/var/lib/idontmonitor/security.json` and defaults to false.
- The rate-limit guard is only evaluated when protection is explicitly enabled. Its default threshold is 600 requests per source per 10 seconds and the temporary response window is 60 seconds.
- Per-source rate limiting is not definitive DDoS classification. NAT/shared egress may aggregate many legitimate users; tune thresholds conservatively and prefer upstream protection for volumetric attacks.
- BackPack cleanup remains fail-closed: uncertain firewall ownership or unreadable firewall state prevents configuration deletion. No global firewall flush is used.
