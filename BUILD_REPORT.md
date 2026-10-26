# Build report — idontMonitor v1.9.9

## Changes
- BackPack metrics lookup now derives the exact config path from systemd ExecStart and reads `<config-stem>.metrics.json` beside that config, matching BackPack's `cmd/cmd.go` and `internal/metrics.Path` implementation.
- Protocol/config detection inspects the exact config file passed by ExecStart, rather than guessing config filenames from the systemd unit name. Only protocol labels are returned; config contents and secrets are not exposed.
- Tunnel card colors now derive from the active theme tokens.
- Version and static cache tokens bumped to 1.9.9.

## Validation
- `python -m compileall -q app`: passed
- `pytest -q`: 11 passed
- Not tested on a live VPS or iOS Safari. Paqet remains best-effort because the provided Paqet archive does not include the full engine source.
