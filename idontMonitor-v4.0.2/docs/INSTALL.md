# Installation notes

1. Ensure the VPS is Debian/Ubuntu with systemd.
2. For HTTPS, create DNS A/AAAA records pointing to the VPS public address and allow inbound TCP 80/443.
3. Review `install.sh` before running as root.
4. Run `sudo bash install.sh` and choose HTTP or HTTPS.
5. Save the generated admin password from the final installer screen.
6. Check `idontMonitor status`, `idontMonitor url`, and `journalctl -u idontmonitor`.

HTTPS mode checks that the domain resolves to the detected public IP before writing Caddy config. Caddy obtains/renews certificates automatically when public DNS and inbound port requirements are satisfied. DNS-only proxy/CDN modes can require additional configuration.
