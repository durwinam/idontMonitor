# Build report — idontMonitor v2.3.3

- Source reviewed: uploaded `C-Tunnel-main.zip`, whose `pkg/version/version.go` declares C-Tunnel **0.2.5**.
- Fixed C-Tunnel traffic undercounting for ECMP lane devices by summing only the exact `ct-<name>` base interface and `.1`–`.7` lane devices.
- Fixed C-Tunnel instance removal for shared systemd template units. Teardown failure now preserves the enabled instance and state/configuration record.
- Added regression tests for lane aggregation, strict interface matching, and safe instance removal.
- Updated active runtime, installer, UI, asset cache keys, README, and release metadata to v2.3.3. Historical release notes remain historical.
- Automated tests: **36 passed** (`python -m pytest -q`).
- Shell syntax checks and Python compile checks passed.
- Live VPS/kernel behavior was not tested; the final release requires a real host smoke test before production deployment.
