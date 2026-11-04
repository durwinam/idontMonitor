# Security notes — idontMonitor v3.1.0

- Analyzer and mutation APIs require the existing authenticated session.
- Process stop requires explicit confirmation, refuses PID 1/root-owned processes and protected process names, and compares `/proc/<pid>/stat` start ticks to reduce PID-reuse risk. SIGTERM may still interrupt a user application; bulk action requires two confirmations.
- File deletion accepts only fixed managed log basenames, rejects symlinks and paths outside the resolved managed directory, and is audit-logged. It does not scan or delete OS, Docker, database, or arbitrary application files.
- Endpoint ping is bounded and uses a validated host extracted from config. ICMP is not proof of tunnel data-plane health.
- Stage-test process actions and log deletion before enabling operational use.
