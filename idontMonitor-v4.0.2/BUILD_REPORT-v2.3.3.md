# Build report — idontMonitor v2.3.3

- Source base: idontMonitor v2.3.2 package supplied in the current workspace.
- Version: 2.3.3.
- Security updates: server-side CAPTCHA, stronger credential generation/policy, random five-digit initial username, HTTPS-only remote login, bounded rate-limit state, account-state persistence repair, and login timing mitigation.
- No unrelated monitoring formulas, tunnel metrics, or UI layout logic intentionally changed.
- Test command: `PYTHONPATH=. pytest -q`.
- Automated result: 41 tests passed in the local build environment.
- Additional checks: `bash -n install.sh scripts/idontmonitor-ops scripts/idontmonitor-update`; Python compile check for app/main.py and app/ops.py.
- Not performed: live VPS deployment, external penetration test, or actual BackPack package upgrade.
