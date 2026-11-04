# idontMonitor v3.1.0

## Resource analyzer UX and safety
- Resource Analyzer is relocated to VPS Management and opens scan results in a dedicated mobile-responsive modal.
- Each eligible RAM process offers a guarded SIGTERM action; bulk stop requires two confirmations and server-side PID/start-time validation. Root-owned and selected critical process names are protected.
- Disk scan remains deliberately scoped to the four explicitly managed idontMonitor log files. Each listed file has a delete action; bulk deletion requires two confirmations and server-side basename, directory, regular-file, and symlink checks. No arbitrary filesystem scan or deletion is exposed.
- Mutating operations are audit-logged.

## Tunnel endpoint probe
- Expanded endpoint key matching for common server/remote address variants in JSON/TOML-like configs.
- Ping still reports endpoint ICMP reachability, not end-to-end data-plane tunnel RTT. ICMP-filtered or unsupported endpoints remain unavailable, not zero.

## Verification
- Python compile checks and 48 pytest tests pass.
- JavaScript syntax checks and installer/update shell syntax checks pass.
- Real process termination, deletion, and Telegram delivery must be validated on a staging VPS before production use.
