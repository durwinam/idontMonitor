# Source audit notes for v1.9.9

The integration was designed after inspecting the supplied `idontMonitor-v1.8.1.zip`, `C-Tunnel-main.zip`, `BackPack-main(1).zip`, and `paqet-tunnel-main(1).zip` archives.

## idontMonitor v1.8.1

- Kept the existing dashboard, authentication, metrics, security checks and update center in place.
- Added operations routes in a separate module rather than expanding the main route file further.
- Kept all mutating system actions behind a root-owned argument-validating helper and required explicit confirmation from the browser.
- The updater validates the new module and stages the helper/sudoers policy before switching the active release.
- Added bounded rotating application logs and tests for the new security boundary.
- Fixed the remote `bash -c` install path so an unset `BASH_SOURCE[0]` does not cause a shell error or a false local-directory assumption.

## C-Tunnel

- The supplied source includes systemd templates `ctunnel@.service` and `ctunnel-engine@.service`; the detector therefore recognizes instantiated `ctunnel@NAME.service` and `ctunnel-engine@NAME.service` units.
- The panel does not install C-Tunnel, rewrite its configuration, or assume that an interface is attributable to a tunnel without a verified mapping.

## BackPack

- The supplied project includes distinct tunnel and management components. The detector is intentionally restricted to `backpack-NAME.service` instances and explicitly excludes management units such as `backpack-monitor.service`, `backpack-webui.service`, and `backpack-proxy.service`.
- No unsupported CLI or undocumented metrics endpoint is invoked. If a verified per-tunnel interface mapping is not available, per-tunnel traffic is shown as unavailable.

## Paqet

- The supplied archive is an installation script, not the complete tunnel-engine source tree. The integration does not build, download, install, or reconfigure Paqet.
- Detection uses resulting systemd unit names conservatively and excludes relay/watchdog helper units (`paqet-relay.service`, `paqet-auto-reset.service`, and `paqet-tunnel.service`) from tunnel counts and privileged service actions.

## Remaining integration constraints

- The UI can evaluate local CPU/RAM/disk thresholds on refresh, but no Telegram/email push provider is configured in this source; no external delivery is claimed.
- A VPS cannot reliably alert an external recipient while the VPS itself is down without an independent external monitor. This release does not claim to provide that capability.
- SSH management is not an arbitrary remote shell. The “Web Terminal” is a fixed, read-only local diagnostic command palette. Privileged actions are separately allowlisted.
- Plugin architecture is a constrained module boundary and design contract, not an arbitrary third-party code loader.
