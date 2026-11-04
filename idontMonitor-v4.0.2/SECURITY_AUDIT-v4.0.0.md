# Security notes — idontMonitor v4.0.0

- Anti-DDoS dashboard reports application-layer HTTP request observations only. It does not claim network-wide visibility or mitigation.
- No automatic IP blocking is performed; this avoids collateral damage from false positives and legitimate high concurrency.
- The collector and watchdog run as root through fixed systemd units with fixed script paths; they accept no user-provided shell commands.
- Watchdog policy is fixed: CPU OR MemAvailable-derived RAM pressure >90% for 120 seconds; Telegram warning; 15-second delay; recheck; 30-minute cooldown.
- The watchdog reads Telegram credentials from the existing root-protected state file and never logs the token.
- Existing authenticated web session, CSRF protections, host validation and allowlisted operations model are retained.
- Limitations: in-process HTTP telemetry is volatile across app restarts; it only sees requests that reach this application. Upstream network protection must be supplied by the hosting provider or a suitable edge service.
