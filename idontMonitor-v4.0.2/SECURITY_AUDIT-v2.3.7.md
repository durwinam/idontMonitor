# Security review — idontMonitor v2.3.7

- New analyzer endpoints require an authenticated panel session.
- RAM analyzer is read-only and returns only five selected non-obvious system processes; it exposes no kill endpoint.
- Disk analyzer reads only the explicitly named `idontmonitor.log` and numbered rotations under `IDONTMONITOR_LOG_DIR` (default `/var/log/idontmonitor`). It rejects symlinks, non-regular files, and paths that resolve outside the log directory. It exposes no delete endpoint.
- No automatic cleanup was added. This avoids deleting data while safe rotation and open-file behavior are not yet verified.
- This is a source-level review, not a live production security certification.
