"""Restricted operations API for idontMonitor v2.3.6.

All mutating system operations pass through a fixed root-owned helper. No API
accepts a shell command, executable path, or arbitrary systemd unit name.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/ops", tags=["operations"])
STATE_DIR = Path(os.environ.get("IDONTMONITOR_STATE_DIR", "/var/lib/idontmonitor"))
AUDIT_PATH = STATE_DIR / "audit-log.json"
MAINTENANCE_PATH = STATE_DIR / "maintenance.json"
ALERTS_PATH = STATE_DIR / "alerts.json"
TRAFFIC_HISTORY_PATH = STATE_DIR / "tunnel-traffic-history.json"
HELPER = Path("/usr/local/sbin/idontmonitor-ops")

# Deliberately conservative: only known service prefixes can be managed.
TUNNEL_UNIT = re.compile(r"^(?:ctunnel@[A-Za-z0-9_.@-]+|ctunnel-engine@[A-Za-z0-9_.@-]+|backpack-[A-Za-z0-9_.@-]+|paqet(?:-[A-Za-z0-9_.@-]+)?)\.service$")
SAFE_SERVICE = re.compile(r"^[A-Za-z0-9_.@:-]{1,128}\.service$")


def _auth(request: Request) -> None:
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Authentication required")


def _run(args: list[str], timeout: float = 4.0) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                              check=False, stdin=subprocess.DEVNULL, close_fds=True,
                              env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8"})
    except (OSError, subprocess.TimeoutExpired):
        return None


def _systemd_units() -> list[dict[str, Any]]:
    result = _run(["systemctl", "list-units", "--all", "--type=service", "--no-legend", "--no-pager"], 5)
    if not result or result.returncode != 0:
        return []
    units: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        cols = line.split(None, 4)
        if len(cols) < 4:
            continue
        unit, load, active, sub = cols[:4]
        desc = cols[4] if len(cols) > 4 else ""
        if unit.endswith(".service"):
            units.append({"unit": unit, "load": load, "active": active,
                          "sub": sub, "description": desc[:160]})
    return units


def _interface_counters() -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    root = Path("/sys/class/net")
    try:
        for iface in root.iterdir():
            if iface.name == "lo":
                continue
            try:
                rx = int((iface / "statistics/rx_bytes").read_text().strip())
                tx = int((iface / "statistics/tx_bytes").read_text().strip())
                out[iface.name] = {"rx_bytes": rx, "tx_bytes": tx}
            except (OSError, ValueError):
                continue
    except OSError:
        pass
    return out


def _systemd_unit_traffic(unit: str) -> dict[str, Any] | None:
    """Read kernel/systemd per-unit accounting when the unit has IPAccounting enabled."""
    result = _run(["systemctl", "show", unit, "--no-pager", "--property=IPIngressBytes", "--property=IPEgressBytes", "--property=IPAccounting"], 3)
    if not result or result.returncode != 0:
        return None
    values = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1); values[key] = value
    try:
        rx, tx = int(values.get("IPIngressBytes", "")), int(values.get("IPEgressBytes", ""))
    except (TypeError, ValueError):
        return None
    if values.get("IPAccounting", "").lower() != "yes" or rx < 0 or tx < 0:
        return None
    return {"available": True, "interface": "systemd-ip-accounting", "rx_bytes": rx, "tx_bytes": tx,
            "source": "systemd-IPAccounting", "note": "Per-unit IPv4/IPv6 socket accounting; availability depends on service configuration."}


def _unit_exec_metadata(unit: str) -> tuple[str, list[Path]]:
    """Resolve service-specific config paths safely, including BackPack's -c TOML."""
    result = _run(["systemctl", "show", unit, "--no-pager", "--property=ExecStart"], 3)
    raw = result.stdout if result and result.returncode == 0 else ""
    candidates: list[str] = []
    candidates.extend(re.findall(r"(?:^|\s)-c\s+(/etc/backpack/[A-Za-z0-9_.-]+\.toml)(?=\s|[;}])", raw))
    candidates.extend(re.findall(r"(/[A-Za-z0-9_./-]+\.(?:json|ya?ml|toml|conf))(?=\s|[;}])", raw, re.I))
    m = re.fullmatch(r"backpack-client-([A-Za-z0-9_.-]+)\.service", unit)
    if m:
        candidates.append(f"/etc/backpack/client-{m.group(1)}.toml")
    paths: list[Path] = []; seen: set[str] = set()
    for value in candidates:
        if value in seen: continue
        seen.add(value); path=Path(value)
        try:
            resolved=path.resolve(strict=True)
            allowed=(resolved.is_relative_to(Path("/etc/backpack").resolve()) or resolved.is_relative_to(Path("/etc/paqet").resolve()))
            if path.is_absolute() and allowed and resolved.is_file() and resolved.stat().st_size <= 256_000:
                paths.append(resolved)
        except (OSError, RuntimeError): continue
    return raw, paths[:8]


def _backpack_snapshot(unit: str) -> dict[str, Any] | None:
    """Read the exact BackPack metrics snapshot beside its service-specific config."""
    _, configs = _unit_exec_metadata(unit)
    for config in configs:
        name=config.stem; path=config.parent / f"{name}.metrics.json"
        try:
            if not path.is_file() or path.is_symlink() or path.stat().st_size > 128_000: continue
            data=json.loads(path.read_text(encoding="utf-8")); rx,tx=int(data["bytes_in"]),int(data["bytes_out"])
            if rx>=0 and tx>=0 and (not data.get("name") or data.get("name")==name):
                return {"available":True,"interface":"BackPack native metrics","rx_bytes":rx,"tx_bytes":tx,
                        "source":"backpack-native-metrics","note":"Per-instance BackPack snapshot read from the exact config path.",
                        "transport":str(data.get("transport") or "").strip().lower()}
        except (OSError, ValueError, TypeError, KeyError): continue
    return None

def _traffic_for_unit(unit: str, counters: dict[str, dict[str, int]]) -> dict[str, Any]:
    """Use engine-native counters or an exact, engine-derived interface name."""
    accounted = _systemd_unit_traffic(unit)
    if accounted:
        return accounted
    stem = unit.removesuffix(".service")
    if stem.startswith("backpack-"):
        native = _backpack_snapshot(unit)
        if native:
            return native
    candidates: set[str] = set()
    is_ctunnel = stem.startswith(("ctunnel@", "ctunnel-engine@"))
    if is_ctunnel:
        # C-Tunnel defines Dev(name) as "ct-" + tunnel name. Recent releases
        # can create ECMP lane devices named <DEV>.1 through <DEV>.7; include
        # only those exact source-defined names, never arbitrary ct* interfaces.
        name = stem.split("@", 1)[1]
        base = "ct-" + name
        candidates.add(base)
        candidates.update(f"{base}.{lane}" for lane in range(1, 8))
    elif stem.startswith("paqet-"):
        # Paqet interfaces are only accepted when the exact instance-derived
        # name exists; no prefix or host-interface guessing is performed.
        candidates.add(stem)
    matches = sorted((name, data) for name, data in counters.items() if name in candidates)
    if matches:
        rx = sum(data["rx_bytes"] for _, data in matches)
        tx = sum(data["tx_bytes"] for _, data in matches)
        names = [name for name, _ in matches]
        interface = names[0] if len(names) == 1 else f"{names[0]} (+{len(names)-1} lanes)"
        note = ("Exact C-Tunnel interface and ECMP lane counters summed from real interfaces."
                if is_ctunnel else "Exact interface name derived from this tunnel instance.")
        return {"available": True, "interface": interface, "rx_bytes": rx, "tx_bytes": tx,
                "source": "engine-derived-exact-interface", "note": note,
                "interfaces": names if is_ctunnel else [names[0]]}
    return {"available": False, "interface": None, "rx_bytes": None, "tx_bytes": None,
            "source": "not-attributable", "note": "No engine-native snapshot, enabled systemd accounting, or exact engine-derived interface was found."}


def detect_tunnel_projects() -> list[dict[str, Any]]:
    """Detect project presence separately from configured/running tunnel instances."""
    files = _run(["systemctl", "list-unit-files", "--type=service", "--no-legend", "--no-pager"], 5)
    names = set()
    if files and files.returncode == 0:
        for line in files.stdout.splitlines():
            cols = line.split()
            if cols: names.add(cols[0])
    running_names = {item["unit"] for item in _systemd_units()}
    c_evidence = sorted(x for x in names | running_names if x in {"ctunnel@.service", "ctunnel-engine@.service"} or x.startswith(("ctunnel@", "ctunnel-engine@")))
    c_instances = set()
    for unit in c_evidence:
        if unit.startswith("ctunnel-engine@") and not unit.endswith("@.service"):
            c_instances.add(unit[len("ctunnel-engine@"):].removesuffix(".service"))
        elif unit.startswith("ctunnel@") and not unit.endswith("@.service"):
            c_instances.add(unit[len("ctunnel@"):].removesuffix(".service"))
    b_evidence = sorted(x for x in names | running_names if x.startswith("backpack-") and x not in {"backpack-monitor.service", "backpack-webui.service", "backpack-proxy.service"})
    b_management = sorted(x for x in names | running_names if x in {"backpack-monitor.service", "backpack-webui.service", "backpack-proxy.service"})
    p_evidence = sorted(x for x in names | running_names if (x == "paqet.service" or x.startswith("paqet-")) and x not in {"paqet-relay.service", "paqet-auto-reset.service", "paqet-tunnel.service"})
    c_bin = shutil.which("ctunnel") is not None
    b_bin = shutil.which("backpack") is not None
    p_bin = shutil.which("paqet") is not None
    return [
        {"name": "C-Tunnel", "installed": bool(c_evidence or c_bin), "evidence": c_evidence or (["binary on PATH"] if c_bin else []), "configured_instances": len(c_instances)},
        {"name": "BackPack", "installed": bool(b_evidence or b_bin or b_management), "evidence": b_evidence or b_management or (["binary on PATH"] if b_bin else []), "configured_instances": len(b_evidence)},
        {"name": "Paqet", "installed": bool(p_evidence or p_bin or Path("/etc/paqet").is_dir()), "evidence": p_evidence or (["binary on PATH"] if p_bin else (["/etc/paqet"] if Path("/etc/paqet").is_dir() else [])), "configured_instances": len(p_evidence)},
    ]


def _tunnel_protocol(unit: str) -> dict[str, Any]:
    """Read protocol labels from this service's own config and native BackPack snapshot."""
    import re
    raw, configs = _unit_exec_metadata(unit); labels: list[str]=[]; contents=[raw]
    for path in configs:
        try: contents.append(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError: pass
    transport=""
    if unit.startswith("backpack-client-"):
        for config in configs:
            snap=config.parent / f"{config.stem}.metrics.json"
            try:
                if snap.is_file() and not snap.is_symlink() and snap.stat().st_size<=128_000:
                    data=json.loads(snap.read_text(encoding="utf-8"))
                    if data.get("name") in (None,config.stem): transport=str(data.get("transport") or "").strip(); break
            except (OSError, ValueError, TypeError): pass
    if transport: labels.append(transport)
    patterns=((r"\btcpmux\b","tcpmux"),(r"\bwss\b","wss"),(r"\bws\b","ws"),(r"\bwsmux\b","wsmux"),
              (r"\bwebsocket\b","WebSocket"),(r"\bquic\b","QUIC"),(r"\bgrpc\b","gRPC"),
              (r"\bhttp2?\b","HTTP"),(r"\btcp\b","TCP"),(r"\budp\b","UDP"),(r"\bkcp\b","KCP"))
    for pattern,label in patterns:
        if any(re.search(pattern,c,re.I) for c in contents) and label not in labels: labels.append(label)
    stem=unit.removesuffix(".service")
    if stem.startswith("paqet") and not configs:
        for path in (Path("/etc/paqet/config.yaml"),Path("/etc/paqet/config.yml"),Path("/etc/paqet")/f"{stem}.yaml",Path("/etc/paqet")/f"{stem}.yml"):
            try:
                resolved=path.resolve(strict=True)
                if resolved.is_relative_to(Path("/etc/paqet").resolve()) and resolved.is_file() and resolved.stat().st_size<=256_000: contents.append(resolved.read_text(encoding="utf-8",errors="ignore"))
            except (OSError,RuntimeError): pass
    for pattern,label in patterns:
        if any(re.search(pattern,c,re.I) for c in contents) and label not in labels: labels.append(label)
    return {"protocol":labels[0] if labels else None,"protocols":labels,"config_detected":bool(configs),"config_source":"systemd-execstart" if configs else None}

def detect_tunnels() -> list[dict[str, Any]]:
    units = _systemd_units()
    counters = _interface_counters()
    found: dict[str, dict[str, Any]] = {}
    for item in units:
        unit = item["unit"]
        if not TUNNEL_UNIT.fullmatch(unit):
            continue
        # Exclude management/watchdog/relay services: they are not tunnel instances.
        if unit in {"backpack-monitor.service", "backpack-webui.service", "backpack-proxy.service",
                    "paqet-relay.service", "paqet-auto-reset.service", "paqet-tunnel.service"}:
            continue
        kind = "C-Tunnel" if unit.startswith(("ctunnel@", "ctunnel-engine@")) else (
            "BackPack" if unit.startswith("backpack") else "Paqet")
        found[unit] = {"id": unit, "name": kind, "unit": unit,
                       "installed": item["load"] != "not-found", "active": item["active"] == "active",
                       "state": item["active"], "substate": item["sub"],
                       "description": item["description"],
                       **_tunnel_protocol(unit),
                       "traffic": _traffic_for_unit(unit, counters)}
    # Installed-but-inactive unit files are useful, but only if their names match
    # the strict allowlist above. Never infer installation from a binary alone.
    files = _run(["systemctl", "list-unit-files", "--type=service", "--no-legend", "--no-pager"], 5)
    if files and files.returncode == 0:
        for line in files.stdout.splitlines():
            cols = line.split()
            if len(cols) < 2 or not TUNNEL_UNIT.fullmatch(cols[0]) or cols[0] in found or cols[0] in {
                    "backpack-monitor.service", "backpack-webui.service", "backpack-proxy.service",
                    "paqet-relay.service", "paqet-auto-reset.service", "paqet-tunnel.service"}:
                continue
            unit = cols[0]
            kind = "C-Tunnel" if unit.startswith(("ctunnel@", "ctunnel-engine@")) else ("BackPack" if unit.startswith("backpack") else "Paqet")
            found[unit] = {"id": unit, "name": kind, "unit": unit, "installed": True,
                           "active": False, "state": "inactive", "substate": "unknown",
                           "description": "Installed systemd unit; not currently loaded",
                           **_tunnel_protocol(unit),
                           "traffic": _traffic_for_unit(unit, counters)}
    return sorted(found.values(), key=lambda x: (x["name"], x["unit"]))


def _record_traffic_history(tunnels: list[dict[str, Any]]) -> None:
    samples = [ {"at": datetime.now(timezone.utc).isoformat(), "unit": t["unit"],
                 "interface": t["traffic"]["interface"], "rx_bytes": t["traffic"]["rx_bytes"],
                 "tx_bytes": t["traffic"]["tx_bytes"]}
                for t in tunnels if t.get("traffic", {}).get("available") ]
    if not samples:
        return
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        try: history = json.loads(TRAFFIC_HISTORY_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError): history = []
        if not isinstance(history, list): history = []
        history.extend(samples); history = history[-1000:]
        _write_json_atomic(TRAFFIC_HISTORY_PATH, history)
    except OSError:
        pass

def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, separators=(",", ":"))
            handle.flush(); os.fsync(handle.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
    except Exception:
        try: os.unlink(tmp_name)
        except OSError: pass
        raise

def _audit(action: str, target: str, result: str, request: Request) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            rows = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
            if not isinstance(rows, list): rows = []
        except (OSError, ValueError):
            rows = []
        rows.insert(0, {"at": datetime.now(timezone.utc).isoformat(), "action": action,
                        "target": target[:128], "result": result,
                        "ip": request.client.host if request.client else "unknown"})
        rows = rows[:1000]
        _write_json_atomic(AUDIT_PATH, rows)
    except OSError:
        pass


def _helper(action: str, target: str = "") -> tuple[bool, str]:
    if not HELPER.is_file() or not os.access(HELPER, os.X_OK):
        return False, "Restricted operations helper is not installed; mutating operations are disabled."
    args = ["sudo", "-n", str(HELPER), action]
    if target:
        args.append(target)
    result = _run(args, 20)
    if result is None:
        return False, "Operation timed out or could not be executed."
    message = (result.stdout or result.stderr or "").strip()[:500]
    return result.returncode == 0, message or ("Completed" if result.returncode == 0 else "Operation failed")


class RestartRequest(BaseModel):
    confirm: bool = False


class ServiceAction(BaseModel):
    action: str = Field(pattern="^(start|restart)$")
    confirm: bool = False

class DeleteTunnelRequest(BaseModel):
    confirm: bool = False


class MaintenanceRequest(BaseModel):
    enabled: bool
    duration_minutes: int = Field(default=60, ge=5, le=1440)
    reason: str = Field(default="", max_length=200)


class AlertSettings(BaseModel):
    enabled: bool = True
    cpu_percent: int = Field(default=90, ge=50, le=100)
    ram_percent: int = Field(default=90, ge=50, le=100)
    disk_percent: int = Field(default=90, ge=50, le=100)

class RestorePayload(BaseModel):
    format: str = Field(pattern="^idontmonitor-ops-backup-v1$")
    alerts: AlertSettings = Field(default_factory=AlertSettings)


@router.get("/summary")
def summary(request: Request):
    _auth(request)
    tunnels = detect_tunnels()
    projects = detect_tunnel_projects()
    _record_traffic_history(tunnels)
    cpu = shutil.disk_usage("/")
    disk_percent = round(cpu.used / cpu.total * 100, 1) if cpu.total else 0
    active = sum(1 for t in tunnels if t["active"])
    score = max(0, min(100, round(100 - disk_percent * 0.25 - max(0, len(tunnels)-active)*8)))
    maintenance = {}
    try: maintenance = json.loads(MAINTENANCE_PATH.read_text())
    except (OSError, ValueError): pass
    measurable = [t["traffic"] for t in tunnels if t.get("traffic", {}).get("available")]
    traffic_total = {"available": bool(measurable), "rx_bytes": sum(int(x["rx_bytes"]) for x in measurable),
                     "tx_bytes": sum(int(x["tx_bytes"]) for x in measurable), "measured_tunnels": len(measurable),
                     "total_tunnels": len(tunnels), "coverage": "partial" if measurable and len(measurable) < len(tunnels) else ("complete" if measurable and len(measurable) == len(tunnels) else "unavailable"),
                     "source": "sum-of-verified-tunnel-counters"}
    return {"version": "2.3.6", "tunnels": tunnels, "projects": projects, "traffic_total": traffic_total, "tunnel_count": len(tunnels),
            "active_tunnels": active, "health_score": score, "disk_percent": disk_percent,
            "maintenance": maintenance, "generated_at": datetime.now(timezone.utc).isoformat(),
            "score_note": "Basic score uses verified disk usage and detected service state only; it is not a full reliability prediction."}


@router.get("/tunnels")
def tunnels(request: Request):
    _auth(request)
    items = detect_tunnels(); _record_traffic_history(items)
    measurable = [t["traffic"] for t in items if t.get("traffic", {}).get("available")]
    traffic_total = {"available": bool(measurable), "rx_bytes": sum(int(x["rx_bytes"]) for x in measurable),
                     "tx_bytes": sum(int(x["tx_bytes"]) for x in measurable), "measured_tunnels": len(measurable),
                     "total_tunnels": len(items), "coverage": "partial" if measurable and len(measurable) < len(items) else ("complete" if measurable and len(measurable) == len(items) else "unavailable"),
                     "source": "sum-of-verified-tunnel-counters"}
    return {"items": items, "traffic_total": traffic_total, "projects": detect_tunnel_projects(), "generated_at": datetime.now(timezone.utc).isoformat()}

@router.get("/tunnels/history")
def tunnel_history(request: Request):
    _auth(request)
    try: rows = json.loads(TRAFFIC_HISTORY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError): rows = []
    return {"items": rows[-200:] if isinstance(rows, list) else [],
            "note": "History contains only samples mapped to a verified tunnel network interface. No sample means per-tunnel counters are unavailable on this host."}


@router.post("/tunnels/restart-all")
def restart_all(request: Request, payload: RestartRequest):
    _auth(request)
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required.")
    items = detect_tunnels()
    results = []
    for item in items:
        if not item["installed"]:
            continue
        if not item["active"]:
            results.append({"unit": item["unit"], "ok": False,
                            "detail": "Skipped: service is inactive; no automatic start was attempted."})
            _audit("restart-tunnel", item["unit"], "skipped-inactive", request)
            continue
        ok, detail = _helper("restart-tunnel", item["unit"])
        results.append({"unit": item["unit"], "ok": ok, "detail": detail})
        _audit("restart-tunnel", item["unit"], "success" if ok else "failed", request)
    return {"results": results, "count": len(results), "success_count": sum(1 for x in results if x["ok"])}


@router.delete("/tunnels/{unit}")
def delete_tunnel(unit: str, payload: DeleteTunnelRequest, request: Request):
    """Remove a detected tunnel service definition, never its config/data files."""
    _auth(request)
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required.")
    if not TUNNEL_UNIT.fullmatch(unit) or unit in {"backpack-monitor.service", "backpack-webui.service", "backpack-proxy.service", "paqet-relay.service", "paqet-auto-reset.service", "paqet-tunnel.service"}:
        raise HTTPException(status_code=400, detail="This unit is not an eligible tunnel instance.")
    # Require an installed custom unit file directly under /etc/systemd/system.
    unit_path = Path("/etc/systemd/system") / unit
    if not unit_path.is_file() or unit_path.is_symlink():
        raise HTTPException(status_code=409, detail="Only a regular custom unit file in /etc/systemd/system can be removed. Package-managed units are protected.")
    ok, detail = _helper("delete-tunnel", unit)
    _audit("delete-tunnel", unit, "success" if ok else "failed", request)
    if not ok:
        raise HTTPException(status_code=409, detail=detail)
    return {"ok": True, "unit": unit, "detail": detail, "configuration_preserved": True}


@router.get("/services")
def services(request: Request):
    _auth(request)
    # Intentionally bounded to a known service set; do not expose every host unit.
    allowed_prefixes = ("idontmonitor", "caddy", "ssh", "sshd", "ctunnel", "backpack", "paqet", "fail2ban", "ufw")
    excluded = {"backpack-monitor.service", "backpack-webui.service", "backpack-proxy.service",
                "paqet-relay.service", "paqet-auto-reset.service", "paqet-tunnel.service"}
    return {"items": [u for u in _systemd_units() if u["unit"] not in excluded and
                       u["unit"].split("@")[0].split("-")[0].startswith(allowed_prefixes)][:100]}


@router.post("/services/{unit}/action")
def service_action(unit: str, payload: ServiceAction, request: Request):
    _auth(request)
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required.")
    if not SAFE_SERVICE.fullmatch(unit) or unit == "idontmonitor.service":
        raise HTTPException(status_code=400, detail="This service is not eligible for remote operations.")
    if payload.action not in ("start", "restart"):
        raise HTTPException(status_code=400, detail="Unsupported action.")
    ok, detail = _helper("service", f"{payload.action}:{unit}")
    _audit(f"service-{payload.action}", unit, "success" if ok else "failed", request)
    if not ok:
        raise HTTPException(status_code=409, detail=detail)
    return {"ok": True, "unit": unit, "action": payload.action, "detail": detail}


@router.get("/audit")
def audit(request: Request):
    _auth(request)
    try: rows = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError): rows = []
    return {"items": rows[:200] if isinstance(rows, list) else []}


@router.get("/diagnostics")
def diagnostics(request: Request):
    _auth(request)
    probes = []
    for label, args in [
        ("systemd", ["systemctl", "is-system-running"]),
        ("disk", ["df", "-P", "/"]),
        ("memory", ["free", "-b"]),
        ("uptime", ["uptime"]),
    ]:
        result = _run(args, 3)
        probes.append({"name": label, "ok": bool(result and result.returncode == 0),
                       "output": ((result.stdout or result.stderr).strip()[:2000] if result else "Probe unavailable")})
    tunnels = detect_tunnels()
    probes.append({"name": "tunnels", "ok": all(t["active"] for t in tunnels) if tunnels else True,
                   "output": f"{sum(t['active'] for t in tunnels)} active of {len(tunnels)} detected; no tunnel was inferred when absent."})
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "probes": probes}


@router.get("/maintenance")
def maintenance_status(request: Request):
    _auth(request)
    try: data = json.loads(MAINTENANCE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError): data = {"enabled": False}
    if data.get("enabled") and data.get("expires_at", 0) <= time.time():
        data = {"enabled": False, "expired": True}
        try: MAINTENANCE_PATH.unlink(missing_ok=True)
        except OSError: pass
    return data


@router.post("/maintenance")
def set_maintenance(payload: MaintenanceRequest, request: Request):
    _auth(request)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    data = {"enabled": payload.enabled, "reason": payload.reason.strip(),
            "updated_at": time.time(), "expires_at": time.time() + payload.duration_minutes * 60 if payload.enabled else 0}
    _write_json_atomic(MAINTENANCE_PATH, data)
    _audit("maintenance", "enabled" if payload.enabled else "disabled", "success", request)
    return data


def _resource_snapshot() -> dict[str, float]:
    cpu_percent = 0.0
    try:
        def _cpu():
            parts = Path("/proc/stat").read_text().splitlines()[0].split()[1:]
            values = list(map(int, parts)); return sum(values), values[3] + (values[4] if len(values) > 4 else 0)
        total_a, idle_a = _cpu(); time.sleep(0.08); total_b, idle_b = _cpu()
        total_delta, idle_delta = total_b-total_a, idle_b-idle_a
        cpu_percent = round(max(0, min(100, (1-idle_delta/total_delta)*100)), 1) if total_delta else 0.0
    except (OSError, ValueError, ZeroDivisionError, IndexError):
        pass
    disk = shutil.disk_usage("/")
    disk_percent = disk.used / disk.total * 100 if disk.total else 0.0
    memory = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            memory[key] = int(value.strip().split()[0]) * 1024
    except (OSError, ValueError):
        pass
    total = memory.get("MemTotal", 0)
    available = memory.get("MemAvailable", memory.get("MemFree", 0))
    ram_percent = max(0, (total - available) / total * 100) if total else 0.0
    return {"cpu_percent": cpu_percent, "disk_percent": round(disk_percent, 1), "ram_percent": round(ram_percent, 1)}

@router.get("/alerts")
def get_alerts(request: Request):
    _auth(request)
    try: settings = AlertSettings(**json.loads(ALERTS_PATH.read_text(encoding="utf-8"))).model_dump()
    except (OSError, ValueError, TypeError): settings = AlertSettings().model_dump()
    current = _resource_snapshot()
    events = []
    if settings.get("enabled"):
        for key, label in (("cpu_percent", "CPU usage"), ("ram_percent", "Memory usage"), ("disk_percent", "Root filesystem usage")):
            if current[key] >= settings[key]:
                events.append({"id": key, "level": "warning", "label": label,
                               "value_percent": current[key], "threshold_percent": settings[key]})
    tunnels = detect_tunnels()
    down = [t for t in tunnels if not t["active"]]
    if settings.get("enabled") and down:
        events.append({"id": "tunnel-down", "level": "warning", "label": "Tunnel service inactive",
                       "units": [t["unit"] for t in down]})
    maintenance = {}
    try: maintenance = json.loads(MAINTENANCE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError): pass
    suppressed = bool(maintenance.get("enabled") and maintenance.get("expires_at", 0) > time.time())
    return {"settings": settings, "current": current, "events": [] if suppressed else events,
            "maintenance_suppressed": suppressed,
            "note": "Alerts are evaluated on panel refresh. External push delivery (Telegram/email) is not configured."}


@router.post("/alerts")
def save_alerts(payload: AlertSettings, request: Request):
    _auth(request)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(ALERTS_PATH, payload.model_dump())
    _audit("alert-settings", "thresholds", "success", request)
    return {"settings": payload.model_dump(), "note": "Thresholds saved. Delivery channels are not configured."}


@router.get("/backup")
def export_backup(request: Request):
    _auth(request)
    try: alerts = json.loads(ALERTS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError): alerts = AlertSettings().model_dump()
    # Export only user-adjustable operations preferences, never credentials, session
    # secrets, SSH keys, tunnel configs, or raw logs.
    _audit("backup-export", "operations-settings", "success", request)
    return {"format": "idontmonitor-ops-backup-v1", "created_at": datetime.now(timezone.utc).isoformat(),
            "alerts": AlertSettings(**alerts).model_dump()}

@router.post("/restore")
def import_backup(payload: RestorePayload, request: Request):
    _auth(request)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(ALERTS_PATH, payload.alerts.model_dump())
    _audit("backup-restore", "operations-settings", "success", request)
    return {"ok": True, "message": "Operations preferences restored. Credentials and tunnel configurations were not included in this backup."}

@router.get("/terminal")
def terminal_catalog(request: Request):
    _auth(request)
    return {"commands": [
        {"id": "uptime", "label": "Uptime", "description": "Host uptime and load averages"},
        {"id": "memory", "label": "Memory", "description": "Memory totals from free -b"},
        {"id": "disk", "label": "Disk", "description": "Filesystem usage from df -P /"},
        {"id": "tunnel-status", "label": "Tunnel status", "description": "Detected tunnel unit states"},
        {"id": "systemd-status", "label": "System manager status", "description": "systemctl is-system-running"},
    ], "mode": "allowlisted local diagnostics", "arbitrary_shell": False}


@router.post("/terminal/{command_id}")
def run_safe_command(command_id: str, request: Request):
    _auth(request)
    catalog = {"uptime": ["uptime"], "memory": ["free", "-b"], "disk": ["df", "-P", "/"],
               "systemd-status": ["systemctl", "is-system-running"]}
    if command_id == "tunnel-status":
        result = {"output": json.dumps(detect_tunnels(), ensure_ascii=False, indent=2), "ok": True}
    elif command_id in catalog:
        proc = _run(catalog[command_id], 4)
        result = {"output": ((proc.stdout or proc.stderr).strip()[:4000] if proc else "Command unavailable"),
                  "ok": bool(proc and proc.returncode == 0)}
    else:
        raise HTTPException(status_code=404, detail="Command is not in the allowlist.")
    _audit("safe-command", command_id, "success" if result["ok"] else "failed", request)
    return result
