# idontMonitor plugin architecture (v1.9.9)

## Security model

Plugins are extension points, not a mechanism for executing arbitrary uploaded code. The v1.9.9 release establishes the operations router boundary (`app/ops.py`) and separates read-only probes from privileged mutations. New modules should be registered through explicit imports and routes, with authorization on every endpoint.

## Required rules for future modules

1. Do not use `shell=True`, `eval`, dynamic imports of user-provided paths, or arbitrary command strings.
2. Validate request bodies with bounded schemas and reject unknown action identifiers.
3. Require the existing authenticated session for every private endpoint.
4. Treat read-only host inspection separately from mutations. Privileged mutations must use a root-owned helper with strict argument validation and a narrowly scoped sudoers entry.
5. Never return secrets, private keys, environment variables, full configuration files, or unredacted logs by default.
6. Use timeouts and output-size limits for subprocesses; do not block request handlers on long-running work.
7. Record security-relevant administrative actions without storing passwords or arbitrary command input.
8. Keep plugin-owned state in `/var/lib/idontmonitor`, use atomic replacement, and set restrictive file permissions.
9. A plugin must declare its routes, permissions, state schema, health checks, and rollback behavior in documentation and tests.
10. Do not report unsupported metrics as zero. Return an explicit unavailable state and a reason.

## Current extension points

- `app/ops.py`: operations APIs, tunnel detection, safe diagnostic command palette, audit log, maintenance and alert settings.
- `app/main.py`: existing host telemetry, security checks, resource history, authentication and update center.
- `static/operations.js`: operations UI; all UI strings should be added to `locales/fa/messages.json` and remain English in English mode.

This is a constrained modular boundary, not a third-party plugin loader. Runtime loading of arbitrary plugins is intentionally not enabled because it would turn dashboard compromise into code execution.
