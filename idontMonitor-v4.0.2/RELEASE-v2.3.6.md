# idontMonitor v2.3.6

## Fixes
- Reworked responsive layout for the Tunnel Manager cards on small screens: stable two-column RX/TX cells, wrapping protocol/config chips, safe long systemd unit names, and properly sized action buttons.
- Removed accidental opaque backgrounds from tunnel-card inner layout rows so the card contents no longer render as disconnected black bands.
- Installer completion now always prints the username actually stored in the resulting config, including after an existing-install path; existing credentials remain preserved during upgrades.
- Credential reset continues to display the username after the reset and displays the generated password only once.
- Bumped app version and static asset cache-busting values to 2.3.6 / 2360.

## Preserved
- No intended changes to CPU, RAM, disk, host network, or tunnel traffic measurement logic.
- Existing username/password are preserved during upgrade/reinstall when an existing config is detected.
- HTTP login behavior and the localized 5-second HTTPS recommendation remain as in v2.3.5.
