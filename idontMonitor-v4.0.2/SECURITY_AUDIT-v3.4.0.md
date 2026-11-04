# Security Audit — idontMonitor v3.4.0

- RAM inventory is read-only. Existing stop action restrictions remain; protected/root processes are not eligible.
- Process attribution reads only `/proc` metadata and walks at most five parents, preventing unbounded traversal.
- Disk breakdown is bounded by existing entry/depth limits and refuses symlinks. No service folder or database content can be deleted from this analyzer.
- BackPack health is sourced from the per-instance native snapshot; no inference from ICMP is used to override the engine's own state.
- C-Tunnel config and reverse/normal endpoint handling remain unchanged from the audited v3.3.0 logic.
- No secrets, tunnel tokens or credentials are exposed in new UI fields.
- Production validation on a staging VPS is still required.
