# Build report — idontMonitor v4.0.1

Base: idontMonitor v4.0.0 source tree.

Implemented changes:
- Responsive redesign of the dedicated Anti-DDoS page; fixed mobile layout, compact status card, and custom animated 24-hour traffic chart.
- Persistent request telemetry in SQLite, minute buckets retained for 24 hours, live refresh, total request count and peak-minute calculation.
- Manual protection checkbox, disabled by default; monitoring and recording remain active when protection is disabled.
- Explicitly gated conservative application-layer rate limiting when protection is enabled: 600 requests per source in 10 seconds triggers a 60-second HTTP 429 window. This is a heuristic and is documented as not proving DDoS.
- BackPack deletion now stops the service without first removing its enablement symlink; PCK inspection tries nft/legacy iptables alternatives and returns actionable backend diagnostics. Disablement and file deletion are deferred until PCK cleanup succeeds.
- Version metadata and static cache-busting references updated to 4.0.1.

Checks:
- `python3 -m compileall -q app scripts tests`: passed.
- `node --check static/app.js`, `operations.js`, `telegram-bot.js`: passed.
- `bash -n install.sh scripts/idontmonitor-ops`: passed.
- `python3 -m pytest -q`: 76 passed.
- SQLite telemetry smoke test (minute aggregation, persistent storage, default-off setting and persisted toggle): passed in an isolated temporary directory; no production VPS data was used.

Not performed:
- No deployment or upgrade on the user's VPS.
- No live DDoS attack test.
- No real BackPack tunnel deletion or firewall mutation on a production host.
