# Build report — idontMonitor v3.1.0

Changes: VPS Management resource analyzer placement, dedicated responsive scan modal, per-item actions, double-confirmed bulk actions, guarded non-root process SIGTERM with process start-time validation, and safe deletion limited to explicitly managed application log files. Tunnel endpoint parser recognizes additional common address keys.

Validation completed:
- `python -m compileall -q app scripts tests`
- `python -m pytest -q` — 48 passed
- `node --check static/operations.js`
- `node --check static/app.js`
- `bash -n install.sh scripts/idontmonitor-update`

Limitations: BackPack source was not available in the supplied build inputs, so its config schema could not be exhaustively cross-checked. C-Tunnel source was inspected for endpoint behavior, but full Go tests were not rerun in this release. The dashboard ping is endpoint ICMP only; it is not a tunnel data-plane RTT measurement. Disk analysis intentionally only lists managed application logs, not every large file on the host. Production destructive-action testing is not claimed.
