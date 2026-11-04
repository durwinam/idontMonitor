# idontMonitor v3.0.0 — Resource & Tunnel Intelligence

## Included
- Authenticated RAM Top-5 process inspection (read-only).
- Managed idontMonitor log inventory and Disk Analyzer (read-only, allowlisted paths only).
- Log Manager settings UI/API with atomic persistence and bounded existing log rotation information.
- Per-instance configured-endpoint ICMP probe where a validated endpoint is discoverable; explicit unavailable states otherwise.
- Telegram six-hour host resource report image and tunnel service down/recovery notifications with two-consecutive-observation debounce.
- Persian/English-aware existing panel UI retained; new UI cache version and release metadata.

## Safety by design
- No automatic file deletion, no process killing, no changes to system/Docker/database logs.
- The log cap setting is currently stored and shown but does not dynamically reconfigure the active handler; current rotation remains 100 MiB x 4 files.
- Endpoint ICMP is not the same as data-plane tunnel RTT and can be filtered.

## Validation
- 48 Python tests passed; Python, JavaScript, and shell syntax checks passed.
- Full C-Tunnel Go test suite exceeded the execution timeout in this environment; see `BUILD_REPORT-v3.0.0.md`.
- Live VPS and live Telegram delivery were not available for testing.
