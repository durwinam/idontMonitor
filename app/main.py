from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pathlib import Path
import os, time, secrets, hashlib, hmac, json, socket, platform, shutil, subprocess, datetime, tempfile, re, fcntl, urllib.request, urllib.error, statistics, logging
from logging.handlers import RotatingFileHandler
from collections import defaultdict, deque

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
CONFIG_PATH = Path(os.environ.get("IDONTMONITOR_CONFIG", "/etc/idontmonitor/config.json"))
ACCOUNT_STATE_PATH = Path(os.environ.get("IDM_ACCOUNT_STATE", "/var/lib/idontmonitor/account.json"))

def load_config():
    try:
        cfg = json.loads(CONFIG_PATH.read_text())
    except Exception:
        cfg = {"version":"2.3.6", "panel_path":"/", "session_secret":"", "admin_hash":"", "allowed_hosts":["localhost","127.0.0.1"]}
    # Mutable account credentials live in service-owned state, not the root-owned deployment config.
    try:
        account = json.loads(ACCOUNT_STATE_PATH.read_text())
        if isinstance(account, dict):
            for key in ("admin_user", "admin_hash"):
                if isinstance(account.get(key), str) and account[key]: cfg[key] = account[key]
    except (OSError, ValueError, TypeError):
        pass
    return cfg

CFG = load_config()
app = FastAPI(title="idontMonitor", version="2.3.6", docs_url=None, redoc_url=None, openapi_url=None)
# Bounded application log: 100 MiB active file plus three rotated files.
logger = logging.getLogger("idontmonitor")
logger.setLevel(logging.INFO)
if not logger.handlers:
    try:
        _log_dir = Path(os.environ.get("IDONTMONITOR_LOG_DIR", "/var/log/idontmonitor"))
        _log_dir.mkdir(parents=True, exist_ok=True)
        _handler = RotatingFileHandler(_log_dir / "idontmonitor.log", maxBytes=100 * 1024 * 1024,
                                       backupCount=3, encoding="utf-8", delay=False)
        os.chmod(_log_dir / "idontmonitor.log", 0o600)
        _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(_handler)
        logger.propagate = False
        logging.getLogger().addHandler(_handler)
        for _name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
            _uvlog = logging.getLogger(_name)
            if _handler not in _uvlog.handlers:
                _uvlog.addHandler(_handler)
            _uvlog.propagate = False
    except OSError:
        # Development/read-only environments still run; systemd journal remains available.
        pass

from app.ops import router as operations_router
app.include_router(operations_router)
app.add_middleware(SessionMiddleware, secret_key=CFG.get("session_secret") or secrets.token_urlsafe(48), https_only=os.environ.get("IDM_HTTPS_COOKIE","0")=="1", same_site="strict", max_age=3600)
# Host validation helps prevent Host-header abuse. Install adds configured domain/IP.
allowed_hosts = CFG.get("allowed_hosts") or ["localhost", "127.0.0.1"]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts + ["*.localhost"])
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

@app.middleware("http")
async def security_response_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data: https:; font-src 'self' data:; "
        "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
        "connect-src 'self' https://api.telegram.org; frame-ancestors 'none'; "
        "base-uri 'self'; form-action 'self'"
    )
    if request.url.path.startswith("/api/") or request.url.path in ("/login", "/healthz"):
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("Pragma", "no-cache")
    if request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response
LOCALES = ROOT / "locales"
if LOCALES.is_dir():
    app.mount("/locales", StaticFiles(directory=str(LOCALES)), name="locales")

# Per-process rate limiter; production deployment is single instance by default. Use proxy-level
# limits too; shared Redis-backed limits are needed if scaling to multiple instances.
login_attempts = defaultdict(deque)
login_ip_requests = defaultdict(deque)
LOGIN_CAPTCHA_CHALLENGES = {}
LOGIN_CAPTCHA_LOCK = __import__("threading").RLock()

# One-time in-memory challenges for sensitive VPS root-password changes.
# Multi-worker deployments should use a shared challenge store.
VPS_CAPTCHA_CHALLENGES = {}
VPS_CAPTCHA_LOCK = __import__("threading").RLock()
vps_captcha_requests = defaultdict(deque)
vps_password_attempts = defaultdict(deque)

def client_ip(request: Request):
    # Do not trust forwarded headers unless an explicitly configured trusted proxy is added.
    return request.client.host if request.client else "unknown"

def limit_hit(bucket, key, max_hits, window):
    now = time.time()
    # Bound attacker-controlled per-IP state to prevent memory exhaustion from
    # distributed credential stuffing or challenge floods.
    if len(bucket) > 10000:
        for old_key, old_queue in list(bucket.items()):
            while old_queue and old_queue[0] < now - window:
                old_queue.popleft()
            if not old_queue:
                bucket.pop(old_key, None)
            if len(bucket) <= 8000:
                break
        if len(bucket) > 12000:
            for old_key in list(bucket.keys())[:2000]:
                bucket.pop(old_key, None)
    q = bucket[key]
    while q and q[0] < now - window:
        q.popleft()
    if len(q) >= max_hits:
        return True
    q.append(now)
    return False

LOGIN_AUDIT_PATH = Path(os.environ.get("IDM_LOGIN_AUDIT", "/var/lib/idontmonitor/login-audit.json"))

def record_login(username: str, request: Request, success: bool):
    """Keep a small privacy-conscious rolling audit trail; never store passwords."""
    try:
        LOGIN_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            records = json.loads(LOGIN_AUDIT_PATH.read_text())
            if not isinstance(records, list): records = []
        except Exception:
            records = []
        records.insert(0, {"at": int(time.time()), "username": str(username)[:80],
                           "ip": client_ip(request), "success": bool(success)})
        records = records[:100]
        fd, tmp = tempfile.mkstemp(prefix=".login-audit-", dir=str(LOGIN_AUDIT_PATH.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(records, f, separators=(",", ":"))
        os.chmod(tmp, 0o600)
        os.replace(tmp, LOGIN_AUDIT_PATH)
    except Exception:
        # Login should not fail just because audit storage is unavailable.
        pass

def password_policy_ok(password: str) -> bool:
    return bool(isinstance(password, str) and 16 <= len(password) <= 128
        and re.search(r"[a-z]", password) and re.search(r"[A-Z]", password)
        and re.search(r"[0-9]", password) and re.search(r"[^A-Za-z0-9]", password)
        and not any(c in password for c in ("\n", "\r", "\x00")))

def verify_password(password: str) -> bool:
    # Format: scrypt$N$r$p$salt_hex$digest_hex
    try:
        scheme,n,r,p,salt_hex,digest_hex = CFG["admin_hash"].split("$")
        if scheme != "scrypt": return False
        salt=bytes.fromhex(salt_hex); expected=bytes.fromhex(digest_hex)
        actual=hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected), maxmem=512*1024*1024)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def require_auth(request: Request):
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Authentication required")

def read_meminfo():
    data={}
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            k,v=line.split(':',1); data[k]=int(v.strip().split()[0])*1024
        total=data.get('MemTotal',0); available=data.get('MemAvailable',data.get('MemFree',0))
        used=max(total-available,0)
        return {"total_bytes":total,"used_bytes":used,"available_bytes":available,"percent":round(used/total*100,1) if total else 0,
                "swap_total_bytes":data.get('SwapTotal',0),"swap_free_bytes":data.get('SwapFree',0)}
    except Exception: return {"total_bytes":0,"used_bytes":0,"available_bytes":0,"percent":0,"swap_total_bytes":0,"swap_free_bytes":0}

def cpu_sample():
    def read():
        parts=Path('/proc/stat').read_text().splitlines()[0].split()[1:]
        vals=list(map(int,parts)); idle=vals[3]+(vals[4] if len(vals)>4 else 0); total=sum(vals)
        return idle,total
    try:
        a=read(); time.sleep(0.12); b=read(); total=b[1]-a[1]; idle=b[0]-a[0]
        return round(max(0,min(100,(1-idle/total)*100)),1) if total else 0
    except Exception: return 0

def disk_stats():
    du=shutil.disk_usage('/')
    return {"total_bytes":du.total,"used_bytes":du.used,"free_bytes":du.free,"percent":round(du.used/du.total*100,1) if du.total else 0}


TRAFFIC_STATE_PATH = Path(os.environ.get("IDM_TRAFFIC_STATE", "/var/lib/idontmonitor/traffic.json"))
TRAFFIC_LOCK = __import__("threading").Lock()
TRAFFIC_LOCK_PATH = Path(os.environ.get("IDM_TRAFFIC_LOCK", "/var/lib/idontmonitor/traffic.lock"))
HISTORY_PATH = Path(os.environ.get("IDM_HISTORY_PATH", "/var/lib/idontmonitor/metrics-history.json"))
HISTORY_LOCK = __import__("threading").Lock()
HISTORY_MAX_SAMPLES = 60 * 24  # retain up to 24h at the default one-minute history cadence
TELEGRAM_BOT_CONFIG = Path(os.environ.get('IDM_TELEGRAM_CONFIG', '/var/lib/idontmonitor/telegram-bot.json'))

def _read_traffic_state():
    try:
        return json.loads(TRAFFIC_STATE_PATH.read_text())
    except Exception:
        return {"schema": 1, "total_rx_bytes": 0, "total_tx_bytes": 0,
                "last_interfaces": {}, "last_seen_date": datetime.date.today().isoformat(),
                "tracking_started_at": None, "period_start": datetime.date.today().replace(day=1).isoformat(),
                "quota_gb": 0, "period": "monthly"}

def _write_traffic_state(state):
    TRAFFIC_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".traffic-", dir=str(TRAFFIC_STATE_PATH.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, separators=(",", ":"))
        os.chmod(tmp, 0o600)
        os.replace(tmp, TRAFFIC_STATE_PATH)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise

def network_stats():
    # Linux kernel interface counters are cumulative since boot. Track counter deltas
    # persistently so usage survives app restarts; after reboot, a reset counter is
    # treated as a new baseline rather than a negative delta.
    interfaces = []
    # Prefer the Linux interface used by the default IPv4 route. Summing every
    # interface can double-count packets on Docker bridges, VPNs and veth pairs.
    # If the route cannot be determined, report a clearly marked fallback set.
    default_ifaces = set()
    try:
        for line in Path('/proc/net/route').read_text().splitlines()[1:]:
            fields = line.split()
            if len(fields) > 7 and fields[1] == '00000000' and int(fields[3], 16) & 1:
                default_ifaces.add(fields[0])
    except Exception:
        pass
    all_interfaces = []
    try:
        for line in Path('/proc/net/dev').read_text().splitlines()[2:]:
            name, values = line.split(':', 1)
            name = name.strip()
            nums = list(map(int, values.split()))
            if name == 'lo' or len(nums) < 16:
                continue
            all_interfaces.append({"name": name, "rx_bytes": nums[0], "tx_bytes": nums[8]})
        chosen = [x for x in all_interfaces if x['name'] in default_ifaces]
        if chosen:
            interfaces = chosen
        else:
            interfaces = [x for x in all_interfaces if not x['name'].startswith(('docker', 'br-', 'veth', 'virbr', 'cni', 'flannel', 'podman'))]
    except Exception:
        pass
    now = datetime.datetime.now().astimezone()
    today = now.date().isoformat()
    month_start = now.date().replace(day=1).isoformat()
    with TRAFFIC_LOCK:
        TRAFFIC_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        with TRAFFIC_LOCK_PATH.open("a+") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            state = _read_traffic_state()
            if not state.get("tracking_started_at"):
                state["tracking_started_at"] = now.isoformat(timespec="seconds")
            last = state.get("last_interfaces", {})
            previous_sample_at = float(state.get("last_sample_at", 0) or 0)
            elapsed_seconds = max(0.0, now.timestamp() - previous_sample_at) if previous_sample_at else 0.0
            delta_rx = delta_tx = 0
            for item in interfaces:
                prev = last.get(item["name"])
                if prev:
                    rx_delta = item["rx_bytes"] - int(prev.get("rx", 0))
                    tx_delta = item["tx_bytes"] - int(prev.get("tx", 0))
                    # Negative deltas indicate a reboot or recreated interface; establish a new baseline.
                    if rx_delta >= 0: delta_rx += rx_delta
                    if tx_delta >= 0: delta_tx += tx_delta
            # Do not infer bytes for newly appearing interfaces; the first observation is a baseline.
            state["total_rx_bytes"] = int(state.get("total_rx_bytes", 0)) + delta_rx
            state["total_tx_bytes"] = int(state.get("total_tx_bytes", 0)) + delta_tx
            period = state.get("period", "monthly")
            current_period = month_start if period == "monthly" else today
            if state.get("period_start") != current_period:
                state["period_rx_bytes"] = 0
                state["period_tx_bytes"] = 0
                state["period_start"] = current_period
            state["period_rx_bytes"] = int(state.get("period_rx_bytes", 0)) + delta_rx
            state["period_tx_bytes"] = int(state.get("period_tx_bytes", 0)) + delta_tx
            state["last_interfaces"] = {x["name"]: {"rx": x["rx_bytes"], "tx": x["tx_bytes"]} for x in interfaces}
            state["last_seen_date"] = today
            state["last_sample_at"] = now.timestamp()
            # Rates are computed only from valid deltas over the actual elapsed time.
            # First sample, zero interval, or counter reset reports zero rather than fabricated throughput.
            state["rx_bytes_per_second"] = round(delta_rx / elapsed_seconds, 2) if elapsed_seconds > 0 else 0.0
            state["tx_bytes_per_second"] = round(delta_tx / elapsed_seconds, 2) if elapsed_seconds > 0 else 0.0
            state["rate_sample_seconds"] = round(elapsed_seconds, 3)
            try: _write_traffic_state(state)
            except OSError: pass
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    rx_total = int(state.get("total_rx_bytes", 0))
    tx_total = int(state.get("total_tx_bytes", 0))
    period_rx = int(state.get("period_rx_bytes", 0))
    period_tx = int(state.get("period_tx_bytes", 0))
    quota_gb = max(0.0, float(state.get("quota_gb", 0) or 0))
    used = period_rx + period_tx
    quota_bytes = int(quota_gb * (1024 ** 3))
    return {"rx_bytes_total": rx_total, "tx_bytes_total": tx_total,
            "tracked_total_bytes": rx_total + tx_total,
            "period_rx_bytes": period_rx, "period_tx_bytes": period_tx,
            "period_used_bytes": used, "quota_gb": quota_gb, "quota_bytes": quota_bytes,
            "remaining_bytes": max(0, quota_bytes - used) if quota_bytes else None,
            "quota_percent": min(100, round(used / quota_bytes * 100, 2)) if quota_bytes else None,
            "period": state.get("period", "monthly"), "period_start": state.get("period_start"),
            "tracking_started_at": state.get("tracking_started_at"), "last_sample_at": state.get("last_sample_at"),
            "rx_bytes_per_second": float(state.get("rx_bytes_per_second", 0) or 0),
            "tx_bytes_per_second": float(state.get("tx_bytes_per_second", 0) or 0),
            "rate_sample_seconds": float(state.get("rate_sample_seconds", 0) or 0),
            "interface_selection": "default-route" if default_ifaces and any(x["name"] in default_ifaces for x in interfaces) else "fallback", "interface_names": [x["name"] for x in interfaces],
            "interfaces": interfaces}

def record_metrics_history(sample):
    """Store one minute-bucketed sample, bounded to 24 hours; safe for a small single-host install."""
    now = int(sample.get("timestamp", time.time()))
    bucket = now // 60 * 60
    try:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with HISTORY_LOCK:
            try:
                rows = json.loads(HISTORY_PATH.read_text())
                if not isinstance(rows, list): rows = []
            except Exception:
                rows = []
            compact = {
                "timestamp": bucket,
                "cpu_percent": round(float(sample.get("cpu_percent", 0)), 1),
                "memory_percent": round(float(sample.get("memory", {}).get("percent", 0)), 1),
                "disk_percent": round(float(sample.get("disk", {}).get("percent", 0)), 1),
                "rx_bytes_total": int(sample.get("network", {}).get("rx_bytes_total", 0)),
                "tx_bytes_total": int(sample.get("network", {}).get("tx_bytes_total", 0)),
                "period_used_bytes": int(sample.get("network", {}).get("period_used_bytes", 0)),
            }
            if rows and int(rows[-1].get("timestamp", 0)) == bucket:
                rows[-1] = compact
            else:
                rows.append(compact)
            cutoff = now - 86400
            rows = [r for r in rows if int(r.get("timestamp", 0)) >= cutoff][-HISTORY_MAX_SAMPLES:]
            fd, tmp = tempfile.mkstemp(prefix=".history-", dir=str(HISTORY_PATH.parent))
            with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump(rows, f, separators=(",", ":"))
            os.chmod(tmp, 0o600); os.replace(tmp, HISTORY_PATH)
    except Exception:
        # Telemetry must remain available even if optional history storage fails.
        pass



# Update Center: public GitHub metadata is read-only; installation is delegated to a
# fixed root-owned helper with no user-controlled command arguments.
import threading
UPDATE_REPO = "durwinam/idontMonitor"
UPDATE_CACHE = {"checked_at": 0, "result": None, "error": None}
UPDATE_LOCK = threading.Lock()
UPDATE_STATUS_PATH = Path(os.environ.get("IDM_UPDATE_STATUS", "/var/lib/idontmonitor/update-status.json"))

def _version_tuple(value):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.-]+)?", str(value or "").strip())
    return tuple(map(int, match.groups())) if match else None

def check_github_update(force=False):
    now = time.time()
    with UPDATE_LOCK:
        if not force and UPDATE_CACHE["result"] is not None and now - UPDATE_CACHE["checked_at"] < 900:
            return {**UPDATE_CACHE["result"], "cached": True}
        req = urllib.request.Request(
            f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest",
            headers={"Accept":"application/vnd.github+json", "User-Agent":"idontMonitor-UpdateChecker/2.3.6", "X-GitHub-Api-Version":"2022-11-28"})
        try:
            with urllib.request.urlopen(req, timeout=6) as response:
                release = json.loads(response.read(1024 * 1024).decode("utf-8"))
            tag = str(release.get("tag_name", ""))
            latest = _version_tuple(tag)
            current = _version_tuple((ROOT / "VERSION").read_text().strip())
            if not latest or not current:
                raise ValueError("GitHub release tag or installed version is invalid")
            result = {"ok":True,"current_version":(ROOT/"VERSION").read_text().strip(),"latest_version":tag.lstrip("v"),
                      "update_available":latest > current,"release_url":release.get("html_url",f"https://github.com/{UPDATE_REPO}/releases"),
                      "release_name":str(release.get("name") or tag)[:180],"published_at":release.get("published_at"),
                      "notes":str(release.get("body") or "")[:12000],"checked_at":int(now),"cached":False}
            UPDATE_CACHE.update(checked_at=now, result=result, error=None)
            return result
        except Exception as exc:
            cached = UPDATE_CACHE.get("result")
            if cached:
                return {**cached, "ok":False, "stale":True, "error":"GitHub check failed; showing last known result."}
            return {"ok":False,"current_version":(ROOT/"VERSION").read_text().strip(),"latest_version":None,
                    "update_available":False,"error":"Could not reach GitHub to verify the latest release.","checked_at":int(now)}

@app.get('/api/updates/check')
def update_check(request: Request, force: int = 0):
    require_auth(request)
    return check_github_update(force=bool(force))

@app.get('/api/updates/status')
def update_status(request: Request):
    require_auth(request)
    try:
        data=json.loads(UPDATE_STATUS_PATH.read_text())
        return data if isinstance(data,dict) else {"state":"unknown"}
    except Exception:
        return {"state":"idle","message":"No update operation has been run."}

@app.post('/api/updates/apply')
def update_apply(request: Request):
    require_auth(request)
    info=check_github_update(force=True)
    if not info.get("ok"):
        raise HTTPException(status_code=503, detail="GitHub release could not be verified; update was not started.")
    if not info.get("update_available"):
        return {"ok":True,"state":"current","message":"This installation is already up to date."}
    helper="/usr/local/sbin/idontmonitor-update"
    if not Path(helper).is_file():
        raise HTTPException(status_code=503, detail="The privileged update helper is not installed. Reinstall/upgrade using the official installer first.")
    try:
        subprocess.Popen(["sudo","-n",helper,"apply"],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True,start_new_session=True)
    except HTTPException: raise
    except Exception:
        raise HTTPException(status_code=503, detail="Could not start the server update process.")
    return {"ok":True,"state":"starting","message":"Update started on the VPS. Follow the live status below."}


@app.get('/healthz')
def health(): return {"ok":True,"version":CFG.get('version','2.3.6')}

def _cmd_ok(args):
    try:
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=2, check=False)
        return result.returncode == 0, result.stdout.strip()
    except Exception:
        return False, ''

@app.get('/api/security')
def security_status(request: Request):
    require_auth(request)
    # Report only checks this process can actually verify; no pretend intrusion detection.
    mode = 'unknown'; proxy_active = False; bind_host = os.environ.get('IDM_BIND_HOST', 'unknown')
    state_file = Path('/var/lib/idontmonitor/install-mode')
    try:
        raw = state_file.read_text(errors='replace')
        vals = dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)
        mode = vals.get('MODE', 'unknown').lower()
        if mode == 'https': proxy_active = _cmd_ok(['systemctl', 'is-active', '--quiet', 'caddy'])[0]
    except Exception:
        pass
    https_cookie = os.environ.get('IDM_HTTPS_COOKIE', '0') == '1'
    cfg_permissions = 'unknown'
    try:
        st = CONFIG_PATH.stat(); cfg_permissions = 'pass' if (st.st_mode & 0o007) == 0 and (st.st_mode & 0o020) == 0 else 'warn'
    except Exception:
        cfg_permissions = 'unknown'
    hardening = {}
    for prop in ('NoNewPrivileges', 'ProtectSystem', 'ProtectHome', 'PrivateTmp'):
        ok, val = _cmd_ok(['systemctl', 'show', 'idontmonitor', '--property=' + prop, '--value'])
        hardening[prop] = bool(ok and val.lower() in (('yes',) if prop in ('NoNewPrivileges','ProtectHome','PrivateTmp') else ('strict','full','yes')))
    hardening_ok = all(hardening.values()) if hardening else False
    items = [
      {'id':'auth','label':'Dashboard authentication','status':'pass','detail':'Metrics and settings require an authenticated session.'},
      {'id':'throttle','label':'Login throttling','status':'pass','detail':'In-process rate limits: 5 attempts per 15 minutes and 30 requests per minute per IP.'},
      {'id':'https','label':'HTTPS transport','status': ('pass' if mode == 'https' and proxy_active and https_cookie else ('warn' if mode == 'http' else 'unknown')), 'detail': ('HTTPS mode and Caddy are active; secure session cookies are enabled.' if mode == 'https' and proxy_active and https_cookie else ('Installed in HTTP mode. Credentials and session cookies can be exposed on untrusted networks.' if mode == 'http' else 'Could not verify HTTPS deployment and proxy state.'))},
      {'id':'bind','label':'Application network binding','status': ('pass' if bind_host in ('127.0.0.1','::1') else ('warn' if bind_host in ('0.0.0.0','::') else 'unknown')), 'detail': ('Application listens on loopback; external access should pass through a reverse proxy.' if bind_host in ('127.0.0.1','::1') else ('Application is bound to all interfaces; firewall rules must restrict access.' if bind_host in ('0.0.0.0','::') else 'Binding could not be verified.'))},
      {'id':'config','label':'Configuration file permissions','status':cfg_permissions,'detail': ('Config file has no group-write or world access bits.' if cfg_permissions == 'pass' else ('Config file permissions may be too broad.' if cfg_permissions == 'warn' else 'Could not inspect config file permissions.'))},
      {'id':'hardening','label':'systemd service hardening','status': ('pass' if hardening_ok else ('warn' if any(hardening.values()) else 'unknown')), 'detail': ('Verified service hardening: ' + ', '.join(k for k,v in hardening.items() if v) if hardening_ok else ('NoNewPrivileges is disabled for the restricted port-change helper; other hardening flags are reported individually.' if not hardening.get('NoNewPrivileges', False) and any(hardening.values()) else ('Some expected systemd hardening settings are missing.' if any(hardening.values()) else 'Could not verify systemd hardening properties.')))}
    ]
    passed=sum(x['status']=='pass' for x in items); warnings=sum(x['status']=='warn' for x in items); unknown=sum(x['status']=='unknown' for x in items)
    return {'checked_at':int(time.time()), 'mode':mode, 'summary':{'passed':passed,'warnings':warnings,'unknown':unknown,'total':len(items)}, 'items':items, 'scope_note':'These are configuration checks, not malware scanning, intrusion detection, or a guarantee that the host is secure.'}

@app.get('/api/session')
def session_info(request: Request):
    return {"authenticated":bool(request.session.get('authenticated'))}

def _new_login_challenge(request: Request):
    left = secrets.randbelow(8) + 2
    right = secrets.randbelow(8) + 2
    token = secrets.token_urlsafe(32); now = int(time.time()); ip = client_ip(request)
    with LOGIN_CAPTCHA_LOCK:
        for old_token, old in list(LOGIN_CAPTCHA_CHALLENGES.items()):
            if int(old.get("expires_at", 0)) < now: LOGIN_CAPTCHA_CHALLENGES.pop(old_token, None)
        if len(LOGIN_CAPTCHA_CHALLENGES) >= 4096:
            oldest = sorted(LOGIN_CAPTCHA_CHALLENGES.items(), key=lambda item: item[1].get("expires_at", 0))[:512]
            for old_token, _ in oldest: LOGIN_CAPTCHA_CHALLENGES.pop(old_token, None)
        LOGIN_CAPTCHA_CHALLENGES[token] = {"answer": str(left + right), "expires_at": now + 180, "ip": ip}
    # The answer is server-side only; the signed but readable session cookie never contains it.
    return {'token': token, 'question': f'{left} + {right}', 'expires_in': 180}

@app.get('/api/login-challenge')
def login_challenge(request: Request):
    if request.session.get('authenticated'):
        raise HTTPException(status_code=409, detail='Already authenticated')
    if limit_hit(login_ip_requests, 'captcha:' + client_ip(request), 30, 60):
        raise HTTPException(status_code=429, detail='Too many challenge requests. Wait before trying again.')
    return _new_login_challenge(request)

@app.get('/login', response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get('authenticated'): return RedirectResponse('/',status_code=303)
    challenge = _new_login_challenge(request)
    page = (STATIC/'login.html').read_text(encoding='utf-8')
    page = page.replace('id="captchaQuestion">Loading…', 'id="captchaQuestion">' + challenge['question'])
    page = page.replace('name="captcha_token" value=""', 'name="captcha_token" value="' + challenge['token'] + '"')
    return HTMLResponse(page)

@app.post('/login')
def login(request: Request, username: str = Form(...), password: str = Form(...),
          captcha_token: str = Form(''), captcha_answer: str = Form('')):
    ip=client_ip(request)
    # HTTP is allowed for compatibility with direct-IP deployments. The login
    # page displays a short HTTPS/TLS recommendation when the connection is HTTP.
    # Credentials are not encrypted in transit over HTTP; HTTPS remains strongly recommended.
    if limit_hit(login_ip_requests,ip,30,60) or limit_hit(login_attempts,ip,5,900):
        raise HTTPException(status_code=429,detail='Too many login attempts. Wait before trying again.')
    with LOGIN_CAPTCHA_LOCK:
        challenge = LOGIN_CAPTCHA_CHALLENGES.pop(captcha_token, None) if captcha_token else None
    valid_challenge = bool(isinstance(challenge, dict)
        and int(challenge.get('expires_at', 0)) >= int(time.time())
        and hmac.compare_digest(str(challenge.get('ip', '')).encode(), ip.encode())
        and hmac.compare_digest(str(challenge.get('answer', '')).encode(), captcha_answer.strip().encode()))
    if not valid_challenge:
        record_login(username, request, False)
        raise HTTPException(status_code=400, detail='CAPTCHA is incorrect or expired. Solve the new challenge and try again.')
    valid_user=hmac.compare_digest(username.encode(),str(CFG.get('admin_user','admin')).encode())
    # Always perform the expensive password hash check, even for an invalid
    # username, to reduce account-ID timing side channels.
    valid_password=verify_password(password)
    valid=valid_user and valid_password
    if not valid:
        record_login(username, request, False)
        raise HTTPException(status_code=401,detail='Invalid credentials')
    record_login(username, request, True)
    request.session.clear(); request.session['authenticated']=True; request.session['login_at']=int(time.time())
    return RedirectResponse('/',status_code=303)

@app.post('/logout')
def logout(request: Request):
    request.session.clear(); return RedirectResponse('/login',status_code=303)

@app.get('/')
def index(request: Request):
    if not request.session.get('authenticated'): return RedirectResponse('/login',status_code=303)
    return FileResponse(STATIC/'index.html')

@app.get('/api/metrics')
def metrics(request: Request):
    require_auth(request)
    load=[float(x) for x in Path('/proc/loadavg').read_text().split()[:3]] if Path('/proc/loadavg').exists() else [0,0,0]
    net=network_stats()
    sample = {"timestamp":int(time.time()),"host":socket.gethostname(),"platform":platform.platform(),"cpu_percent":cpu_sample(),"memory":read_meminfo(),"disk":disk_stats(),"network":net,"load_average":load,"cpu_count":os.cpu_count() or 1,"uptime_seconds":int(time.time()-float(Path('/proc/uptime').read_text().split()[0])) if Path('/proc/uptime').exists() else 0}
    record_metrics_history(sample)
    return sample

# Speed tests use fixed Cloudflare speed endpoints, strict byte caps, short timeouts,
# authenticated sessions, and per-client throttling. No user-supplied URL is accepted.
speedtest_requests = defaultdict(deque)
SPEEDTEST_BASE = "https://speed.cloudflare.com"

@app.get('/api/speedtest')
def speedtest_phase(request: Request, phase: str):
    require_auth(request)
    if phase not in ('latency', 'download', 'upload', 'packetloss'):
        raise HTTPException(status_code=400, detail='Unsupported test phase')
    ip = client_ip(request)
    # Cap each client to a small number of phases; latency starts a new test budget.
    max_hits = 6 if phase == 'latency' else 12
    if limit_hit(speedtest_requests, ip + ':' + phase, max_hits, 300):
        raise HTTPException(status_code=429, detail='Speed test rate limit reached. Please wait a few minutes.')
    if phase == 'latency':
        samples=[]; failures=0; last_error=''
        # Five small HTTPS probes; this is HTTP latency, not raw ICMP RTT.
        for _ in range(3):
            started=time.perf_counter()
            try:
                req=urllib.request.Request(SPEEDTEST_BASE + '/__down?bytes=0&cache=' + str(time.time_ns()), headers={'User-Agent':'idontMonitor-SpeedTest/1.7.3','Cache-Control':'no-cache'})
                with urllib.request.urlopen(req, timeout=1.0) as response:
                    response.read(128)
                    if response.status < 200 or response.status >= 400: raise OSError('HTTP probe rejected')
                samples.append((time.perf_counter()-started)*1000)
            except Exception as exc:
                failures += 1; last_error=type(exc).__name__ + ': ' + str(exc)[:120]
        if not samples:
            return JSONResponse({'phase':phase,'ok':False,'latency_ms':None,'jitter_ms':None,'detail':'Cloudflare HTTPS probe failed from this VPS (' + (last_error or 'no response') + '). Check outbound TCP/443, DNS, proxy and TLS.'}, status_code=502)
        diffs=[abs(samples[i]-samples[i-1]) for i in range(1,len(samples))]
        return {'phase':phase,'ok':True,'latency_ms':round(statistics.median(samples),2),'jitter_ms':round(statistics.mean(diffs),2) if diffs else 0.0,'samples':len(samples),'failed_probes':failures,'provider':'Cloudflare HTTPS endpoint','method':'HTTPS request latency'}
    if phase == 'download':
        started=time.perf_counter(); received=0; samples=[]; last_sample=started; bytes_sample=0; deadline=started+5.5; last_error=''
        try:
            while time.perf_counter() < deadline:
                remaining=max(0.25, deadline-time.perf_counter())
                req=urllib.request.Request(f'{SPEEDTEST_BASE}/__down?bytes=8388608&nonce={time.time_ns()}', headers={'User-Agent':'idontMonitor-SpeedTest/1.7.3','Cache-Control':'no-cache'})
                with urllib.request.urlopen(req, timeout=min(remaining+1.0,7.5)) as response:
                    while time.perf_counter() < deadline:
                        chunk=response.read(128*1024)
                        if not chunk: break
                        now=time.perf_counter(); received += len(chunk); bytes_sample += len(chunk)
                        if now-last_sample >= 0.5:
                            samples.append({'t':round(now-started,2),'mbps':round(bytes_sample*8/(now-last_sample)/1_000_000,2)})
                            last_sample=now; bytes_sample=0
                if time.perf_counter() >= deadline: break
            elapsed=max(time.perf_counter()-started,0.001)
            if received < 65536: raise OSError('Only a small amount of data was received')
            return {'phase':phase,'ok':True,'bytes':received,'duration_seconds':round(elapsed,3),'mbps':round(received*8/elapsed/1_000_000,2),'samples':samples,'provider':'Cloudflare speed test endpoint'}
        except Exception as exc:
            last_error=type(exc).__name__ + ': ' + str(exc)[:120]
            if received >= 65536:
                elapsed=max(time.perf_counter()-started,0.001)
                return {'phase':phase,'ok':True,'bytes':received,'duration_seconds':round(elapsed,3),'mbps':round(received*8/elapsed/1_000_000,2),'samples':samples,'warning':last_error,'provider':'Cloudflare speed test endpoint'}
            return JSONResponse({'phase':phase,'ok':False,'mbps':None,'detail':'Download failed from this VPS ('+last_error+'). Check outbound TCP/443, DNS, proxy and TLS.'}, status_code=502)
    if phase == 'upload':
        started=time.perf_counter(); total=0; samples=[]; last_sample=started; bytes_sample=0; deadline=started+5.5; last_error=''
        try:
            while time.perf_counter() < deadline and total < 12*1024*1024:
                payload=os.urandom(512*1024)
                req=urllib.request.Request(SPEEDTEST_BASE + '/__up', data=payload, method='POST', headers={'User-Agent':'idontMonitor-SpeedTest/1.7.3','Content-Type':'application/octet-stream','Cache-Control':'no-cache'})
                with urllib.request.urlopen(req, timeout=min(max(1.0,deadline-time.perf_counter()+1),7.5)) as response:
                    response.read(1024)
                    if response.status < 200 or response.status >= 400: raise OSError('Upload endpoint rejected data')
                total += len(payload); bytes_sample += len(payload); now=time.perf_counter()
                if now-last_sample >= 0.5:
                    samples.append({'t':round(now-started,2),'mbps':round(bytes_sample*8/(now-last_sample)/1_000_000,2)})
                    last_sample=now; bytes_sample=0
            elapsed=max(time.perf_counter()-started,0.001)
            if total < 65536: raise OSError('Upload transfer was too small to measure')
            return {'phase':phase,'ok':True,'bytes':total,'duration_seconds':round(elapsed,3),'mbps':round(total*8/elapsed/1_000_000,2),'samples':samples,'provider':'Cloudflare speed test endpoint'}
        except Exception as exc:
            last_error=type(exc).__name__ + ': ' + str(exc)[:120]
            if total >= 65536:
                elapsed=max(time.perf_counter()-started,0.001)
                return {'phase':phase,'ok':True,'bytes':total,'duration_seconds':round(elapsed,3),'mbps':round(total*8/elapsed/1_000_000,2),'samples':samples,'warning':last_error,'provider':'Cloudflare speed test endpoint'}
            return JSONResponse({'phase':phase,'ok':False,'mbps':None,'detail':'Upload failed from this VPS ('+last_error+'). Check outbound TCP/443, DNS, proxy and TLS.'}, status_code=502)
    # ICMP packet loss is measured separately. If ping/ICMP is blocked, report unknown.
    try:
        result=subprocess.run(['ping','-n','-c','3','-W','1','1.1.1.1'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,timeout=4,check=False)
        match=re.search(r'(\d+(?:\.\d+)?)%\s*packet loss',result.stdout)
        if not match:
            return {'phase':phase,'ok':False,'packet_loss_percent':None,'detail':'ICMP unavailable or filtered; packet loss is unknown'}
        return {'phase':phase,'ok':True,'packet_loss_percent':float(match.group(1)),'target':'1.1.1.1','method':'ICMP ping','packets':3}
    except Exception:
        return {'phase':phase,'ok':False,'packet_loss_percent':None,'detail':'ping utility unavailable or ICMP blocked; packet loss is unknown'}

@app.get('/api/history')
def metrics_history(request: Request, hours: int = 24):
    require_auth(request)
    if hours not in (1, 6, 24):
        raise HTTPException(status_code=400, detail="hours must be 1, 6 or 24")
    try:
        rows = json.loads(HISTORY_PATH.read_text())
        if not isinstance(rows, list): rows = []
    except Exception:
        rows = []
    cutoff = int(time.time()) - hours * 3600
    return {"hours": hours, "interval_seconds": 60, "items": [r for r in rows if int(r.get("timestamp", 0)) >= cutoff]}


@app.get('/api/settings')
def get_settings(request: Request):
    require_auth(request)
    with TRAFFIC_LOCK:
        state = _read_traffic_state()
    return {"traffic_quota_gb": max(0.0, float(state.get("quota_gb", 0) or 0)),
            "traffic_period": state.get("period", "monthly")}

@app.post('/api/settings')
async def save_settings(request: Request):
    require_auth(request)
    try:
        body = await request.json()
        quota = float(body.get("traffic_quota_gb", 0))
        period = str(body.get("traffic_period", "monthly"))
        if quota < 0 or quota > 100000000:
            raise ValueError("quota out of range")
        if period not in ("daily", "monthly"):
            raise ValueError("invalid period")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid settings")
    with TRAFFIC_LOCK:
        state = _read_traffic_state()
        if state.get("period", "monthly") != period:
            state["period"] = period
            today = datetime.date.today()
            state["period_start"] = (today.replace(day=1).isoformat() if period == "monthly" else today.isoformat())
            state["period_rx_bytes"] = 0
            state["period_tx_bytes"] = 0
        state["quota_gb"] = quota
        _write_traffic_state(state)
    return {"ok": True, "traffic_quota_gb": quota, "traffic_period": period}


@app.get('/api/telegram-bot')
def telegram_bot_settings(request: Request):
    require_auth(request)
    try:
        d=json.loads(TELEGRAM_BOT_CONFIG.read_text())
        admins=d.get('admin_ids',[])
        token_set=bool(d.get('token'))
    except Exception:
        admins=[]; token_set=False
    return {"configured":token_set and len(admins)>0, "token_set":token_set, "token_preview":"configured (hidden)" if token_set else "", "admin_ids":admins}

@app.post('/api/telegram-bot')
async def save_telegram_bot_settings(request: Request):
    require_auth(request)
    try:
        body=await request.json()
        token=str(body.get('token','')).strip()
        admin_values=body.get('admin_ids',[])
        if not isinstance(admin_values,list) or not 1 <= len(admin_values) <= 3:
            raise ValueError('Enter between one and three numeric Telegram admin IDs')
        admins=[]
        for value in admin_values:
            value=str(value).strip()
            if not re.fullmatch(r'[1-9][0-9]{4,19}',value): raise ValueError('Admin IDs must be numeric Telegram user IDs')
            if int(value) not in admins: admins.append(int(value))
        if len(admins)!=len(admin_values): raise ValueError('Admin IDs must be unique')
        if not token:
            try: token=json.loads(TELEGRAM_BOT_CONFIG.read_text()).get('token','')
            except Exception: pass
        if not re.fullmatch(r'[0-9]{5,15}:[A-Za-z0-9_-]{20,}',token):
            raise ValueError('Enter a valid Telegram bot token from BotFather')
        # Verify token before persisting it; never return token to the browser.
        req=urllib.request.Request(f'https://api.telegram.org/bot{token}/getMe',data=b'',method='GET')
        with urllib.request.urlopen(req,timeout=10) as response: result=json.loads(response.read(65536))
        if not result.get('ok') or not isinstance(result.get('result'),dict):
            raise ValueError('Telegram rejected this bot token')
        TELEGRAM_BOT_CONFIG.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(prefix='.telegram-bot-',dir=str(TELEGRAM_BOT_CONFIG.parent))
        with os.fdopen(fd,'w',encoding='utf-8') as f: json.dump({'schema':1,'token':token,'admin_ids':admins,'bot_username':result['result'].get('username','')},f,separators=(',',':'))
        os.chmod(tmp,0o600); os.replace(tmp,TELEGRAM_BOT_CONFIG)
        logger.info('Telegram bot settings updated; token omitted; admin_count=%d',len(admins))
        return {'ok':True,'configured':True,'bot_username':result['result'].get('username',''),'admin_ids':admins,'message':'Bot settings saved securely. The Telegram worker will reload configuration.'}
    except HTTPException: raise
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=400,detail='Telegram token verification failed (HTTP error)')
    except (urllib.error.URLError,TimeoutError):
        raise HTTPException(status_code=502,detail='Could not reach Telegram to verify the token')
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e))
    except Exception:
        raise HTTPException(status_code=400,detail='Invalid Telegram bot settings')

@app.get('/api/account')
def account_info(request: Request):
    require_auth(request)
    try:
        env = {}
        env_path = Path("/etc/idontmonitor/environment")
        for line in env_path.read_text().splitlines():
            if "=" in line:
                k,v=line.split("=",1); env[k]=v
        port = int(env.get("IDM_APP_PORT","0"))
    except Exception:
        port = 0
    return {"username": CFG.get("admin_user","admin"), "port": port}

@app.get('/api/security/logins')
def recent_logins(request: Request):
    require_auth(request)
    try:
        records = json.loads(LOGIN_AUDIT_PATH.read_text())
        if not isinstance(records, list): records = []
    except Exception:
        records = []
    return {"items": records[:3]}

@app.post('/api/account/username')
async def change_username(request: Request):
    require_auth(request)
    try:
        body = await request.json()
        current = str(body.get("current_password", ""))
        username = str(body.get("username", "")).strip()
        if not verify_password(current): raise HTTPException(status_code=403, detail="Current password is incorrect")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
            raise HTTPException(status_code=400, detail="Username must be 3-32 characters: letters, numbers, dot, underscore or hyphen")
        if hmac.compare_digest(username.encode(), str(CFG.get("admin_user","admin")).encode()):
            return {"ok": True, "username": username}
        CFG["admin_user"] = username
        _save_config()
        return {"ok": True, "username": username}
    except HTTPException: raise
    except Exception: raise HTTPException(status_code=400, detail="Invalid account request")

@app.post('/api/account/password')
async def change_password(request: Request):
    require_auth(request)
    try:
        body = await request.json()
        current = str(body.get("current_password", ""))
        new_password = str(body.get("new_password", ""))
        if not verify_password(current): raise HTTPException(status_code=403, detail="Current password is incorrect")
        if not password_policy_ok(new_password):
            raise HTTPException(status_code=400, detail="Password must be 16–128 characters and include uppercase, lowercase, a number, and a special character")
        salt=secrets.token_bytes(16); n=32768; r=8; parallel=1
        digest=hashlib.scrypt(new_password.encode(),salt=salt,n=n,r=r,p=parallel,dklen=32,maxmem=512*1024*1024)
        CFG["admin_hash"]=f"scrypt${n}${r}${parallel}${salt.hex()}${digest.hex()}"
        _save_config()
        request.session.clear()
        return {"ok": True, "reauth_required": True}
    except HTTPException: raise
    except Exception: raise HTTPException(status_code=400, detail="Invalid password request")

def _save_config():
    tmp = None
    try:
        ACCOUNT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, tmp = tempfile.mkstemp(prefix=".account-", dir=str(ACCOUNT_STATE_PATH.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"admin_user": CFG.get("admin_user", ""), "admin_hash": CFG.get("admin_hash", "")}, f, separators=(",", ":"))
            f.flush(); os.fsync(f.fileno())
        os.chmod(tmp, 0o600); os.replace(tmp, ACCOUNT_STATE_PATH); os.chmod(ACCOUNT_STATE_PATH, 0o600)
    except Exception:
        if tmp:
            try: os.unlink(tmp)
            except OSError: pass
        raise HTTPException(status_code=500, detail="Could not save account settings")

@app.post('/api/account/port')
async def change_port(request: Request):
    require_auth(request)
    try:
        body = await request.json()
        current = str(body.get("current_password", ""))
        port = int(body.get("port", 0))
        if not verify_password(current): raise HTTPException(status_code=403, detail="Current password is incorrect")
        if not 20000 <= port <= 60000: raise HTTPException(status_code=400, detail="Port must be between 20000 and 60000")
        # Port changes require a root-owned, tightly-scoped helper installed by install.sh.
        helper = Path("/usr/local/sbin/idontmonitor-set-port")
        if not helper.exists():
            raise HTTPException(status_code=503, detail="Port change helper is not installed. Reinstall/upgrade with the v2.3.6 installer.")
        result = subprocess.run(["sudo", "-n", str(helper), str(port)], capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail="Port change failed safely. Check service logs and firewall rules.")
        return {"ok": True, "port": port, "message": "Port changed; the service is restarting. Update firewall rules if needed."}
    except HTTPException: raise
    except Exception: raise HTTPException(status_code=400, detail="Invalid port request")

@app.get('/api/vps/summary')
def vps_summary(request: Request):
    require_auth(request)
    try:
        mem = {}
        for line in Path('/proc/meminfo').read_text().splitlines():
            if ':' in line:
                k, v = line.split(':', 1); mem[k] = int(v.strip().split()[0]) * 1024
        total = mem.get('MemTotal', 0); available = mem.get('MemAvailable', 0)
        disk = shutil.disk_usage('/')
        load = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
        uptime = int(float(Path('/proc/uptime').read_text().split()[0]))
        os_name = platform.platform()
        try:
            for line in Path('/etc/os-release').read_text().splitlines():
                if line.startswith('PRETTY_NAME='):
                    os_name = line.split('=', 1)[1].strip().strip('"'); break
        except OSError: pass
        return {'hostname': socket.gethostname(), 'os': os_name, 'kernel': platform.release(),
                'cpu_count': os.cpu_count() or 1, 'load': [round(float(x), 2) for x in load],
                'uptime_seconds': uptime, 'memory_total': total, 'memory_used': max(0, total-available),
                'memory_available': available, 'disk_total': disk.total, 'disk_used': disk.used,
                'disk_free': disk.free, 'status': 'ok'}
    except Exception:
        logger.exception('VPS summary collection failed')
        raise HTTPException(status_code=503, detail='Live VPS information is temporarily unavailable')

def _new_vps_password_captcha(request: Request):
    # Create a short-lived challenge bound to both source IP and login session.
    left = __import__("secrets").randbelow(8) + 2
    right = __import__("secrets").randbelow(8) + 2
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    challenge = {
        "answer": str(left + right), "expires_at": now + 180,
        "ip": client_ip(request), "login_at": int(request.session.get("login_at", 0) or 0),
    }
    with VPS_CAPTCHA_LOCK:
        for old_token, old in list(VPS_CAPTCHA_CHALLENGES.items()):
            if int(old.get("expires_at", 0)) < now:
                VPS_CAPTCHA_CHALLENGES.pop(old_token, None)
        if len(VPS_CAPTCHA_CHALLENGES) >= 2048:
            oldest = sorted(VPS_CAPTCHA_CHALLENGES.items(), key=lambda item: item[1].get("expires_at", 0))[:256]
            for old_token, _ in oldest:
                VPS_CAPTCHA_CHALLENGES.pop(old_token, None)
        VPS_CAPTCHA_CHALLENGES[token] = challenge
    return {"token": token, "question": f"{left} + {right}", "expires_in": 180}

@app.get('/api/vps/password-challenge')
def vps_password_challenge(request: Request):
    require_auth(request)
    ip = client_ip(request)
    if limit_hit(vps_captcha_requests, ip, 12, 60):
        raise HTTPException(status_code=429, detail="Too many CAPTCHA requests. Wait before trying again.")
    return _new_vps_password_captcha(request)

@app.post('/api/vps/password')
async def vps_change_password(request: Request):
    require_auth(request)
    try:
        body = await request.json()
        current = str(body.get('current_password', ''))
        new_password = str(body.get('new_password', ''))
        confirm = str(body.get('confirm_password', ''))
        captcha_token = str(body.get('captcha_token', ''))[:128]
        captcha_answer = str(body.get('captcha_answer', '')).strip()[:8].translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'))
        ip = client_ip(request)
        if limit_hit(vps_password_attempts, ip, 5, 900):
            raise HTTPException(status_code=429, detail='Too many password-change attempts. Wait before trying again.')
        with VPS_CAPTCHA_LOCK:
            challenge = VPS_CAPTCHA_CHALLENGES.pop(captcha_token, None) if captcha_token else None
        valid_captcha = bool(
            isinstance(challenge, dict)
            and int(challenge.get('expires_at', 0)) >= int(time.time())
            and hmac.compare_digest(str(challenge.get('ip', '')).encode(), ip.encode())
            and int(challenge.get('login_at', 0)) == int(request.session.get('login_at', 0) or 0)
            and hmac.compare_digest(str(challenge.get('answer', '')).encode(), captcha_answer.encode())
        )
        if not valid_captcha:
            raise HTTPException(status_code=400, detail='CAPTCHA is incorrect or expired. Solve the new challenge and try again.')
        if not verify_password(current): raise HTTPException(status_code=403, detail='Current panel password is incorrect')
        if new_password != confirm: raise HTTPException(status_code=400, detail='New passwords do not match')
        if len(new_password) < 14 or len(new_password) > 128 or any(c in new_password for c in ('\n','\r','\x00',':')):
            raise HTTPException(status_code=400, detail='Password must be 14–128 characters and cannot contain newline or colon')
        helper = Path('/usr/local/sbin/idontmonitor-ops')
        if not helper.is_file() or helper.is_symlink(): raise HTTPException(status_code=503, detail='Trusted VPS operations helper is not installed')
        result = subprocess.run(['sudo','-n',str(helper),'change-root-password'], input=new_password+'\n',
                                capture_output=True, text=True, timeout=12, close_fds=True,
                                env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8'})
        if result.returncode != 0: raise HTTPException(status_code=500, detail='Password change failed safely; check server logs')
        logger.warning('Root account password changed through authenticated VPS management')
        return {'ok': True, 'message': 'Root VPS password changed successfully.'}
    except HTTPException: raise
    except subprocess.TimeoutExpired: raise HTTPException(status_code=504, detail='Password helper timed out')
    except Exception: raise HTTPException(status_code=400, detail='Invalid password-change request')

@app.post('/api/vps/reboot')
async def vps_reboot(request: Request):
    require_auth(request)
    try:
        body = await request.json()
        current = str(body.get("current_password", ""))
        if not verify_password(current):
            raise HTTPException(status_code=403, detail="Current password is incorrect")
        helper = Path("/usr/local/sbin/idontmonitor-ops")
        if not helper.is_file() or helper.is_symlink():
            raise HTTPException(status_code=503, detail="Trusted VPS operations helper is not installed")
        result = subprocess.run(["sudo", "-n", str(helper), "reboot-vps"], capture_output=True, text=True, timeout=5,
                                stdin=subprocess.DEVNULL, close_fds=True,
                                env={"PATH":"/usr/sbin:/usr/bin:/sbin:/bin", "LANG":"C.UTF-8"})
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail="Reboot request failed safely; check service logs")
        return {"ok": True, "message": "Reboot requested. The dashboard may disconnect briefly."}
    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        return {"ok": True, "message": "Reboot was dispatched; the server may be restarting."}
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid reboot request")

@app.get('/api/config')
def public_config(request: Request):
    require_auth(request)
    return {"version":CFG.get('version','2.3.6'),"theme_default":"Nebula Purple","themes":["Nebula Purple","Cyber Mint","Crimson Pulse","Arctic Blue","Emerald Matrix","Solar Amber","Ultra Dark", "Midnight Emerald Glass VIP"]}
