# idontMonitor v2.3.7 — Resource Analyzer Safety Preview

## Included
- Added authenticated, read-only RAM Top-5 process inventory.
- Added authenticated, read-only disk inventory restricted to explicitly named idontMonitor application log files.
- Added independent RAM and managed-log scan controls in the Tunnel Manager workspace.
- Explicitly does not stop processes or delete files. Arbitrary host-wide disk traversal is not performed.
- Preserved existing verified tunnel traffic accounting and existing bounded application log rotation behavior.

## Safety notes
- Disk inventory rejects symlinks and only accepts regular files directly under the configured idontMonitor log directory.
- No automatic cleanup/deletion was introduced in this preview because safe rotation semantics and open-file handling need dedicated tests before destructive actions can be enabled.
- The independent BackPack source archive was not available in the current build inputs. Existing source integration was retained; new BackPack-specific ping behavior was not guessed or fabricated.

## Planned but not included in this preview
- Actual per-tunnel ping probes and tunnel topology visualization.
- Six-hour Telegram chart reports and event/recovery push alerts.
- Confirmed two-step process stop and safe disk cleanup actions.
- Configurable 1 GB managed-log policy/rotation control and incident-history reports.

## Validation
- Python compileall: passed.
- Bash syntax checks: passed.
- `node --check static/operations.js`: passed.
- `python -m pytest -q`: 43 passed.
- Live VPS, real tunnel ping, Telegram delivery, and browser/device visual tests were not run.
