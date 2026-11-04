# Focused security review — idontMonitor v2.3.0

Scope: Telegram custom-emoji/button fallback changes and release packaging.

- Button icons are sent only through Telegram's documented `icon_custom_emoji_id` field; callback actions, callback data, color styles, and row order remain intact.
- Unicode fallback payloads are constructed from the original keyboard constants, so a rejected custom icon cannot remove the original glyphs or callback actions.
- No token, password, or credential was added to source or release metadata by this change.
- API rejection handling retries only when the response explicitly indicates custom-emoji/entity rejection; unrelated network/API errors are not silently treated as a Premium restriction.
- The worker does not query external services except the Telegram Bot API it already uses.

This is a focused review of the changed Telegram path, not a guarantee that every dependency or runtime behavior is malware-free. Live Telegram verification and a full dependency vulnerability scan require the deployment environment and bot credentials.
