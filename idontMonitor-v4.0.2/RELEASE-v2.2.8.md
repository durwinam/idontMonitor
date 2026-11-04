# idontMonitor v2.2.8

## Telegram bot
- Added Bot API 9.4 inline button styles (`primary`, `success`, `danger`) centrally at send/edit time, without mutating shared keyboard definitions. Older Telegram clients may ignore visual styles.
- Restored the approved five-row inline keyboard order: single, pair, single, pair, pair.
- Corrected CPU/RAM/Disk emoji markers in English resource/status output so mapped custom emoji entities can actually match the displayed characters.
- Applied the supplied reboot and cross custom-emoji IDs. Custom emoji rendering still depends on valid IDs, a Premium-enabled bot owner under Telegram's current rules, and a compatible Telegram client; explicit API rejection falls back to Unicode.

## Web panel
- Centralized semantic raised/inset surface colors and applied them to dedicated tunnel cards, traffic aggregate/cells, controls, terminal panels, and mobile top bar.
- Theme palette now updates the additional semantic surface variables when switching themes.

## Validation
- Added regression tests for button styles/layout, supplied emoji IDs and theme-surface inheritance. Live Telegram rendering requires a configured bot token and an eligible Telegram account, and was not simulated as a successful live send.
