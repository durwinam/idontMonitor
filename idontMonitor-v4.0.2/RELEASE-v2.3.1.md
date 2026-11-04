# idontMonitor v2.3.1

## Changes
- Version metadata and displayed version updated to 2.3.1.
- Retains the Telegram panel-login URL resolver from idontMonitor's own installation metadata: HTTPS uses the configured domain on standard HTTPS; HTTP uses the dedicated port recorded by idontMonitor's installer.
- Retains fail-closed behavior when reliable public installation metadata is unavailable, avoiding guesses from other product ports or external IP detection.
- No changes to monitoring calculations, tunnel statistics, or core behavior.

## Validation
- Automated test results are recorded in `BUILD_REPORT-v2.3.1.md` after the release test run.
