# Security Policy

Report vulnerabilities privately to the project maintainer once a verified security contact is published. Do not include secrets, tokens, or customer data in public issue reports.

This initial release has not undergone an independent security audit. For public exposure, use HTTPS, keep the host patched, restrict firewall access, back up configuration securely, and do not treat this release as suitable for thousands of users without load testing, shared rate limiting, and an independent review.


## v1.4.1 account controls
The panel stores account username/password hash in `/var/lib/idontmonitor/account.json` with mode 0600, separate from root-owned deployment configuration. Passwords are hashed with scrypt; password and username changes require the current password. Recent login attempts are stored in a bounded rolling audit file without storing credentials.

The in-panel port change uses a root-owned helper and a sudoers rule limited to that helper. To permit this narrowly scoped operation, `NoNewPrivileges` is disabled for the application service in this release. This is a security trade-off; review the sudoers rule and helper before production deployment. The helper accepts only ports 20000–60000 and updates the Caddy upstream when applicable. Firewall rules are not opened automatically.
