# Security and behavior audit — idontMonitor v2.2.9

## Scope of this release
- Reviewed the Telegram worker's custom emoji request/response handling and the related automated tests.
- The worker never logs the bot token or message content for emoji fallback.
- A Telegram entity error retries the message with its original Unicode glyphs and without custom entities.
- Premium ineligibility is cached only when the returned description explicitly indicates a Premium restriction; invalid IDs do not permanently disable attempts for later messages.
- HTTPError bodies are parsed once to avoid consuming the response before capability detection.

## Limitations
- The Bot API does not expose a reliable direct flag for the bot owner's Premium subscription. This release detects eligibility from Telegram's actual response rather than assuming from the bot profile.
- No live bot token or Premium/non-Premium owner account was available for end-to-end Telegram rendering tests. Actual display must be confirmed after deployment.
- This targeted audit is not a full third-party dependency or runtime security audit.
