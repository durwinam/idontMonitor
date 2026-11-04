# Build report — idontMonitor v3.6.3

## Root cause
`systemd/idontmonitor.service` contained `CapabilityBoundingSet=` with an empty value. systemd applies that bounding set to descendants, including `sudo`; sudo therefore lacked the capabilities needed to switch to root UID/GID. The UI's exact error (`unable to change to root gid` followed by `error initializing audit plugin sudoers_audit`) is consistent with this restriction.

## Change
- Removed the empty capability bounding set.
- Kept `User=idontmonitor`, `Group=idontmonitor`, `NoNewPrivileges=false`, and `AmbientCapabilities=` empty.
- Kept privilege escalation restricted to `/usr/local/sbin/idontmonitor-ops` with its argument validation and sudoers allowlist.
- Added a regression test to reject an empty `CapabilityBoundingSet=` in the service unit.

## Verification
See final test output at build time. End-to-end sudo and actual BackPack tunnel deletion still require a disposable tunnel on the user's VPS.
