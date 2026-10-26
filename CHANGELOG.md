# Changelog

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
