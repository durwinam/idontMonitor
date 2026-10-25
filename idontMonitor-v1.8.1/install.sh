#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
VERSION="1.8.1"
REPO_URL="https://github.com/durwinam/idontMonitor"
INSTALL_DIR="/opt/idontmonitor"
CONFIG_DIR="/etc/idontmonitor"
STATE_DIR="/var/lib/idontmonitor"
LOG_DIR="/var/log/idontmonitor"
SERVICE="idontmonitor"

if [[ $EUID -ne 0 ]]; then echo "Run as root: sudo bash install.sh" >&2; exit 1; fi
if [[ ! -f "$(dirname "$0")/app/main.py" ]]; then echo "Run install.sh from the extracted project directory." >&2; exit 1; fi
EXISTING_INSTALL=0
if [[ -e "$INSTALL_DIR/current" || -L "$INSTALL_DIR/current" ]]; then
  EXISTING_INSTALL=1
  echo "Existing idontMonitor installation detected. Installing a new release while preserving config and state."
  # Create a protected rollback snapshot before touching code, packages or service settings.
  [[ -s "$CONFIG_DIR/config.json" && -s "$CONFIG_DIR/environment" && -s "$STATE_DIR/install-mode" ]] || {
    echo "Existing install metadata is incomplete; refusing upgrade before making changes." >&2; exit 1;
  }
  install -d -m 0700 /var/backups/idontmonitor
  UPGRADE_BACKUP="/var/backups/idontmonitor/idontmonitor-pre-v${VERSION}-$(date +%Y%m%d-%H%M%S).tar.gz"
  backup_items=()
  [[ -d "$CONFIG_DIR" ]] && backup_items+=("etc/idontmonitor")
  [[ -d "$STATE_DIR" ]] && backup_items+=("var/lib/idontmonitor")
  tar -czf "$UPGRADE_BACKUP" -C / "${backup_items[@]}" || { rm -f "$UPGRADE_BACKUP"; echo "Could not back up current config/state; refusing upgrade." >&2; exit 1; }
  chmod 0600 "$UPGRADE_BACKUP"
  echo "Protected pre-upgrade backup created: $UPGRADE_BACKUP"
fi

say(){ printf '\n\033[1;36m[idontMonitor]\033[0m %s\n' "$*"; }
fail(){ echo "ERROR: $*" >&2; exit 1; }
command -v apt-get >/dev/null || fail "This installer currently supports Debian/Ubuntu (apt)."
# Install the locally hosted Persian UI font (no runtime Google Fonts dependency).
apt-get update -qq || true
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq fonts-vazirmatn >/dev/null 2>&1 || true

PUBLIC_IP=""
DOMAIN=""
APP_PORT=""
APP_BIND_HOST=""

if (( EXISTING_INSTALL )); then
  # Safe upgrade mode: refuse to guess any connection setting. Preserve the
  # existing transport, port, domain/IP, URL path, credentials and state.
  [[ -s "$CONFIG_DIR/config.json" ]] || fail "Existing install detected but config is missing; refusing unsafe upgrade."
  [[ -s "$CONFIG_DIR/environment" ]] || fail "Existing install detected but environment is missing; refusing to change the panel port."
  [[ -s "$STATE_DIR/install-mode" ]] || fail "Existing install detected but install-mode metadata is missing; refusing to guess HTTP/HTTPS settings."
  MODE="$(sed -n 's/^MODE=//p' "$STATE_DIR/install-mode" | head -n1)"
  APP_PORT="$(sed -n 's/^IDM_APP_PORT=//p' "$CONFIG_DIR/environment" | head -n1)"
  APP_BIND_HOST="$(sed -n 's/^IDM_BIND_HOST=//p' "$CONFIG_DIR/environment" | head -n1)"
  DOMAIN="$(sed -n 's/^DOMAIN=//p' "$STATE_DIR/install-mode" | head -n1)"
  PUBLIC_IP="$(sed -n 's/^PUBLIC_IP=//p' "$STATE_DIR/install-mode" | head -n1)"
  [[ "$MODE" == "http" || "$MODE" == "https" ]] || fail "Existing transport is unknown; no settings were changed."
  [[ "$APP_PORT" =~ ^[0-9]{1,5}$ ]] && (( APP_PORT >= 1 && APP_PORT <= 65535 )) || fail "Existing panel port is invalid; no settings were changed."
  [[ "$APP_BIND_HOST" == "0.0.0.0" || "$APP_BIND_HOST" == "127.0.0.1" ]] || fail "Existing bind address is unknown; no settings were changed."
  if [[ "$MODE" == "https" ]]; then
    [[ -n "$DOMAIN" && -s /etc/caddy/Caddyfile ]] || fail "Existing HTTPS configuration is incomplete; no settings were changed."
  else
    [[ -n "$PUBLIC_IP" ]] || PUBLIC_IP="$(hostname -I | awk '{print $1}')"
  fi
  say "Safe upgrade: preserving ${MODE^^}, port ${APP_PORT}, bind ${APP_BIND_HOST}, domain/IP, credentials, URL path and state."
else
  say "Choose panel transport"
  PS3="Select 1 or 2: "
  select mode in "HTTP on server IP (not encrypted)" "HTTPS on a domain (automatic TLS)"; do
    case "$REPLY" in 1) MODE="http"; break;; 2) MODE="https"; break;; *) echo "Choose 1 or 2.";; esac
  done
fi

if [[ "$MODE" == "https" && $EXISTING_INSTALL -eq 0 ]]; then
  read -r -p "Domain (e.g. monitor.example.com): " DOMAIN
  DOMAIN="${DOMAIN,,}"
  [[ "$DOMAIN" =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$ ]] || fail "Invalid domain format."
  [[ "$DOMAIN" == *.* && "$DOMAIN" != *..* ]] || fail "Enter a fully qualified domain."
  say "Checking DNS A/AAAA records and public address..."
  PUBLIC_IP="$(curl -4fsS --max-time 5 https://api.ipify.org 2>/dev/null || true)"
  if [[ -z "$PUBLIC_IP" ]]; then PUBLIC_IP="$(curl -6fsS --max-time 5 https://api64.ipify.org 2>/dev/null || true)"; fi
  [[ -n "$PUBLIC_IP" ]] || fail "Could not detect public IP. Check outbound internet/DNS and retry."
  DNS_IPS="$(getent ahosts "$DOMAIN" 2>/dev/null | awk '{print $1}' | sort -u || true)"
  [[ -n "$DNS_IPS" ]] || fail "No DNS A/AAAA result for $DOMAIN. Configure DNS and retry."
  if ! grep -Fxq "$PUBLIC_IP" <<<"$DNS_IPS"; then
    echo "Domain DNS does not resolve to detected server IP ($PUBLIC_IP). Found:"; echo "$DNS_IPS"
    fail "Point the domain A/AAAA record to this server before requesting TLS."
  fi
  say "DNS check passed for $DOMAIN -> $PUBLIC_IP"
elif [[ "$MODE" == "http" && $EXISTING_INSTALL -eq 0 ]]; then
  PUBLIC_IP="$(curl -4fsS --max-time 5 https://api.ipify.org 2>/dev/null || true)"
  [[ -n "$PUBLIC_IP" ]] || PUBLIC_IP="$(hostname -I | awk '{print $1}')"
  [[ -n "$PUBLIC_IP" ]] || fail "Could not detect an IP address."
fi

say "Installing system dependencies"
export DEBIAN_FRONTEND=noninteractive
# Repair the Caddy repository key/source before apt update. Older installer versions
# could leave a source entry without signed-by, producing NO_PUBKEY ABA1F9B8875A6661.
if [[ "$MODE" == "https" && ! -x "$(command -v caddy 2>/dev/null || true)" ]]; then
  if [[ "$MODE" == "https" ]]; then
    apt-get install -y ca-certificates curl gnupg debian-keyring debian-archive-keyring apt-transport-https || fail "Could not install repository prerequisites."
    install -d -m 0755 /usr/share/keyrings /etc/apt/sources.list.d /etc/caddy
    if curl -fsSL --retry 3 https://dl.cloudsmith.io/public/caddy/stable/gpg.key -o /tmp/caddy-key.gpg; then
      gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg /tmp/caddy-key.gpg || fail "Could not install Caddy repository key."
      chmod 0644 /usr/share/keyrings/caddy-stable-archive-keyring.gpg
      printf '%s\n' 'deb [signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg] https://dl.cloudsmith.io/public/caddy/stable/deb/debian any-version main' > /etc/apt/sources.list.d/caddy-stable.list
    else
      echo "WARNING: Could not retrieve Caddy signing key; will continue without changing other repositories."
    fi
  fi
fi
if ! apt-get update; then
  echo "WARNING: apt-get update failed. Checking whether required packages are already installed."
fi
apt-get install -y python3 python3-venv python3-pip curl ca-certificates openssl dnsutils sudo || fail "Required Python/system packages could not be installed."
if [[ "$MODE" == "https" ]] && ! command -v caddy >/dev/null 2>&1; then
  if ! apt-get install -y caddy; then
    echo "WARNING: Caddy installation failed. App files will still be installed, but the HTTPS proxy will be unavailable until Caddy is fixed."
  fi
fi

say "Preparing isolated service account and directories"
if ! id idontmonitor >/dev/null 2>&1; then useradd --system --home-dir /var/lib/idontmonitor --shell /usr/sbin/nologin idontmonitor; fi
install -d -o root -g root -m 0755 "$INSTALL_DIR" "$INSTALL_DIR/releases" "$INSTALL_DIR/releases/$VERSION"
install -d -o root -g idontmonitor -m 0750 "$CONFIG_DIR"
install -d -o idontmonitor -g idontmonitor -m 0750 "$STATE_DIR" "$LOG_DIR"
cp -a "$(dirname "$0")/." "$INSTALL_DIR/releases/$VERSION/"
chown -R root:root "$INSTALL_DIR/releases/$VERSION"
ln -s "$INSTALL_DIR/releases/$VERSION" "$INSTALL_DIR/current.new"
mv -Tf "$INSTALL_DIR/current.new" "$INSTALL_DIR/current"
if [[ -f /usr/share/fonts/truetype/vazirmatn/Vazirmatn-Regular.ttf ]]; then install -d -m 0755 "$INSTALL_DIR/current/static/fonts"; install -m 0644 /usr/share/fonts/truetype/vazirmatn/Vazirmatn-Regular.ttf "$INSTALL_DIR/current/static/fonts/Vazirmatn-Regular.ttf"; fi
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --disable-pip-version-check --no-cache-dir -r "$INSTALL_DIR/current/requirements.txt"
# The installer uses umask 077, so pip-created venv executables can otherwise
# become inaccessible to the unprivileged systemd service account. Normalize
# venv permissions explicitly while keeping the environment root-owned.
chown -R root:idontmonitor "$INSTALL_DIR/venv"
find "$INSTALL_DIR/venv" -type d -exec chmod 0750 {} +
find "$INSTALL_DIR/venv" -type f -perm /111 -exec chmod 0750 {} +
find "$INSTALL_DIR/venv" -type f ! -perm /111 -exec chmod 0640 {} +
# Confirm the service account can execute Python and Uvicorn before configuring systemd.
if ! runuser -u idontmonitor -- "$INSTALL_DIR/venv/bin/python" -c 'import fastapi, uvicorn' >/dev/null 2>&1; then
  echo "WARNING: venv dependency/permission check failed; attempting repair and reinstall."
  runuser -u idontmonitor -- "$INSTALL_DIR/venv/bin/python" -m pip install --disable-pip-version-check --no-cache-dir -r "$INSTALL_DIR/current/requirements.txt" || true
  chown -R root:idontmonitor "$INSTALL_DIR/venv"
  find "$INSTALL_DIR/venv" -type d -exec chmod 0750 {} +
  find "$INSTALL_DIR/venv" -type f -perm /111 -exec chmod 0750 {} +
  find "$INSTALL_DIR/venv" -type f ! -perm /111 -exec chmod 0640 {} +
fi
if ! runuser -u idontmonitor -- "$INSTALL_DIR/venv/bin/python" -c 'import fastapi, uvicorn' >/dev/null 2>&1; then
  echo "WARNING: Python dependencies still cannot be executed as idontmonitor; installation will continue with diagnostics."
fi

# Pick a random high port by testing an actual bind, then reserve it for localhost.
find_free_port() {
  python3 - "$1" <<'PYPORT'
import socket,sys,random
host=sys.argv[1]
ports=list(range(20000,45001)); random.shuffle(ports)
for p in ports:
    s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host,p)); print(p); break
    except OSError:
        pass
    finally:
        s.close()
else:
    raise SystemExit(1)
PYPORT
}
if (( EXISTING_INSTALL == 0 )); then
  if [[ "$MODE" == "http" ]]; then
    APP_PORT="$(find_free_port 0.0.0.0)" || fail "No free HTTP application port found in 20000-45000. Existing services were not stopped."
    APP_BIND_HOST="0.0.0.0"
  else
    APP_PORT="$(find_free_port 127.0.0.1)" || fail "No free local application port found in 20000-45000. Existing services were not stopped."
    APP_BIND_HOST="127.0.0.1"
  fi
fi
SESSION_SECRET="$(openssl rand -hex 48)"
HTTPS_COOKIE_VALUE="$([[ "$MODE" == "https" ]] && echo 1 || echo 0)"
if (( EXISTING_INSTALL )); then
  # Keep the existing cookie/security mode exactly as configured.
  existing_cookie="$(sed -n 's/^IDM_HTTPS_COOKIE=//p' "$CONFIG_DIR/environment" | head -n1)"
  [[ "$existing_cookie" == "0" || "$existing_cookie" == "1" ]] || fail "Existing cookie security setting is invalid; no settings were changed."
  HTTPS_COOKIE_VALUE="$existing_cookie"
fi
INITIAL_PASSWORD=""
if [[ -s "$CONFIG_DIR/config.json" ]]; then
  # Existing installation: preserve credentials and never print a newly generated fake password.
  ADMIN_HASH="$(python3 - "$CONFIG_DIR/config.json" <<'PY'
import json,sys
try:
    cfg=json.load(open(sys.argv[1]))
    print(cfg.get('admin_hash',''))
except Exception:
    print('')
PY
)"
  [[ -n "$ADMIN_HASH" ]] || fail "Existing config has no valid admin password hash; refusing to overwrite credentials. Back up /etc/idontmonitor/config.json and repair it first."
else
  # Fresh installation: generate one random password and store only its scrypt hash.
  INITIAL_PASSWORD="$(openssl rand -hex 18)"
  ADMIN_HASH="$(python3 - "$INITIAL_PASSWORD" <<'PY'
import hashlib,secrets,sys
p=sys.argv[1].encode(); salt=secrets.token_bytes(16); n=16384; r=8; parallel=1
d=hashlib.scrypt(p,salt=salt,n=n,r=r,p=parallel,dklen=32)
print(f'scrypt${n}${r}${parallel}${salt.hex()}${d.hex()}')
PY
)"
fi

if [[ "$MODE" == "https" ]]; then HOSTS="\"$DOMAIN\",\"localhost\",\"127.0.0.1\""; else HOSTS="\"$PUBLIC_IP\",\"localhost\",\"127.0.0.1\""; fi
python3 - "$CONFIG_DIR/config.json" "$VERSION" "$SESSION_SECRET" "$ADMIN_HASH" "$HOSTS" <<'PY'
import json,sys,os,tempfile
path,version,secret,pwhash,hosts=sys.argv[1:]
allowed=[x.strip().strip('"') for x in hosts.split(',')]
if os.path.exists(path):
    with open(path) as f: cfg=json.load(f)
    cfg['version']=version
    cfg['allowed_hosts']=sorted(set((cfg.get('allowed_hosts') or []) + allowed))
    cfg.setdefault('panel_path','/')
else:
    cfg={"version":version,"session_secret":secret,"admin_user":"admin","admin_hash":pwhash,"allowed_hosts":allowed,"panel_path":"/"}
fd,tmp=tempfile.mkstemp(prefix='.config-',dir=os.path.dirname(path))
with os.fdopen(fd,'w') as f:
    json.dump(cfg,f,indent=2); f.write('\n')
os.chmod(tmp,0o640); os.replace(tmp,path)
PY
chmod 0640 "$CONFIG_DIR/config.json"; chown root:idontmonitor "$CONFIG_DIR/config.json"
ENV_TMP="$(mktemp "$CONFIG_DIR/.environment.XXXXXX")"
{
  printf 'IDM_APP_PORT=%s\n' "$APP_PORT"
  printf 'IDM_BIND_HOST=%s\n' "$APP_BIND_HOST"
  printf 'IDM_HTTPS_COOKIE=%s\n' "$HTTPS_COOKIE_VALUE"
  printf 'IDONTMONITOR_CONFIG=%s\n' "$CONFIG_DIR/config.json"
  # Retain any deployment-specific environment entries not managed by this installer.
  if (( EXISTING_INSTALL )) && [[ -r "$CONFIG_DIR/environment" ]]; then
    grep -Ev '^(IDM_APP_PORT|IDM_BIND_HOST|IDM_HTTPS_COOKIE|IDONTMONITOR_CONFIG)=' "$CONFIG_DIR/environment" || true
  fi
} > "$ENV_TMP"
chmod 0640 "$ENV_TMP"; chown root:idontmonitor "$ENV_TMP"; mv "$ENV_TMP" "$CONFIG_DIR/environment"

CADDY_START_OK=1
if [[ "$MODE" == "https" ]]; then
  install -d -m 0755 /etc/caddy
  if ! command -v caddy >/dev/null 2>&1; then CADDY_START_OK=0; echo "WARNING: Caddy is unavailable; HTTPS proxy cannot be activated."; fi
  if (( EXISTING_INSTALL )); then
    # Keep the active reverse-proxy configuration byte-for-byte on upgrades.
    if ! command -v caddy >/dev/null 2>&1 || ! caddy validate --config /etc/caddy/Caddyfile; then
      CADDY_START_OK=0
      echo "WARNING: Existing Caddy config did not validate; it was not rewritten."
    fi
  elif [[ -s /etc/caddy/Caddyfile ]]; then
    CADDY_BACKUP="/etc/caddy/Caddyfile.idontmonitor-backup.$(date +%s)"
    cp -a /etc/caddy/Caddyfile "$CADDY_BACKUP"
    cat >> /etc/caddy/Caddyfile <<EOF

# idontMonitor v$VERSION
$DOMAIN {
    encode zstd gzip
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        Referrer-Policy "no-referrer"
        X-Frame-Options "DENY"
        -Server
    }
    reverse_proxy 127.0.0.1:$APP_PORT
}
EOF
  else
    cat > /etc/caddy/Caddyfile <<EOF
$DOMAIN {
    encode zstd gzip
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        Referrer-Policy "no-referrer"
        X-Frame-Options "DENY"
        -Server
    }
    reverse_proxy 127.0.0.1:$APP_PORT
}
EOF
  fi
  if ! command -v caddy >/dev/null 2>&1 || ! caddy validate --config /etc/caddy/Caddyfile; then
    CADDY_START_OK=0
    echo "WARNING: Caddy configuration validation failed. Continuing installation; see final diagnostics."
  fi
fi
# Ensure the unprivileged service account can traverse and read the app tree.
chmod 0755 "$INSTALL_DIR" "$INSTALL_DIR/releases" "$INSTALL_DIR/releases/$VERSION"
find "$INSTALL_DIR/releases/$VERSION" -type d -exec chmod 0755 {} +
find "$INSTALL_DIR/releases/$VERSION" -type f -exec chmod 0644 {} +
install -m 0644 "$INSTALL_DIR/current/systemd/idontmonitor.service" /etc/systemd/system/idontmonitor.service
# Install a fixed root-owned updater. The web process can invoke only the `apply` action.
install -o root -g root -m 0750 "$INSTALL_DIR/current/scripts/idontmonitor-update" /usr/local/sbin/idontmonitor-update
printf '%s\n' 'idontmonitor ALL=(root) NOPASSWD: /usr/local/sbin/idontmonitor-update apply' > /etc/sudoers.d/idontmonitor-update
chmod 0440 /etc/sudoers.d/idontmonitor-update
visudo -cf /etc/sudoers.d/idontmonitor-update >/dev/null || fail "Invalid update sudo policy."

# Narrowly scoped helper for authenticated in-panel port changes. The web process
# may invoke only this root-owned script with one validated high-port argument.
cat > /usr/local/sbin/idontmonitor-set-port <<'PORTHELPER'
#!/usr/bin/env bash
set -Eeuo pipefail
[[ $# -eq 1 && "$1" =~ ^[0-9]{5}$ ]] || { echo "invalid port" >&2; exit 2; }
PORT="$1"
(( PORT >= 20000 && PORT <= 60000 )) || { echo "port out of range" >&2; exit 2; }
ENV_FILE="/etc/idontmonitor/environment"
[[ -f "$ENV_FILE" ]] || exit 3
OLD_PORT="$(sed -n 's/^IDM_APP_PORT=//p' "$ENV_FILE" | head -n1)"
[[ "$OLD_PORT" =~ ^[0-9]+$ ]] || exit 4
if [[ "$PORT" != "$OLD_PORT" ]] && ss -ltnH | awk '{print $4}' | grep -Eq "(:|\\.)${PORT}$"; then
  echo "port is already in use" >&2; exit 5
fi
TMP="$(mktemp /etc/idontmonitor/.environment.XXXXXX)"
awk -v p="$PORT" 'BEGIN{done=0} /^IDM_APP_PORT=/{print "IDM_APP_PORT=" p;done=1;next} {print} END{if(!done)print "IDM_APP_PORT=" p}' "$ENV_FILE" > "$TMP"
chown root:idontmonitor "$TMP"; chmod 0640 "$TMP"; mv "$TMP" "$ENV_FILE"
# If Caddy proxies to the previous local application port, update that upstream too.
if [[ -f /etc/caddy/Caddyfile && "$OLD_PORT" != "$PORT" ]]; then
  sed -i -E "s/(reverse_proxy[[:space:]]+127\\.0\\.0\\.1:)${OLD_PORT}([[:space:]]*)/\\1${PORT}\\2/g" /etc/caddy/Caddyfile
  if command -v caddy >/dev/null 2>&1 && caddy validate --config /etc/caddy/Caddyfile >/dev/null 2>&1; then systemctl reload caddy || true; fi
fi
systemctl restart idontmonitor
PORTHELPER
chmod 0750 /usr/local/sbin/idontmonitor-set-port
chown root:root /usr/local/sbin/idontmonitor-set-port
cat > /etc/sudoers.d/idontmonitor-port <<'SUDOERS'
idontmonitor ALL=(root) NOPASSWD: /usr/local/sbin/idontmonitor-set-port *
SUDOERS
chmod 0440 /etc/sudoers.d/idontmonitor-port
visudo -cf /etc/sudoers.d/idontmonitor-port >/dev/null || fail "Port helper sudoers rule failed validation."

systemctl daemon-reload
APP_START_OK=1
systemctl enable idontmonitor >/dev/null 2>&1 || APP_START_OK=0
systemctl restart idontmonitor >/dev/null 2>&1 || APP_START_OK=0
if [[ "$MODE" == "https" ]]; then
  systemctl enable caddy >/dev/null 2>&1 || CADDY_START_OK=0
  if ! systemctl reload caddy >/dev/null 2>&1; then systemctl restart caddy >/dev/null 2>&1 || CADDY_START_OK=0; fi
fi

say "Waiting for application health check (installation continues even if it fails)"
HEALTH_OK=0
for attempt in $(seq 1 30); do
  if curl -fsS --connect-timeout 1 --max-time 2 "http://127.0.0.1:$APP_PORT/healthz" >/dev/null 2>&1; then HEALTH_OK=1; break; fi
  sleep 1
  if (( attempt == 10 )); then systemctl restart idontmonitor >/dev/null 2>&1 || true; fi
done
if (( HEALTH_OK == 0 )); then
  APP_START_OK=0
  echo "WARNING: health check failed on port $APP_PORT. Continuing installation and collecting diagnostics at the end."
fi

if [[ "$MODE" == "http" ]]; then
  # HTTP mode serves Uvicorn directly on its preserved dedicated port.
  HTTP_PORT="$APP_PORT"
  CADDY_START_OK=1
  PANEL_URL="http://$PUBLIC_IP:$HTTP_PORT/"
  if (( EXISTING_INSTALL == 0 )); then
    printf 'MODE=http\nPUBLIC_IP=%s\nHTTP_PORT=%s\n' "$PUBLIC_IP" "$HTTP_PORT" > "$STATE_DIR/install-mode"
  fi
else
  PANEL_URL="https://$DOMAIN/"
  if (( EXISTING_INSTALL == 0 )); then
    printf 'MODE=https\nDOMAIN=%s\nPUBLIC_IP=%s\n' "$DOMAIN" "$PUBLIC_IP" > "$STATE_DIR/install-mode"
  fi
fi
chmod 0600 "$STATE_DIR/install-mode"; chown idontmonitor:idontmonitor "$STATE_DIR/install-mode"

cat > /usr/local/bin/idontMonitor <<'CLI'
#!/usr/bin/env bash
set -uo pipefail
CONFIG=/etc/idontmonitor/config.json
ENV_FILE=/etc/idontmonitor/environment
STATE=/var/lib/idontmonitor/install-mode
VERSION="1.8.1"

pause(){ read -r -p 'Press Enter to continue...' _ || true; }
line(){ printf '%s\n' '------------------------------------------------------------'; }
update_check(){
  local cache=/var/lib/idontmonitor/latest-version-cache latest cached_at now
  now=$(date +%s); cached_at=0; latest=''
  if [[ -r "$cache" ]]; then read -r cached_at latest < "$cache" || true; fi
  if [[ ! "$cached_at" =~ ^[0-9]+$ ]] || (( now-cached_at > 900 )) || [[ ! "$latest" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    latest=$(curl -fsSL --connect-timeout 2 --max-time 4 -H 'Accept: application/vnd.github+json' -H 'User-Agent: idontMonitor-CLI/1.8.1' "https://api.github.com/repos/durwinam/idontMonitor/releases/latest" 2>/dev/null | python3 -c 'import json,sys; print(str(json.load(sys.stdin).get("tag_name", "")).lstrip("v"))' 2>/dev/null || true)
    if [[ "$latest" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then printf '%s %s\n' "$now" "$latest" > "$cache" 2>/dev/null || true; else latest=''; fi
  fi
  if [[ "$latest" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] && [[ "$(printf '%s\n%s\n' "$VERSION" "$latest" | sort -V | tail -1)" == "$latest" ]] && [[ "$latest" != "$VERSION" ]]; then
    printf '\033[1;33m  Update available: current v%s → latest v%s\033[0m\n' "$VERSION" "$latest"
  elif [[ -n "$latest" ]]; then printf '  Version status: v%s is up to date\n' "$VERSION"; fi
}
banner(){
  clear 2>/dev/null || true
  printf '\033[1;35m'
  cat <<'ART'
  ██╗██████╗  ██████╗ ███╗   ██╗████████╗
  ██║██╔══██╗██╔═══██╗████╗  ██║╚══██╔══╝
  ██║██║  ██║██║   ██║██╔██╗ ██║   ██║
  ██║██║  ██║██║   ██║██║╚██╗██║   ██║
  ██║██████╔╝╚██████╔╝██║ ╚████║   ██║
  ╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═══╝   ╚═╝
ART
  printf '\033[0m'
  echo "  idontMonitor v${VERSION} | VPS CONTROL CENTER"
  update_check
  line
}
get_url(){
  if [[ -r "$STATE" ]]; then
    # This file is installer-owned and root-owned; source it only as root.
    . "$STATE"
    if [[ "${MODE:-}" == https && -n "${DOMAIN:-}" ]]; then echo "https://${DOMAIN}/"
    elif [[ -n "${PUBLIC_IP:-}" && "${HTTP_PORT:-0}" != "0" ]]; then echo "http://${PUBLIC_IP}:${HTTP_PORT}/"
    else echo "Panel URL is not configured"; fi
  else echo "Install metadata unavailable"; fi
}
svc_status(){
  systemctl is-active --quiet idontmonitor && echo "Web application: ACTIVE" || echo "Web application: INACTIVE"
  systemctl is-enabled --quiet idontmonitor && echo "Autostart: enabled" || echo "Autostart: disabled"
  [[ -r "$ENV_FILE" ]] && grep -E '^IDM_(BIND_HOST|APP_PORT)=' "$ENV_FILE" || true
  if [[ -r "$STATE" ]] && grep -q '^MODE=https$' "$STATE"; then
    systemctl is-active --quiet caddy && echo "HTTPS proxy: ACTIVE" || echo "HTTPS proxy: INACTIVE"
  fi
  if command -v free >/dev/null; then free -h | head -2; fi
  if command -v df >/dev/null; then df -h / | tail -1; fi
}
traffic(){
  echo "Network byte counters (since boot):"
  if [[ -r /proc/net/dev ]]; then
    awk -F'[: ]+' 'NR>2 {gsub(/^[ \t]+|[ \t]+$/,"",$1); if($1!="" && $1!="lo") printf "%-16s RX %12s bytes | TX %12s bytes\n",$1,$2,$10}' /proc/net/dev
  fi
}
threats(){
  echo "Recent authentication/security-related application events:"
  if command -v journalctl >/dev/null; then
    journalctl -u idontmonitor --since '24 hours ago' --no-pager 2>/dev/null | grep -iE 'invalid credentials|unauthor|rate.limit|login|security|denied' | tail -30 || echo "No matching events found in the last 24 hours."
  fi
  echo
  echo "Note: this is a log filter, not a full threat-detection engine."
}
network_diag(){
  echo "Hostname: $(hostname 2>/dev/null || echo unknown)"
  echo "Default route:"
  ip route 2>/dev/null | head -5 || true
  echo
  echo "Listening TCP ports (first 25):"
  ss -lnt 2>/dev/null | head -26 || true
  echo
  echo "Panel health:"
  if [[ -r "$ENV_FILE" ]]; then
    local p
    p="$(sed -n 's/^IDM_APP_PORT=//p' "$ENV_FILE" | head -1)"
    if [[ "$p" =~ ^[0-9]+$ ]] && curl -fsS --connect-timeout 2 "http://127.0.0.1:${p}/healthz" >/dev/null 2>&1; then
      echo "Local health check: OK (127.0.0.1:${p})"
    else echo "Local health check: FAILED"; fi
  else echo "Environment file unavailable"; fi
}
reset_panel_password(){
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "Password reset requires root. Run: sudo idontMonitor"
    pause; return
  fi
  [[ -s "$CONFIG" ]] || { echo "Config not found: $CONFIG"; pause; return; }
  echo "This will replace the web-panel admin password."
  read -r -p 'Type RESET to continue: ' confirm
  [[ "$confirm" == "RESET" ]] || { echo "Cancelled."; pause; return; }
  local backup generated
  backup="/etc/idontmonitor/config.json.backup-$(date +%Y%m%d-%H%M%S)"
  cp -p "$CONFIG" "$backup" || { echo "Could not create backup; no changes made."; pause; return; }
  chmod 0600 "$backup"
  generated="$(openssl rand -hex 18)" || { echo "Password generation failed."; pause; return; }
  if ! python3 - "$CONFIG" "$generated" <<'PY'
import hashlib,json,os,secrets,sys,tempfile
path,password=sys.argv[1:]
with open(path,encoding="utf-8") as f:
    cfg=json.load(f)
salt=secrets.token_bytes(16)
n,r,p=16384,8,1
digest=hashlib.scrypt(password.encode(),salt=salt,n=n,r=r,p=p,dklen=32)
cfg["admin_hash"]=f"scrypt${n}${r}${p}${salt.hex()}${digest.hex()}"
fd,tmp=tempfile.mkstemp(prefix=".config-reset-",dir=os.path.dirname(path))
try:
    with os.fdopen(fd,"w",encoding="utf-8") as f:
        json.dump(cfg,f,indent=2); f.write("\n")
    os.chmod(tmp,0o640)
    try:
        import grp
        os.chown(tmp,0,grp.getgrnam("idontmonitor").gr_gid)
    except (KeyError,PermissionError):
        pass
    os.replace(tmp,path)
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
    raise
PY
  then
    cp -p "$backup" "$CONFIG"
    echo "Password reset failed; original config restored."
    pause; return
  fi
  if systemctl restart idontmonitor; then
    echo
    echo "Password reset successful."
    echo "Username: admin"
    echo "New password (shown once): $generated"
    echo "Backup: $backup"
    echo "Save this password securely; it is not stored in plaintext."
  else
    cp -p "$backup" "$CONFIG"
    systemctl restart idontmonitor >/dev/null 2>&1 || true
    echo "Service restart failed; previous config was restored."
  fi
  pause
}
panel_menu(){
  while true; do
    banner
    echo "WEB PANEL"
    echo "  Current URL: $(get_url)"
    echo
    echo "  1) Open/show Panel Link"
    echo "  2) Show current bind host and port"
    echo "  3) Restart Web Panel"
    echo "  4) Recent Web Panel logs"
    echo "  5) Change panel port (guided)"
    echo "  6) Change entry IP/domain metadata"
    echo "  7) Manage URL path / HTTPS / access control"
    echo "  8) Reset web-panel password"
    echo "  9) Check GitHub for updates"
    echo "  0) Back"
    read -r -p 'Select: ' c || return
    case "$c" in
      1) get_url; pause;;
      2) grep -E '^IDM_(BIND_HOST|APP_PORT)=' "$ENV_FILE" 2>/dev/null || echo "Config unavailable"; pause;;
      3) systemctl restart idontmonitor && echo "Restart completed." || echo "Restart failed."; pause;;
      4) journalctl -u idontmonitor -n 100 --no-pager; pause;;
      5) echo "Port changes require updating the service environment and, for HTTPS, the reverse-proxy config."; echo "This release intentionally does not apply a partial port change from CLI."; echo "Use the verified installer/upgrade workflow after a config backup."; pause;;
      6) echo "Entry IP/domain is installer metadata. Changing it does not change DNS or firewall rules."; echo "For HTTPS, use a domain with valid DNS and the Caddy TLS workflow."; pause;;
      7) echo "Custom URL paths, SSL toggling, and access-control management are not implemented in v1.3.0."; echo "No configuration was changed."; pause;;
      8) reset_panel_password;;
      9) update_check; echo "To install a verified update, run: sudo idontMonitor update"; pause;;
      0) return;;
      *) echo "Invalid option"; sleep 1;;
    esac
  done
}
vps_menu(){
  while true; do
    banner; echo "VPS MANAGEMENT"; echo "  1) Restart idontMonitor service"; echo "  2) Enable service autostart"; echo "  3) Disable service autostart"; echo "  4) Reboot VPS (confirmation required)"; echo "  0) Back"
    read -r -p 'Select: ' c || return
    case "$c" in
      1) systemctl restart idontmonitor && echo "Service restarted." || echo "Restart failed."; pause;;
      2) systemctl enable idontmonitor && echo "Autostart enabled."; pause;;
      3) systemctl disable idontmonitor && echo "Autostart disabled."; pause;;
      4) read -r -p 'Type REBOOT to confirm: ' confirm; if [[ "$confirm" == REBOOT ]]; then systemctl reboot; else echo "Cancelled."; pause; fi;;
      0) return;; *) echo "Invalid option"; sleep 1;;
    esac
  done
}
backup_menu(){
  local d="/var/lib/idontmonitor/backups"
  while true; do
    banner; echo "BACKUP & RESTORE"; echo "  1) Create protected config backup"; echo "  2) List backups"; echo "  0) Back"
    read -r -p 'Select: ' c || return
    case "$c" in
      1) install -d -m 0700 "$d"; local f="$d/idontmonitor-config-$(date +%Y%m%d-%H%M%S).tar.gz"; tar -czf "$f" /etc/idontmonitor /var/lib/idontmonitor/install-mode 2>/dev/null && chmod 0600 "$f" && echo "Backup created: $f" || echo "Backup failed."; pause;;
      2) if [[ -d "$d" ]]; then find "$d" -maxdepth 1 -type f -printf '%f (%s bytes)\n'; else echo "No backups yet."; fi; pause;;
      0) return;; *) echo "Invalid option"; sleep 1;;
    esac
  done
}
case "${1:-menu}" in
  status) svc_status; systemctl --no-pager --full status idontmonitor 2>/dev/null || true;;
  url) get_url;;
  logs) journalctl -u idontmonitor -n "${2:-100}" --no-pager;;
  restart) systemctl restart idontmonitor && echo "Restarted.";;
  update-check) update_check;;
  update)
    if [[ $EUID -ne 0 ]]; then echo "Run: sudo idontMonitor update"; exit 1; fi
    if [[ ! -x /usr/local/sbin/idontmonitor-update ]]; then echo "Update helper is missing. Upgrade with the official installer first."; exit 2; fi
    echo "Checking GitHub release and installing the verified update on this VPS..."
    exec /usr/local/sbin/idontmonitor-update apply;;
  menu)
    while true; do
      banner
      echo "  1) Server Status"
      echo "  2) VPS Management"
      echo "  3) Traffic Monitor"
      echo "  4) Threat Monitor"
      echo "  5) Network Diagnostics"
      echo "  6) Telegram Bot"
      echo "  7) Web Panel"
      echo "  8) Backup & Restore"
      echo "  9) Update"
      echo " 10) Uninstall"
      echo "  0) Exit"
      read -r -p 'Select: ' choice || exit 0
      case "$choice" in
        1) banner; svc_status; systemctl --no-pager --full status idontmonitor 2>/dev/null || true; pause;;
        2) vps_menu;;
        3) banner; traffic; pause;;
        4) banner; threats; pause;;
        5) banner; network_diag; pause;;
        6) banner; echo "Telegram Bot integration is not configured in this release."; echo "No bot settings were found or changed."; pause;;
        7) panel_menu;;
        8) backup_menu;;
        9) banner; echo "Secure self-updater is not implemented in this release."; echo "No files were changed. Update only from a verified release."; pause;;
        10) banner; echo "Uninstall removes services and application files and may be destructive."; read -r -p 'Type UNINSTALL to continue: ' confirm; if [[ "$confirm" == UNINSTALL ]]; then echo "Automatic uninstall is not implemented in this release; nothing was removed."; else echo "Cancelled."; fi; pause;;
        0) exit 0;;
        *) echo "Invalid option"; sleep 1;;
      esac
    done;;
  *) echo "Usage: idontMonitor [status|url|logs [N]|restart|update]"; exit 2;;
esac
CLI
chmod 0755 /usr/local/bin/idontMonitor

printf '\n\033[1;35m============================================================\033[0m\n'
printf '\033[1;36m                    idontMonitor\033[0m\n'
printf '\033[1;35m============================================================\033[0m\n'
printf 'Version       : %s\nPanel URL     : %s\nAdmin username: admin\n' "$VERSION" "$PANEL_URL"
if [[ -n "$INITIAL_PASSWORD" ]]; then
  printf 'Initial password: %s\n' "$INITIAL_PASSWORD"
  printf '\nIMPORTANT: Save this one-time password now. Only its hash is stored.\n'
else
  printf '\nExisting credentials preserved. The installer did not change or reveal your password.\n'
fi
if [[ "$MODE" == "http" ]]; then printf '\033[1;31mWARNING: HTTP is unencrypted. Use only on a trusted network or switch to HTTPS.\033[0m\n'; else printf 'TLS: Caddy will obtain and renew the certificate automatically if DNS and ports 80/443 are reachable.\n'; fi
printf 'CLI: idontMonitor | Status: idontMonitor status | URL: idontMonitor url\n'
printf '\nInstaller finished.\n'
if (( HEALTH_OK == 1 )); then printf 'Application health: OK (127.0.0.1:%s)\n' "$APP_PORT"; else printf '\033[1;31mApplication health: FAILED (port %s)\033[0m\n' "$APP_PORT"; printf 'Check: journalctl -u idontmonitor -n 100 --no-pager\n'; systemctl status idontmonitor --no-pager -l || true; journalctl -u idontmonitor -n 40 --no-pager || true; fi
if (( CADDY_START_OK == 0 )); then printf '\033[1;33mProxy/TLS did not start or reload. Check: journalctl -u caddy -n 100 --no-pager\n'; systemctl status caddy --no-pager -l || true; fi
if [[ "$MODE" == "https" ]]; then printf 'TLS certificate issuance requires valid DNS and inbound ports 80/443.\n'; fi
printf 'No unrelated service was intentionally stopped.\n' 
