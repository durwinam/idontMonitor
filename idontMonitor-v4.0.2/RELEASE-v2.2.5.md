# idontMonitor v2.2.5

## Security
- Login now requires a short arithmetic CAPTCHA in addition to the existing username/password authentication.
- Challenge answers expire after five minutes and each challenge is consumed by a single login attempt.
- Challenge generation is rate-limited per client; existing login throttling and audit logging remain enabled.

## Compatibility
- Preserves the existing dashboard, metrics collection, tunnel detection, operations routes, installation modes, and update/rollback architecture.
- CAPTCHA is first-party and does not depend on external CAPTCHA services or send login data to third parties.

## Validation
- Source-level tests and syntax checks are run for this archive. Live VPS, browser-device, and privileged system-operation checks require a deployed test environment.
