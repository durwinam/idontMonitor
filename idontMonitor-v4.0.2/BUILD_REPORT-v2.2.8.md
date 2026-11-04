# Build report — idontMonitor v2.2.8

Base: the prior v2.2.7 source package.

## Changes
- Telegram inline keyboards now receive Bot API 9.4 `style` fields through a single serializer used by both send and edit operations.
- Restored the stable five-row menu arrangement (single, pair, single, pair, pair) and preserved callbacks.
- Added supplied reboot/cross emoji IDs and fixed CPU/RAM/Disk markers so custom-emoji entities are placed over the intended emoji characters in both languages.
- Expanded theme-aware semantic colors for dedicated tunnel cards, aggregate and per-tunnel traffic boxes, forms, terminal/log boxes, and mobile navigation.
- Updated app/API/installer version metadata and static asset cache-busting to v2.2.8.

## Validation
- Project tests: 23 passed (including Telegram style serialization and custom-emoji entity regression checks).
- JavaScript syntax: `app.js`, `operations.js`, `telegram-bot.js`, `i18n.js` passed Node syntax checks.
- Bash syntax: `install.sh` and `scripts/idontmonitor-ops` passed.
- Python syntax for the updater passed `py_compile`; compileall could not write bytecode files in the mounted source directory, so it is not counted as a full compileall pass.
- ZIP/TAR integrity and required source files are verified during packaging.

## Not performed
- No live VPS upgrade, visual browser session, or authenticated Telegram message send was available. Colored button display and Premium emoji rendering must be confirmed on a Bot API 9.4-compatible Telegram client with a properly eligible bot owner and valid custom emoji IDs.
