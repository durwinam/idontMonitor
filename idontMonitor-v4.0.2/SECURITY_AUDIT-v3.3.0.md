# Security Audit — idontMonitor v3.3.0

- Endpoint parsing uses exact service instance names and canonical engine state/config paths; symlinks and oversized state/config files are rejected.
- BackPack native peer is accepted only from a fresh snapshot (<=90 seconds) with `connected=true`. Explicit disconnected state prevents stale static fallback.
- C-Tunnel reverse mode uses only its configured `tun_remote4` and exact `ct-<name>` interface; arbitrary `ct*` interfaces are not guessed.
- ICMP execution remains bounded to one packet and a short timeout. Interface argument is accepted only for a strict `ct-<name>` pattern.
- RAM inventory is read-only and now includes root-owned daemons for accurate attribution. Existing stop endpoint restrictions remain in place; root/system processes are not eligible.
- Disk directory scans remain bounded and skip symlinks. No service directory is deletable; cleanup is limited to managed application logs.
- No secrets, tunnel tokens, or credentials are emitted in analyzer output or new reports.
- No live VPS integration test was possible in this build environment; confirm actual engine snapshot paths and ping permissions on staging before production rollout.
