# Security audit — idontMonitor v3.2.0

- Analyzer endpoints require an authenticated session.
- Process ownership is attributed from kernel cgroup membership; `/proc` values are read-only during scans.
- RAM stop remains an individual, confirmed SIGTERM operation with start-time revalidation and protected system/root process checks. Bulk service-group stopping is disabled.
- Disk scans are bounded by entry count and depth, do not follow symlinks, and are read-only.
- Service/config directory footprints have no delete action.
- Cleanup remains limited to fixed idontMonitor managed log basenames under the configured log directory, with canonical path and symlink checks.
- C-Tunnel and BackPack config reads are restricted to their canonical `/etc` roots and bounded file sizes. No shell command is built from config content.
- ICMP target is validated and passed as a single argument to a fixed `ping` invocation with a short timeout.
- No credentials, tunnel tokens, or secrets are returned by the new analyzer endpoints.

## Residual considerations
- A configured endpoint may intentionally block ICMP; this must be reported as ICMP-unreachable, not tunnel-down.
- Service directory sizes are approximate when the scan hits its bounded entry limit.
- Live host integration and privileged mutation tests remain outstanding.
