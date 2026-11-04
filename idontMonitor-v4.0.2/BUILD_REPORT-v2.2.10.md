# Build report — idontMonitor v2.3.0

Base: idontMonitor v2.2.9 source.

## Implemented
- Registered all 17 known custom emoji IDs and retained environment-based overrides.
- Added Bot API 9.4 `icon_custom_emoji_id` to every inline button in the menu, language picker, back/cancel flows, and confirmation keyboards.
- Preserved existing button colors and the five-row layout.
- Kept original Unicode labels in a separate fallback keyboard. If Telegram rejects custom icons/entities, the sender retries without custom IDs and keeps the Unicode emoji and callback actions.
- Improved Premium restriction detection so an invalid ID is not automatically interpreted as an owner Premium restriction.
- Extended status/resource/network messages to use mapped custom emoji IDs in the message text.
- Updated runtime/release metadata to v2.3.0.

## Verification
- 30 automated tests passed.
- Python compile checks passed.
- Bash syntax checks passed for installer and operations helper.
- JavaScript syntax checks passed for web assets.
- ZIP/TAR archive integrity and required-file presence checks passed.
- Live Telegram rendering was not tested because no real bot token/owner account was available.
