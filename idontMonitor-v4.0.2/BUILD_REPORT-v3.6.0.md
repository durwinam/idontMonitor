# Build report — idontMonitor v3.6.0

## Implemented

1. **Log lifecycle fix:** active log cleanup is performed with the Python rotating handler lock. The handler is flushed, closed, the active path is cleared, and the handler is reopened to create a fresh file. Rotated allowlisted files are deleted separately. This prevents the old open-file-descriptor bug where a deleted log could remain unlinked while the process continued writing to it.
2. **Tunnel deletion fix:** verified C-Tunnel template instances are accepted even though systemd instances do not have their own unit file. The shared template must exist in a trusted systemd unit directory. BackPack/Paqet custom instances still require a regular, non-symlink custom unit file. The root helper continues to stop and disable supported instances without deleting their configuration/data.
3. **Restricted helper execution fix:** removed the incorrect unprivileged `os.access(X_OK)` check against a root-owned `0750` helper. The app validates regular-file/root-owner/owner-execute metadata, then uses `sudo -n` for execution. Installer and updater deploy the helper and validate sudoers with `visudo`.
4. **Analyzer UX:** native browser confirms/alerts were replaced with a branded responsive idontMonitor dialog/toast flow. RAM protected entries are visible as protected instead of silently omitting their action. Disk labels now describe clearing logs rather than deleting memory or service data.
5. **Version/cache metadata:** bumped to 3.6.0 and cache-busted static assets.

## Verification

- 63 pytest tests passed, including a regression test that verifies the active log file is recreated and accepts new log records after cleanup.
- Python compileall, JavaScript syntax checks, and shell syntax checks passed.
- No production VPS operations were executed.

## Remaining boundaries

- RAM process stop remains limited to eligible non-root processes; root/core/database/container services are protected intentionally.
- Tunnel removal applies to detected supported tunnel instances only. Shared templates, control planes, relay services, configuration and data are preserved.
- Disk cleanup is limited to the four named idontMonitor log files; it does not offer arbitrary directory/file deletion.
