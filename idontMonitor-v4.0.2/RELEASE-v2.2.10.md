# idontMonitor v2.3.0

## Telegram Premium custom emoji — complete UI coverage
- Uses all 17 known supplied custom emoji IDs in the shared mapping and mapped status indicators.
- Uses Bot API 9.4 `icon_custom_emoji_id` for every inline button: main menu, language selection, back/cancel, password confirmation and reboot confirmation.
- Keeps button colors, callback data, and five-row layout unchanged.
- Sends custom emoji entities in message text and custom icons in inline keyboards when Telegram accepts them.
- On explicit Telegram rejection, retries using original Unicode emoji labels and the same actions/styles without custom IDs.
- Premium eligibility is learned from Telegram's response; invalid IDs trigger a per-message fallback rather than permanently disabling custom emoji.
- Keeps web-panel themes and box colors unchanged from v2.2.9.

## Validation
- Added regression tests for all 17 IDs, inline button icon support, color/layout preservation, and Unicode fallback.
- 30 automated tests passed.
- Live Telegram display must still be confirmed with a real bot owner account and current Telegram clients.
