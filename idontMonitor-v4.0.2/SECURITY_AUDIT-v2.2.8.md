# Security audit notes — idontMonitor v2.2.8

This release carries forward the v2.2.7 static review and adds focused tests for Telegram keyboard serialization, supplied custom emoji IDs, and theme-aware surface styling. No live VPS install or authenticated Telegram send was available in this build environment, so this report does not claim live behavior was verified.

## Focused checks
- Telegram buttons are styled centrally at send/edit time using Bot API 9.4 `style` values: `primary`, `success`, and `danger`. Older Telegram clients may ignore the color styles.
- Keyboard constants are copied before styles are attached, preserving shared layouts and callback actions.
- Custom emoji entities use UTF-16 offsets and only attach to emoji markers present in the message. If Telegram rejects custom entities, the existing Unicode fallback remains active.
- CPU/RAM/Disk labels now consistently include the mapped emoji characters in Persian and English resource messages.
- The theme variables now govern tunnel cards, traffic surfaces, terminal output, inputs and the mobile top bar, in addition to existing cards and panels.

## Limitations
- Custom emoji rendering depends on the IDs being valid and matching Telegram's emoji alt values, the bot owner meeting Telegram's Premium eligibility requirements, and the client supporting the feature. Live rendering must be confirmed with the configured bot.
- Button colors require Telegram Bot API 9.4-compatible client support; the server cannot force older clients to render colored buttons.
- CSS checks and automated tests do not replace visual testing in browsers and mobile Telegram clients.
