# Security review — v2.3.5

- Removed the server-side HTTPS-only login rejection to meet the requested HTTP compatibility behavior.
- Added a client-side, login-page-only HTTPS/SSL/TLS recommendation for HTTP, localized in English and Persian, with a five-second lifetime.
- Existing CAPTCHA validation, rate limiting, password hashing, and session logic were not intentionally changed.
- HTTP inherently exposes credentials and session cookies to network interception; the notice does not mitigate this risk. Deploy HTTPS for production use.
- Automated tests are not a substitute for testing on the target VPS or an external penetration test.
