# idontMonitor v3.6.3

## Fixed
- Corrected systemd capability bounding that blocked sudo's setuid/setgid transition. This was the direct cause of `unable to change to root gid` and `error initializing audit plugin sudoers_audit` during BackPack tunnel deletion.
- Kept the web process running as `idontmonitor`; no ambient capabilities are granted. Privileged operations still go through the fixed root-owned helper and its allowlisted sudoers policy.

## Verification boundary
- Regression tests and static checks validate the unit policy and helper invocation. The final delete must still be exercised against a disposable tunnel on the target VPS because this build environment cannot reproduce the VPS's systemd/sudo runtime.
