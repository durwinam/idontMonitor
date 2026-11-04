# Build report — idontMonitor v2.3.4

- Source base: supplied `idontMonitor-v2.3.3.zip`.
- Version metadata, runtime/API version, CLI version, UI labels, browser cache keys, release notes, and packaging checks updated to 2.3.4.
- Password-reset OpenSSL scrypt memory ceiling raised from 128 MiB to 512 MiB without changing scrypt work factors.
- Added regression coverage that performs real scrypt derivation.
- Monitoring formulas and tunnel metric calculations were not intentionally modified.

Validation results are recorded in the delivery response and the release test suite. Live VPS testing remains outstanding.
