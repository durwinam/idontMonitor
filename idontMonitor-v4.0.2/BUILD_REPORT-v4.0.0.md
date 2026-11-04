# Build report — idontMonitor v4.0.0

## Base
- Source base: idontMonitor v3.6.3 release archive.
- Version metadata: VERSION, installer, FastAPI metadata, operations API metadata, UI labels and cache-busting values updated to 4.0.0.

## Implemented
- Dedicated Anti-DDoS Shield page with a separate navigation entry and custom dark/neon glass visual system.
- Bounded application-layer HTTP request telemetry, per-client rolling request rates, top sources and anomaly observations.
- Automatic IP blocking intentionally remains disabled to avoid false positives against legitimate high-concurrency traffic. The UI clearly states that this is not upstream volumetric mitigation.
- Added minute telemetry collector and systemd timer for 24-hour resource history and tunnel state-change events.
- Reworked Telegram report to cover the preceding six hours: highest sampled CPU, RAM used/total/percent, disk used/total/percent, active/inactive tunnels and tunnel incidents.
- Added root-owned resource watchdog and systemd timer. CPU OR MemAvailable-derived RAM pressure above 90% for 120 seconds triggers Telegram warning, 15-second grace, a final pressure recheck and a 30-minute reboot cooldown.
- Installer installs and enables the collector and watchdog timers while retaining the existing config/state backup and upgrade workflow.

## Verification performed
- Python compile checks: passed.
- JavaScript syntax checks (Node): passed.
- Bash syntax checks: passed.
- Systemd unit verification: passed with no diagnostics.
- Collector smoke test in an isolated temporary state directory: passed; generated one sample and tunnel event history file.
- FastAPI import and Shield endpoint registration: passed.
- Pytest: **72 passed**.

## Important limitations
- No live VPS upgrade or real system reboot was executed during this build.
- No real DDoS attack simulation or network-level firewall mitigation was performed. The Shield page observes HTTP requests that reach the application; it does not block clients and cannot mitigate upstream link saturation.
- Peak CPU history begins accumulating after the collector timer starts. The first six-hour report after installation may state that sample coverage is incomplete.
- Automatic reboot can interrupt active users and tunnels. It is enabled according to the requested CPU OR RAM >90% sustained policy, with a 120-second hold and 30-minute cooldown.
