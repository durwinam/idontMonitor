# Security audit notes — idontMonitor v2.2.7

## Scope and method
Static/manual review of the v2.2.6 codebase carried forward into v2.2.7, with targeted review of `app/main.py`, `app/ops.py`, `scripts/idontmonitor-ops`, `scripts/idontmonitor-update`, `scripts/idontmonitor-telegram-bot.py`, `install.sh`, authentication/session code, update archive handling, and dependencies declared in `requirements.txt`. Searched for common dangerous execution patterns, embedded credentials/private keys, suspicious persistence mechanisms, encoded payload indicators, and unexpected network destinations. Also ran the repository tests and syntax checks.

## Findings and changes
- **No obvious malware indicators found in the reviewed source.** The searched files did not reveal an embedded credential/private key, common miner/backdoor indicators, or an unexplained encoded payload. This is not a guarantee that all behavior or third-party dependencies are benign.
- **Privileged command boundary:** reviewed the fixed helper and argument-array subprocess calls; no arbitrary shell command endpoint was found in the reviewed routes. The root helper and its sudoers policy remain security-critical and must be kept root-owned and non-writable by the service account.
- **Updater extraction:** reviewed archive member checks for absolute paths, `..`, unsupported special files, and expanded-size bounds before extraction. Release authenticity still depends on the configured upstream repository and available GitHub release digest; unsigned/fallback source downloads are not equivalent to a signed release.
- **Authentication:** checked session-based route guards, login challenge expiry/one-use behavior, source-IP/session binding for sensitive VPS password CAPTCHA, rate limiting, and security response headers. Rate limits and CAPTCHA state are process-local, so multi-worker deployments need a shared store/proxy limits.
- **Dashboard reliability:** fixed a hardcoded stale version label and added a guard against overlapping metrics refresh requests.
- **Theme consistency:** normalized legacy component surfaces and control colors to follow selected theme variables.
- **Missing asset:** removed a font-face reference to a font that was not packaged.

## Static scan notes
- No matches for common private-key/token patterns were found in the source text scanned.
- No unexplained outbound destinations were found in the URL scan; the source includes GitHub update APIs, Telegram Bot API, Cloudflare speed test, IP lookup endpoints, and Caddy package/key endpoints used by documented features.
- Bandit was not installed in the build environment, so no Bandit report is claimed. No dynamic malware sandbox or dependency vulnerability database scan was available.

## Test and deployment limits
Automated repository tests and syntax checks passed. This review did not execute the installer against a real VPS, perform a production update/rollback, verify all UI states in real browsers/devices, or test live Telegram premium emoji rendering. Review dependency advisories and release provenance before production deployment; keep a backup and test upgrade/rollback on a non-production VPS first.
