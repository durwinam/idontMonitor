## v1.7.6
- Rebuilt icon and full logo directly from the user-provided IMG_2226 artwork.
- Removed only the connected white background, preserving enclosed white lettering and highlights.
- Unified logo sizing, containment, and cache-busting across login, sidebar, mobile navigation, and boot screen.

# Changelog

## 1.7.3
- Added a dedicated Speed Test page in the sidebar.
- Added authenticated, rate-limited server-side latency, download, upload and ICMP packet-loss test phases using a fixed external provider.
- Added animated phase visualization and clear unknown/unavailable states; no synthetic measurements are displayed.
- Existing configuration, credentials, path, port and traffic state are not intentionally rewritten by application-code changes.

## v1.7.3 — Visual identity & motion polish
- Replaced the compact brand mark with a dedicated idontMonitor server-monitoring logo mark.
- Unified navigation SVG stroke style and added consistent icon containers.
- Added animated chart glow/sweep and subtle card entrance motion, respecting reduced-motion preferences.
- Refined the Network Pulse loading screen with a cleaner logo mark, larger orbits, and breathing core ring.

# Changelog

## v1.7.3
- Make Network Pulse loading screen prominent and ensure it remains visible for a short minimum duration after first successful telemetry.
- Add consistent dedicated SVG glyphs for CPU, RAM and disk metrics.
- Preserve existing endpoint, credentials, port, path, protocol and stored telemetry configuration during upgrades.

# Changelog

## v1.7.3 — Safe Upgrade & Responsive Login
- Fixed the login layout at tablet and mobile widths to use a centered single-column layout and prevent horizontal overflow.
- Upgrades now reuse the installed transport, application port, bind address, domain/IP and install metadata instead of prompting for a new panel type or selecting a random port.
- Refuse an upgrade if existing configuration metadata is missing or ambiguous, rather than guessing connection settings.
- Preserve the existing Caddy reverse-proxy configuration on upgrades; do not append duplicate site blocks.
- Preserve config, credentials, session secret, custom panel path, environment settings and traffic state.

# Changelog

## 1.7.3
- Added original idontMonitor logo asset and animated Network Pulse boot screen that dismisses after successful telemetry.
- Added live RX/TX throughput cards with bytes/s and bits/s conversion based on real kernel counter deltas and actual sample interval.
- Added recent measured throughput graph and explicit interface/sample diagnostics.
- Preserved existing authentication, account settings, traffic allowance, and security flows.


## 1.5.0
- Hardened traffic state updates with cross-process locking.
- Added bounded 24-hour minute-bucketed metrics history API.
- Added explicit network sample and interface selection metadata.
- Prevented newly observed interfaces from contributing their pre-observation counters.
- Preserved binary units and existing account/security workflows.

# Changelog

## 1.4.1
- Rebuilt Settings into a Theme Studio with seven selectable visual themes.
- Added authenticated username changes and password resets with current-password verification and scrypt hashing.
- Added a rolling login audit trail and a Security Center view of the latest three login attempts.
- Added a guarded in-panel high-port change workflow through a root-owned helper and narrowly scoped sudoers rule; HTTPS proxy upstream is updated when applicable.
- Kept traffic accounting informational and documented its limitations.
- Added mobile-friendly theme cards and account controls.


## v1.4.1 — Visual and accounting redesign
- Rebuilt the web panel visual system with a new dark operations-console design, cleaner spacing, improved responsive navigation, and clearer information hierarchy.
- Reorganized the UI around Overview, Resources, Network & Traffic, Security Center, and Settings.
- Network accounting now prefers the interface(s) associated with the default IPv4 route to reduce double-counting caused by virtual bridges and veth interfaces. If the route cannot be detected, it falls back to a conservative interface filter and exposes the selected interface names in the API.
- Preserved binary display units: 1024 MB = 1 GB and 1024 GB = 1 TB. Internal calculations remain in bytes.
- Updated version metadata and documentation.

## Important accounting limitations
- Traffic tracking begins with the first sample; historical usage before installation is not recoverable from local counters.
- A route interface is a best-effort approximation of billable provider traffic. Providers may account traffic differently, and some routed or multi-interface setups require explicit interface selection or provider API integration.
- Settings and this panel are a single-admin per-install deployment, not a central multi-tenant hosted control plane.


## v1.7.3
- Rebuilt the login screen as a responsive, polished secure-access experience.
- Added accessible password visibility toggle, loading state, and inline error handling.
- Replaced dashboard Unicode symbol icons with inline SVG icons.
- Kept existing authentication endpoints and core monitoring behavior unchanged.

## v1.7.3
- Removed conflicting duplicate Speed Test API/JavaScript implementations that could cause the UI to call a different endpoint than the server exposed.
- Added bounded, real download/upload measurements with per-window throughput samples and a live chart.
- Improved network failure diagnostics to expose the exception class/message and common outbound DNS/TLS/443 causes.
- Tuned test phases for an approximately 20-second run; actual duration depends on network response and endpoint availability.
- Reduced the oversized boot logo/orbit composition and kept the sidebar brand compact.


## 1.7.3
- Fixed the missing `setGauge` JavaScript function that stopped the speed test after the first successful measurement.
- Added animated CPU, RAM, disk and swap circular utilization gauges using live metrics and actual capacities.
- Corrected logo mark asset to remove the clipped wordmark from the icon-only image; enforced contain sizing across boot/sidebar/login contexts.
- Preserved authenticated Cloudflare transfer testing and surfaced phase errors in the connection report.


## v1.8.0 — Architecture, Persian UI and Project Footer

- Added language selector in the dashboard top bar and login page.
- Added Persian translation catalog and RTL styling with Vazirmatn font declaration.
- Added a shared dashboard footer with GitHub and Telegram SVG links and `durwinam` copyright.
- Rewrote README in Persian with project logo at the top, setup guidance, architecture map, tests, and security notes.
- Documented the current architecture and safe staged-refactor direction.
- Preserved the current backend behavior and operational configuration defaults.

## v1.8.1 — Update Center & localization polish

- Added a dedicated Update Center with GitHub release checks, installed/latest version comparison, release notes, live update status, and a glass-style release notification.
- Added a constrained root-owned VPS updater: release ZIP asset required, stable semantic version check, SHA-256 digest verification, archive path validation, Python syntax check, dependency installation before activation, health check, and automatic release-symlink rollback on health-check failure.
- Added CLI update status checks and `sudo idontMonitor update` to run the server-side updater.
- Added custom theme-aware language selector styling, browser-language detection, and `/locales` static serving so locale dictionaries load correctly.
- Removed the runtime Google Fonts import and added support for a locally served Vazirmatn font. The installer attempts to install the distro font package and bundle it locally.
- Corrected the official GitHub repository URL in the installer and updated version metadata to 1.8.1.

### Update safety notes

The web updater requires a published GitHub Release with a matching `idontMonitor-vX.Y.Z.zip` asset and a GitHub-provided SHA-256 asset digest. If the asset or digest is missing, it refuses to change the installed release. Runtime configuration and monitoring state remain outside versioned releases.
