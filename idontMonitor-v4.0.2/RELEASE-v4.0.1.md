# idontMonitor v4.0.1

## Shield / Anti-DDoS
- Rebuilt the Shield page layout for mobile and desktop with a responsive command-centre header, dedicated 24-hour animated request chart, request totals, live RPS, peak minute and source/event panels.
- Request telemetry remains enabled independently of the protection switch and is stored in a bounded SQLite 24-hour minute history.
- Anti-DDoS protection is **off by default** and is only armed after the operator explicitly checks the dedicated switch.
- When manually enabled, a conservative application-layer per-source guard temporarily returns HTTP 429 to a source exceeding the configured 600 requests per 10 seconds, for 60 seconds. The action is recorded as a rate-limit event.
- This is not proof that an event is DDoS and is not a substitute for CDN/datacenter mitigation against distributed or link-saturating attacks. A large shared-NAT client population can still require threshold tuning.

## BackPack tunnel deletion
- Reordered deletion so the exact tunnel service is stopped first, while its systemd enablement symlink remains intact during PCK inspection.
- The helper no longer uses `disable --now` before PCK inspection, preventing the half-deleted state shown in the supplied screenshot.
- Firewall inspection now tries the configured iptables binary and nft/legacy alternatives, and reports the actual inspection error when all fail.
- If PCK ownership/rules cannot be verified, cleanup fails closed and leaves the unit definition and tunnel configuration in place. No broad firewall flush or unrelated rule deletion is performed.
- Systemd disablement and file removal occur only after PCK cleanup succeeds.

## Verification
- Python compileall: passed.
- JavaScript syntax checks: passed.
- Bash syntax checks: passed.
- Pytest: 76 passed.
- Package integrity: ZIP and TAR.GZ extraction and checksum verification performed.

## Limitations
- Request telemetry records HTTP requests that reach this FastAPI application; requests rejected upstream or handled only by a reverse proxy are not included unless the proxy is separately instrumented.
- Local application rate limiting cannot stop volumetric attacks that saturate the VPS network link before traffic reaches the application.
- No live VPS deployment, real attack simulation, or real BackPack firewall deletion was performed in the build environment. BackPack deletion remains deliberately fail-closed if firewall ownership cannot be verified.
