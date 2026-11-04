# Build report — idontMonitor v4.0.2

## Scope
Persian localization of the Anti-DDoS page and cleanup of navigation labels, based on the supplied v4.0.1 source archive.

## Changes
- Added Persian translations for Anti-DDoS navigation, page headings, 24-hour request telemetry, chart labels, counters, source analysis, anomaly timeline, protection toggle, state labels, explanations, and dynamic empty/error states.
- Added right-to-left layout rules for the Anti-DDoS command center while keeping numeric telemetry readable.
- Removed NEW badges from VPS Management and Telegram navigation items, and removed the NEW marker from the VPS hero title.
- Updated app, API, installer, displayed version, and static asset cache keys to v4.0.2.
- Anti-DDoS request telemetry and manual protection behavior are unchanged. No tunnel deletion or firewall policy changes are included in this UI-focused release.

## Validation
- Pytest: 77 passed.
- Python compile checks: passed through the project test suite.
- Installer shell syntax: passed (`bash -n install.sh`).
- Archive integrity and SHA256 are generated for the release packages.

No live VPS installation or browser-based visual QA was performed in this build environment.
