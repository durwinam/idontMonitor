# idontMonitor v2.2.3 — VPS Control Center & Inline Admin Flows

- Fixed VPS Management navigation and added live VPS telemetry with safe fallbacks.
- Enabled secure root VPS password changes from the web panel and Telegram admin bot.
- Added Telegram VPS reboot with explicit confirmation.
- Converted Telegram callback navigation to edit existing messages and added back/cancel controls.
- Improved theme consistency and responsive VPS/login layouts.

Security notes: root password changes require authenticated panel access or a configured Telegram admin. Telegram password messages are deleted on receipt where Telegram permits, and the password is kept only in worker memory until confirmation. Avoid using this flow in groups; use a private chat with the bot.
