# idontMonitor v2.3.3

## C-Tunnel compatibility update

Reviewed the uploaded C-Tunnel source at version **0.2.5** and adjusted idontMonitor's tunnel integration only where the new source behavior required it.

- RX/TX now sums the exact base C-Tunnel interface and ECMP lane interfaces (`.1`–`.7`) when present. Unrelated `ct-*` interfaces are excluded.
- The delete action now handles C-Tunnel's shared systemd template units correctly: it stops and disables the selected instance without deleting the shared template or tunnel configuration.
- A failed C-Tunnel stop/teardown now fails closed; idontMonitor does not disable the instance or remove its record after a failed teardown.
- Watchdog service/timer units remain excluded from tunnel-instance counts; they are support services, not tunnel data-plane instances.
- Other tunnel types, monitoring calculations, themes, Telegram keyboard design, and panel-link resolution were not intentionally changed.

## Validation

- Automated tests: **36 passed** (`python -m pytest -q`).
- `bash -n install.sh scripts/idontmonitor-ops`: passed.
- Python compile check: passed.
- ZIP/TAR.GZ integrity and SHA-256 verification performed during packaging.
- No live VPS, kernel tunnel teardown, or Telegram delivery test was possible in this build environment.
