## [2.3.4] - 2026-10-30
- Updated C-Tunnel compatibility for release 0.2.5.
- Aggregate RX/TX counters across the exact C-Tunnel base interface and source-defined ECMP lane interfaces (`.1` through `.7`), without counting unrelated interfaces.
- Fixed C-Tunnel instance removal: because C-Tunnel uses shared systemd template units, idontMonitor now stops and disables only the selected instance instead of expecting a standalone unit file or deleting the shared template.
- If C-Tunnel teardown fails, the instance is not disabled and its configuration/state record is preserved, matching C-Tunnel 0.2.5's safe teardown behavior.
- Bumped runtime, installer, UI, and package metadata to 2.3.4; existing monitor calculations and other tunnel integrations remain unchanged.

## v2.3.0\n- Full custom emoji icon support for all inline buttons using Bot API 9.4.\n- Complete registration/use of 17 known custom emoji IDs, including status indicators.\n- Unicode-only fallback keyboard preserves original emoji labels when Telegram rejects custom emoji.\n\n## v2.3.0
- Fixed Unicode fallback when Telegram returns a JSON `ok:false` response for rejected custom-emoji entities, as well as when it raises HTTP errors.
- Automatically switches to the original Unicode emoji glyphs when Telegram reports that the bot cannot use Premium custom emoji; retains custom-emoji attempts for later messages when an individual ID/entity is invalid.
- Added regression tests for both response shapes, preserving the same visible emoji glyphs and Premium-capability detection.
- Retained styled Telegram inline buttons, the stable five-row layout, and theme-aware surfaces from v2.2.8.

## [2.2.6] - 2026-10-28

- Added authenticated, single-use server-side CAPTCHA for root VPS password changes, bound to client IP and login session, expiring after three minutes.
- Added rate limits for CAPTCHA issuance and password-change attempts.
- Localized password-change CAPTCHA controls and common operation errors for Persian and English.
- Added Telegram custom emoji entities for mapped glyphs with Unicode fallback after explicit Telegram entity rejection; IDs can be overridden with `IDM_TELEGRAM_CUSTOM_EMOJI_IDS`.
- Added baseline HTTP security headers and `no-store` on API/login responses.
- Preserved monitoring, traffic accounting, tunnel operations, updater, and existing themes.

# Changelog

## [2.2.5] - 2026-10-28
- Added a server-validated, expiring one-time arithmetic CAPTCHA to administrator login.
- CAPTCHA challenges are stored in the signed server session, compared in constant time, and refreshed after failed submissions.
- Added rate limiting for challenge generation and kept the existing login attempt limits and audit trail.
- Updated version metadata and release packaging checks.

## v2.2.4 — VPS Control Center & Inline Admin Flows
- Fixed VPS Management navigation so the page is actually reachable from the sidebar.
- Added live host summary cards with explicit fallback states.
- Enabled authenticated root VPS password changes through a narrowly allowlisted root-owned helper.
- Added Telegram inline menu actions for root password change and reboot confirmation.
- Reworked Telegram callback navigation to edit the existing message and include back/cancel controls.
- Improved mobile VPS layouts and theme-aware surface styles.

## 2.2.2

- Improved narrow-screen layout and prevented horizontal overflow in the dashboard and login page.
- Standardized dashboard surfaces to follow the selected theme palette.
- Corrected Persian navigation label for VPS Management and adjusted navigation badges.
- Expanded Telegram bot with functional admin-only buttons for status, resources, network counters, tunnel services, and help.

# Changelog

## 2.2.1
- Add a dedicated Telegram Bot configuration page in the web panel.
- Verify the bot token with Telegram before saving it; never return the token to the browser.
- Support up to three unique numeric Telegram admin IDs.
- Add a separate restricted systemd long-poll worker; unauthorized users are denied on /start.
- Install and enable the Telegram worker through the standard installer.

# Changelog

## 2.2.0
- Added a dedicated VPS Management workspace with protected reboot confirmation.
- Added VIP Midnight Emerald Glass theme with shared theme tokens, animated glass surfaces, and reduced-motion support.
- Added responsive animated cards and a reusable secure-action modal foundation.
- Preserved the existing monitoring pages and tunnel manager.
- VPS OS password change is intentionally not wired to an unsafe shell command; it requires a separately audited root-owned password helper before it can be enabled.

# Changelog

## 2.2.0

- Fixed Release updater to prefer the exact `idontMonitor-vX.Y.Z.tar.gz` asset and validate its GitHub-provided SHA-256 digest when available.
- Added a tag-archive fallback only when the release has no matching project asset.
- Hardened archive extraction against special files, traversal, and oversized expanded content.
- Made release directory creation staged and refused in-place overwrite of an existing version directory.
- Synchronizes updater, operations helper, systemd unit, and CLI version during update, with rollback backups.
- Fixed the CLI menu's stale update message and expanded usage help.
- Refuses installer in-place overwrite when the same version is already installed.
- Expanded update tests and documentation.


## v2.2.0
- Release-based updater now uses the GitHub release tag source archive (`tar.gz`) instead of requiring a ZIP asset.
- Added an explicit main-branch update path for development builds.
- Improved version consistency across source, installer, CLI, and release metadata.
- Kept safe port selection on fresh install and preserved existing port during upgrades.


## 1.9.9
- Added BackPack native metrics snapshot reader for per-instance `bytes_in` / `bytes_out` where snapshots are present beside recognized configuration paths.
- Added C-Tunnel interface mapping based on its source-defined `ct-<name>` device naming.
- Kept systemd IPAccounting as a per-unit source and Paqet mapping conservative unless an exact interface is present.
- Improved traffic source labels and unknown-data handling; totals sum only measurable independent tunnel instances.
- Reworked boot screen sizing and exit behavior for dynamic mobile viewports.
- Applied branded styling to form controls across all pages.

## v1.9.9
- Redesigned compact loading screen with safer mobile viewport handling.
- Added best-effort protocol/config metadata chips to tunnel cards (labels only; no secrets exposed).
- Refined tunnel card visual hierarchy and RX/TX panels.
- Fixed RTL toggle thumb direction to keep the switch inside its track.
- Versioned static asset cache keys to v1.9.9.

## 1.9.9
- Fix BackPack metrics path resolution using the exact config path from systemd ExecStart.
- Detect tunnel protocol from the actual service config path.
- Theme-aware tunnel card colors.

## v2.2.4
- Added per-administrator Telegram language selection with Persian/English menu and in-bot language switching.
- Added live CPU utilization percentage to Telegram status and resource summaries.
- Expanded Persian localization fallbacks for login and VPS management.
- Improved iPhone safe-area layout, RTL input alignment, and reduced-motion behavior.
