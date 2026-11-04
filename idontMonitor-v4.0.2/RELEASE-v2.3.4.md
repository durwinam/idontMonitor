# idontMonitor v2.3.4

## Security and reliability fixes
- Fixed the password-reset failure `ValueError: [digital envelope routines] memory limit exceeded` by increasing the explicit OpenSSL scrypt memory ceiling to 512 MiB in password reset, password change, initial credential generation, and password verification.
- Kept scrypt work factors (`N=32768`, `r=8`, `p=1`) unchanged; the configured maximum is a ceiling, not a pre-allocation.
- Added a regression test that actually derives a scrypt digest with the reset parameters and checks that runtime and installer caps stay aligned.
- Updated version metadata and browser asset cache keys to 2.3.4.
- No monitoring formulas or tunnel traffic calculation logic intentionally changed.

## Validation
- Full pytest suite and Python/shell/JavaScript syntax checks are part of the build verification.
- This is source-level validation, not a live VPS test or external penetration test. The password reset should still be verified on the target host after backing up configuration and account state.
