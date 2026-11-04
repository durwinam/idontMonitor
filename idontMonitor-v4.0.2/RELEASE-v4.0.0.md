# idontMonitor v4.0.0

## Highlights
- Dedicated Anti-DDoS Shield dashboard with live application request-rate observations, top source rates and anomaly timeline.
- Six-hour Telegram report based on stored samples: peak CPU, RAM used/total/percent, disk usage, active/inactive tunnels and recorded tunnel incidents.
- Minute telemetry collector persists resource samples and tunnel state transitions.
- Guarded automatic reboot when CPU **OR** RAM pressure exceeds 90% continuously for 120 seconds. Telegram warning, 15-second grace period, final pressure recheck and 30-minute cooldown.

## Safety and scope
- Shield telemetry does not automatically block IPs. High request volume may be legitimate; automatic blocking is intentionally off by default.
- Host-level application telemetry cannot detect or mitigate attacks that saturate the upstream network link. Use provider/CDN mitigation for volumetric DDoS.
- Automatic reboot can interrupt all active sessions and tunnels. It is enabled by the installer as explicitly requested. A cooldown and sustained-pressure requirement reduce reboot-loop risk.
- Six-hour peak CPU reporting requires collector history; first report after installation may indicate insufficient sample coverage.

## Upgrade
Run the v4.0.0 installer from the extracted release archive as root. Existing configuration and application state are backed up by the installer before upgrade.
