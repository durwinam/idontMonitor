# Build report — idontMonitor v2.2.9

Base: v2.2.8 source.

## Fix
The previous implementation only handled raised exceptions. Telegram API wrappers may return an `{ok:false, description:...}` JSON result instead, so the Unicode fallback was skipped. The sender now handles both response shapes, retries with the same original text without `entities`, and caches an explicit Premium-eligibility rejection for the worker lifetime. Invalid entity IDs fall back per message without disabling future custom emoji attempts. HTTPError bodies are read once so the Premium restriction can be detected reliably.

## Verification
- Automated test suite: 26 passed.
- JavaScript syntax and installer/operations shell syntax checks are run during packaging.
- No live Telegram token/account was available to verify actual rendering. Premium eligibility is detected from Telegram's response rather than a guessed owner flag.
