# idontMonitor v2.2.9

## Telegram Premium emoji fallback
- Detect both raised HTTP errors and JSON `{ok:false}` responses from Telegram when custom emoji entities are rejected.
- Retry the same message using the exact original Unicode emoji glyphs, preserving CPU/RAM/Disk and other icons.
- If Telegram explicitly reports a Premium eligibility restriction, cache the unsupported capability for the worker lifetime and avoid repeatedly sending rejected entities.
- Invalid/custom emoji entity errors trigger a Unicode retry without permanently disabling custom emoji, allowing corrected IDs to work on subsequent messages.
- Premium capability is determined from Telegram's actual response; Bot API does not provide a reliable direct flag for the bot owner's Premium status.

## Validation
- Added regression tests for JSON API error fallback, unchanged Unicode glyphs, Premium restriction caching, and per-message fallback for invalid IDs.
- No live Telegram account/token was available to verify actual rendering on Telegram clients.
