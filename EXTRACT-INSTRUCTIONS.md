# Safe extraction — idontMonitor v2.2.4

This archive intentionally contains one top-level directory, `idontMonitor-v2.2.4/`.

## Safe manual extraction

```bash
sudo install -d -m 0755 /opt/idontmonitor-source
sudo unzip idontMonitor-v2.2.4.zip -d /opt/idontmonitor-source
cd /opt/idontmonitor-source/idontMonitor-v2.2.4
```

The files are source files only. Extracting does **not** install or start the service.
To install, review the README and then run the installer from this directory:

```bash
sudo bash ./install.sh
```

The installer installs the application under `/opt/idontmonitor` and creates the required service/configuration paths. Do not extract the archive directly into `/`, `/root`, or `/etc`.
