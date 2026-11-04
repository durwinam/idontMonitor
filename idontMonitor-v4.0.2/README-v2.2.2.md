# idontMonitor v2.2.2

## Telegram Bot configuration

This release adds a **Telegram Bot** page to the authenticated web panel. Configure a BotFather token and between one and three unique numeric Telegram user IDs. The panel verifies the token with Telegram's `getMe` API before saving settings. The token is written to `/var/lib/idontmonitor/telegram-bot.json` with mode `0600` and is never returned by the settings API.

A separate `idontmonitor-telegram-bot.service` performs long polling without third-party Python packages. Only configured user IDs can use bot commands. Unauthorized users who send `/start` receive: “You do not have access to this bot.” The starter menu currently includes server status and help. Existing monitoring and tunnel-management behavior is retained.

## Upgrade / install

Extract the source archive and run:

```bash
sudo bash install.sh
```

For an existing installation, follow the installer's preflight checks and review its backup and final service status. The installer enables the Telegram worker; until a token and at least one admin ID are saved in the web panel, it remains idle.

## Security notes

- Use HTTPS for the web panel and a strong panel password.
- Never share the bot token. If it is exposed, revoke/regenerate it via BotFather.
- Admin IDs are numeric Telegram **user IDs**, not usernames or group IDs.
- The token is stored locally with restrictive file permissions; root and the service account can access it.
- Bot API traffic requires outbound HTTPS access to `api.telegram.org`.
- This release does not expose arbitrary shell execution through Telegram.

## Validation

Source syntax checks (`compileall`, `bash -n`, `node --check`) and all source-level test scripts passed in the build environment. Live Telegram token validation, actual Telegram delivery, service installation on a real VPS, and browser-level testing were not performed here.
