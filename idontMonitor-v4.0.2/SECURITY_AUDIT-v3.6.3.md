# Security audit — idontMonitor v3.6.3

- The web service continues to run as the dedicated unprivileged `idontmonitor` account.
- No ambient capabilities are granted to the application.
- The systemd capability bounding set is left at the system default so setuid sudo can perform its required UID/GID transition; sudo remains constrained by the dedicated sudoers command rule and the root-owned helper's strict argument validation.
- Do not replace this with `NOPASSWD: ALL`, a shell command endpoint, or a writable helper.
- Deployment verification must confirm helper owner `root:root`, mode `0750`, sudoers mode `0440`, `visudo -cf`, service unit state, and a disposable tunnel deletion.
