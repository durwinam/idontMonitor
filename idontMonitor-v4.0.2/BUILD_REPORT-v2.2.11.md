# Build report — idontMonitor v2.3.0

## Scope
- Fixed literal `\\n` sequences in the Persian server-status message so lines render correctly.
- Added a single-button final row: “لینک ورود به پنل” / “Open panel link”.
- Panel URL resolves from `IDM_PANEL_URL`, or from the VPS public IP with configured `IDM_PUBLIC_HOST`, `IDM_WEB_PORT` / `WEB_PUBLIC_PORT` and `IDM_PANEL_SCHEME` settings. It does not rely on a stale `serverip` value.
- Applied keyboard colors by row position: single-button rows red; paired rows first/right-side button blue and second/left-side button green in the Persian RTL layout.
- Retained Premium custom emoji IDs and Unicode fallback behavior.

## Validation
- Python compilation passed.
- Installer shell syntax checks passed.
- Full test suite passed.
- Live Telegram delivery and public IP endpoint reachability were not tested in this build environment.

## Scope protection
Monitoring calculations, network counters, tunnel detection, reboot/password flows, web panel routes and update logic were not intentionally changed.
