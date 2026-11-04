# Build Report — idontMonitor v3.4.0

Source base: idontMonitor v3.3.0 plus supplied BackPack-main and C-Tunnel-main source archives.

Changes: RAM attribution/cgroup decoder and parent walk; BackPack native `connected` tri-state semantics; independent ICMP/native health messaging; bounded disk child breakdown; mobile analyzer UI refresh.

Tests: `pytest -q` — 59 passed; `python -m compileall -q app tests` — passed; `node --check static/operations.js` — passed; `node --check static/app.js` — passed; `bash -n install.sh` — passed.

Limits: No access to the user's live VPS. A timed-out ICMP probe cannot prove a tunnel is down. Disk scan is intentionally read-only except managed app logs. Unknown cgroup ownership remains unassigned rather than being guessed.
