"""Restricted operations API for idontMonitor v4.0.2.

All mutating system operations pass through a fixed root-owned helper. No API
accepts a shell command, executable path, or arbitrary systemd unit name.
"""
from __future__ import annotations

import json
import os
import signal
import re
import socket
import statistics
import shutil
import subprocess
import tempfile
import time
import tomllib
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

API_VERSION = "4.0.2"
router = APIRouter(prefix="/api/ops", tags=["operations"])
# No files were deleted. Analyzer scans remain read-only unless a separately
# authorized managed-log cleanup action is explicitly confirmed.
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
    m = re.fullmatch(r"backpack-([A-Za-z0-9_.-]+)\.service", unit)
    if m:
        # BackPack app.ConfigDir is /etc/backpack; config and metrics use the
        # tunnel name directly (name.toml / name.metrics.json), not client-name.
        candidates.append(f"/etc/backpack/{m.group(1)}.toml")
    m = re.fullmatch(r"ctunnel(?:-engine)?@([A-Za-z0-9_.-]+)\.service", unit)
    if m:
        # C-Tunnel's canonical catalog is /etc/ctunnel/state.json; per-instance
        # engine env is under /etc/ctunnel/tunnels/<name>.env.
        candidates.extend(["/etc/ctunnel/state.json", f"/etc/ctunnel/tunnels/{m.group(1)}.env"])
    paths: list[Path] = []; seen: set[str] = set()
    for value in candidates:
        if value in seen: continue
        seen.add(value); path=Path(value)
        try:
            resolved=path.resolve(strict=True)
            allowed=(resolved.is_relative_to(Path("/etc/backpack").resolve()) or resolved.is_relative_to(Path("/etc/paqet").resolve()) or resolved.is_relative_to(Path("/etc/ctunnel").resolve()))
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
    # The helper is intentionally root:root 0750. Checking os.access(X_OK)
    # as the unprivileged web user falsely reports it as non-executable even
    # though sudo is allowed to execute it. Validate its trusted metadata here;
    # let sudo perform the actual privileged execution check.
    try:
        st = HELPER.lstat()
        if (not __import__("stat").S_ISREG(st.st_mode) or st.st_uid != 0
                or not (st.st_mode & 0o100) or HELPER.is_symlink()):
            return False, "Restricted operations helper is missing or failed root ownership/permission checks. Run the official installer/update as root."
    except OSError:
        return False, "Restricted operations helper is not installed. Run the official installer/update as root."
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



# Version 3 resource/tunnel intelligence. Every probe is bounded and read-only.
MANAGED_LOG_DIR = Path(os.environ.get("IDONTMONITOR_LOG_DIR", "/var/log/idontmonitor"))
MANAGED_LOG_NAMES = ("idontmonitor.log", "idontmonitor.log.1", "idontmonitor.log.2", "idontmonitor.log.3")
LOG_MANAGER_SETTINGS = STATE_DIR / "log-manager.json"


def _safe_managed_logs() -> list[dict[str, Any]]:
    """Return only known regular, non-symlink app log files under the configured directory."""
    items = []
    try:
        base = MANAGED_LOG_DIR.resolve(strict=True)
        if not base.is_dir() or MANAGED_LOG_DIR.is_symlink():
            return []
    except (OSError, RuntimeError):
        return []
    for name in MANAGED_LOG_NAMES:
        candidate = MANAGED_LOG_DIR / name
        try:
            if candidate.is_symlink() or not candidate.is_file():
                continue
            resolved = candidate.resolve(strict=True)
            if resolved.parent != base or not resolved.is_relative_to(base):
                continue
            st = resolved.stat()
            if not __import__("stat").S_ISREG(st.st_mode):
                continue
            items.append({"name": name, "path": str(resolved), "size_bytes": st.st_size,
                          "modified_at": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                          "managed": True, "deletable": True})
        except (OSError, RuntimeError):
            continue
    return sorted(items, key=lambda x: (-x["size_bytes"], x["name"]))


def _read_log_manager_settings() -> dict[str, Any]:
    try:
        data = json.loads(LOG_MANAGER_SETTINGS.read_text(encoding="utf-8"))
        cap = int(data.get("cap_bytes", 1024**3))
        if not 64 * 1024**2 <= cap <= 10 * 1024**3:
            raise ValueError("invalid cap")
        return {"cap_bytes": cap, "enabled": bool(data.get("enabled", True))}
    except (OSError, ValueError, TypeError):
        return {"cap_bytes": 1024**3, "enabled": True}


def _atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="." + path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False)
            stream.flush(); os.fsync(stream.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        try: os.unlink(tmp)
        except OSError: pass


def _clean_endpoint_host(value: Any) -> str | None:
    """Normalize an engine-reported peer (host, host:port, or [IPv6]:port)."""
    if not isinstance(value, str):
        return None
    host = value.strip().strip("\\\"'")
    if not host:
        return None
    if host.startswith("[") and "]" in host:
        host = host[1:host.index("]")]
    elif host.count(":") == 1:
        maybe_host, maybe_port = host.rsplit(":", 1)
        if maybe_port.isdigit():
            host = maybe_host
    if host.lower() in {"localhost", "0.0.0.0", "::", "127.0.0.1", "*"}:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_.:%-]{1,253}", host):
        return None
    try:
        socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        return host
    except (OSError, UnicodeError):
        return None


def _ctunnel_config(name: str) -> dict[str, Any] | None:
    """Read one exact C-Tunnel entry from its canonical Store state."""
    state = Path("/etc/ctunnel/state.json")
    try:
        if state.is_symlink() or not state.is_file() or state.stat().st_size > 512_000:
            return None
        data = json.loads(state.read_text(encoding="utf-8"))
        tunnels = data.get("tunnels", []) if isinstance(data, dict) else []
        for tunnel in tunnels:
            if isinstance(tunnel, dict) and tunnel.get("name") == name:
                return tunnel
    except (OSError, ValueError, TypeError):
        pass
    return None


def _backpack_snapshot_for_unit(unit: str) -> dict[str, Any] | None:
    """Read BackPack's native snapshot from /etc/backpack/<instance>.metrics.json."""
    match = re.fullmatch(r"backpack-([A-Za-z0-9_.-]+)\.service", unit)
    if not match:
        return None
    path = Path("/etc/backpack") / f"{match.group(1)}.metrics.json"
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 128_000:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("name") not in (None, match.group(1)):
            return None
        taken = data.get("taken")
        age = None
        if isinstance(taken, str):
            try:
                stamp = datetime.fromisoformat(taken.replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    stamp = stamp.replace(tzinfo=timezone.utc)
                age = max(0.0, (datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds())
            except ValueError:
                pass
        return {"peer": data.get("peer"), "connected": data.get("connected"),
                "snapshot_age_seconds": age, "snapshot_fresh": age is not None and age <= 90,
                "taken": taken, "role": data.get("role"), "transport": data.get("transport")}
    except (OSError, ValueError, TypeError):
        return None


def _endpoint_info_for_unit(unit: str) -> dict[str, Any]:
    """Return a verified endpoint and, where possible, the correct tunnel device."""
    ct = re.fullmatch(r"ctunnel(?:-engine)?@([A-Za-z0-9_.-]+)\.service", unit)
    if ct:
        name = ct.group(1)
        cfg = _ctunnel_config(name) or {}
        remote = _clean_endpoint_host(cfg.get("remote_ip"))
        reverse = bool(cfg.get("reverse"))
        tun_remote = _clean_endpoint_host(cfg.get("tun_remote4"))
        # Reverse C-Tunnel listeners intentionally use 0.0.0.0 as RemoteIP.
        # Probe the configured inner peer through the exact ct-<name> device.
        if reverse or remote is None:
            if tun_remote:
                return {"host": tun_remote, "interface": "ct-" + name,
                        "source": "ctunnel-tun-remote4", "mode": "tunnel-peer"}
            return {"host": None, "interface": None, "source": "ctunnel-reverse-no-peer",
                    "mode": "unavailable"}
        return {"host": remote, "interface": None, "source": "ctunnel-remote-ip",
                "mode": "underlay-endpoint"}
    bp = re.fullmatch(r"backpack-([A-Za-z0-9_.-]+)\.service", unit)
    if bp:
        snap = _backpack_snapshot_for_unit(unit)
        # Peer is authoritative only while the native snapshot is fresh and
        # the engine explicitly confirms a connected peer.
        if snap and snap.get("snapshot_fresh") and snap.get("connected") is True:
            peer = _clean_endpoint_host(snap.get("peer"))
            if peer:
                return {"host": peer, "interface": None, "source": "backpack-native-peer",
                        "mode": "connected-peer", "native": snap}
        # A fresh snapshot saying disconnected must not fall back to stale config
        # and display a misleading green/reachable peer.
        if snap and snap.get("snapshot_fresh") and snap.get("connected") is False:
            return {"host": None, "interface": None, "source": "backpack-native-disconnected",
                    "mode": "disconnected", "native": snap}
    # Generic fallback remains limited to exact config fields and safe roots.
    candidates: list[str] = []
    if bp:
        name = bp.group(1)
        config = Path("/etc/backpack") / f"{name}.toml"
        try:
            if config.is_file() and not config.is_symlink() and config.stat().st_size <= 256_000:
                parsed = tomllib.loads(config.read_text(encoding="utf-8"))
                sections = [parsed] + [v for v in parsed.values() if isinstance(v, dict)]
                for section in sections:
                    for key in ("server", "remote", "endpoint", "peer", "server_addr", "remote_addr", "remote_address"):
                        value = section.get(key)
                        if isinstance(value, str): candidates.append(value)
                        elif isinstance(value, dict):
                            candidates.extend(str(value[k]) for k in ("host", "address", "ip") if isinstance(value.get(k), str))
        except (OSError, ValueError, tomllib.TOMLDecodeError):
            pass
    _, configs = _unit_exec_metadata(unit)
    for path in configs:
        try:
            if path.is_symlink() or path.stat().st_size > 256_000:
                continue
            raw = path.read_text(encoding="utf-8", errors="ignore")
            candidates.extend(re.findall(
                r'(?im)^\s*(?:server|endpoint|remote|address|host|peer|server_addr|remote_addr|server_address|remote_address|remote_ip|RemoteIP|REMOTE_IP)\s*[:=]\s*["\\\']?([A-Za-z0-9_.:%-]{1,253})', raw))
        except OSError:
            continue
    for candidate in candidates:
        host = _clean_endpoint_host(candidate)
        if host:
            return {"host": host, "interface": None, "source": "verified-config-fallback",
                    "mode": "underlay-endpoint"}
    return {"host": None, "interface": None, "source": "no-verified-endpoint", "mode": "unavailable"}


def _endpoint_for_unit(unit: str) -> str | None:
    """Backward-compatible endpoint resolver."""
    return _endpoint_info_for_unit(unit).get("host")


def _ping_endpoint(host: str, interface: str | None = None) -> dict[str, Any]:
    """One bounded ICMP probe. This measures configured endpoint reachability, not data-plane latency."""
    if not shutil.which("ping"):
        return {"available": False, "status": "unsupported", "latency_ms": None, "note": "ping utility unavailable"}
    command = [shutil.which("ping") or "ping", "-n", "-c", "1", "-W", "1"]
    if interface and re.fullmatch(r"ct-[a-z0-9-]{1,12}", interface):
        command.extend(["-I", interface])
    command.append(host)
    result = _run(command, 2.5)
    if result is None:
        return {"available": False, "status": "timeout", "latency_ms": None, "note": "probe timed out"}
    match = re.search(r"time[=<]([0-9]+(?:\.[0-9]+)?)\s*ms", result.stdout or "")
    if result.returncode == 0 and match:
        label = "ICMP through the configured tunnel interface; not application RTT" if interface else "ICMP to configured underlay endpoint; not end-to-end tunnel latency"
        return {"available": True, "status": "reachable", "latency_ms": float(match.group(1)), "note": label}
    return {"available": False, "status": "unreachable", "latency_ms": None, "note": "endpoint did not answer ICMP; ICMP may be filtered"}


def _proc_start_ticks(proc: Path) -> int | None:
    try:
        raw = (proc / "stat").read_text(encoding="ascii", errors="ignore")
        tail = raw[raw.rfind(")") + 2:].split()
        return int(tail[19])  # field 22 (starttime), after pid/comm/state prefix
    except (OSError, ValueError, IndexError):
        return None


def _ram_top5() -> list[dict[str, Any]]:
    """Read /proc process data without shell commands; exclude kernel/system-owned and PID 1."""
    rows = []
    try:
        page = os.sysconf("SC_PAGE_SIZE")
        for proc in Path("/proc").iterdir():
            if not proc.name.isdigit() or proc.name == "1": continue
            try:
                status = (proc / "status").read_text(encoding="utf-8", errors="ignore")
                vals = dict(re.findall(r"^(Name|State|Uid|VmRSS):\s*(.+)$", status, re.M))
                rss_match = re.match(r"(\d+)\s+kB", vals.get("VmRSS", ""))
                if not rss_match: continue
                uid = int(vals.get("Uid", "0").split()[0])
                if uid == 0: continue
                name = vals.get("Name", proc.name)[:128]
                try: exe = os.readlink(proc / "exe")[:512]
                except OSError: exe = "unavailable"
                rows.append({"pid": int(proc.name), "name": name, "user": str(uid), "state": vals.get("State", "unknown")[:40],
                             "ram_bytes": int(rss_match.group(1))*1024, "executable": exe, "start_ticks": _proc_start_ticks(proc)})
            except (OSError, ValueError, PermissionError): continue
    except OSError: return []
    return sorted(rows, key=lambda x: x["ram_bytes"], reverse=True)[:5]


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




@router.post("/analyzer/ram/{pid}/stop")
def analyzer_stop_process(pid: int, payload: dict[str, Any], request: Request):
    _auth(request)
    if not payload.get("confirm") or pid <= 1:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required")
    proc = Path("/proc") / str(pid)
    try:
        status = (proc / "status").read_text(encoding="utf-8", errors="ignore")
        vals = dict(re.findall(r"^(Name|Uid):\s*(.+)$", status, re.M))
        uid = int(vals.get("Uid", "0").split()[0])
        name = vals.get("Name", "unknown")
        expected = payload.get("start_ticks")
        current = _proc_start_ticks(proc)
        if uid == 0 or name in {"systemd", "sshd", "dockerd", "containerd", "postgres", "redis-server", "idontmonitor"} or expected is None or current != int(expected):
            raise HTTPException(status_code=403, detail="Process is protected or changed since scan")
        os.kill(pid, signal.SIGTERM)
    except HTTPException:
        raise
    except (OSError, ValueError, TypeError, ProcessLookupError):
        raise HTTPException(status_code=409, detail="Process no longer exists or could not be stopped")
    _audit("ram-process-stop", f"pid={pid};name={name}", "requested", request)
    return {"ok": True, "detail": "SIGTERM sent; verify service health before stopping additional processes."}


@router.post("/analyzer/ram/stop")
def analyzer_stop_processes(payload: dict[str, Any], request: Request):
    """Stop only explicitly selected, revalidated non-root user processes."""
    _auth(request)
    if not payload.get("confirm"):
        raise HTTPException(status_code=400, detail="Explicit confirmation is required")
    targets = payload.get("processes", [])
    if not isinstance(targets, list) or not targets or len(targets) > 40:
        raise HTTPException(status_code=422, detail="Provide 1–40 scanned processes")
    protected = {"systemd", "sshd", "dockerd", "containerd", "postgres", "redis-server", "idontmonitor"}
    stopped: list[int] = []; skipped: list[int] = []
    for target in targets:
        try:
            if not isinstance(target, dict):
                skipped.append(0); continue
            pid = int(target.get("pid", 0)); expected = int(target.get("start_ticks", -1))
            if pid <= 1 or expected < 0:
                skipped.append(pid); continue
            proc = Path("/proc") / str(pid)
            status = (proc / "status").read_text(encoding="utf-8", errors="ignore")
            vals = dict(re.findall(r"^(Name|Uid):\s*(.+)$", status, re.M))
            uid = int(vals.get("Uid", "0").split()[0]); name = vals.get("Name", "unknown")
            if uid == 0 or name in protected or _proc_start_ticks(proc) != expected:
                skipped.append(pid); continue
            os.kill(pid, signal.SIGTERM); stopped.append(pid)
        except (OSError, ValueError, TypeError, ProcessLookupError):
            skipped.append(int(target.get("pid", 0)) if isinstance(target, dict) else 0)
    _audit("ram-process-bulk-stop", f"stopped={stopped};skipped={skipped}", "requested", request)
    return {"ok": True, "stopped": stopped, "skipped": skipped,
            "detail": "SIGTERM sent only to eligible non-root processes; verify application health."}


@router.post("/analyzer/disk/delete")
def analyzer_delete_logs(payload: dict[str, Any], request: Request):
    _auth(request)
    if not payload.get("confirm"):
        raise HTTPException(status_code=400, detail="Explicit confirmation is required")
    requested = payload.get("names", [])
    if not isinstance(requested, list) or not requested or len(requested) > len(MANAGED_LOG_NAMES):
        raise HTTPException(status_code=422, detail="Provide one or more managed log names")
    if any(name not in MANAGED_LOG_NAMES for name in requested):
        raise HTTPException(status_code=403, detail="Only explicitly managed idontMonitor log files may be removed")
    removed = []; errors = []
    try:
        MANAGED_LOG_DIR.mkdir(parents=True, exist_ok=True)
        base = MANAGED_LOG_DIR.resolve(strict=True)
        if MANAGED_LOG_DIR.is_symlink() or not base.is_dir():
            raise HTTPException(status_code=403, detail="Managed log directory failed safety checks")
    except (OSError, RuntimeError):
        raise HTTPException(status_code=404, detail="Managed log directory is unavailable")

    # Never unlink the active log inode while Python handlers still hold it open.
    # Flush, close and reopen the RotatingFileHandler under its lock so the next
    # log record is written to a newly-created active file immediately.
    active_name = "idontmonitor.log"
    active_requested = active_name in requested
    handlers = [h for h in logging.getLogger("idontmonitor").handlers
                if isinstance(h, RotatingFileHandler)
                and Path(h.baseFilename).resolve() == (base / active_name)]
    if active_requested and handlers:
        for handler in handlers:
            try:
                handler.acquire()
                try:
                    handler.flush()
                    if handler.stream:
                        handler.stream.close()
                        handler.stream = None
                    active = base / active_name
                    if active.is_symlink():
                        raise OSError("active log path is a symlink")
                    active.unlink(missing_ok=True)
                    handler.stream = handler._open()
                    os.chmod(active, 0o600)
                    removed.append(active_name)
                finally:
                    handler.release()
            except OSError:
                errors.append(active_name)
    for name in dict.fromkeys(requested):
        if name == active_name:
            continue
        target = base / name
        try:
            if target.is_symlink() or not target.is_file() or target.resolve(strict=True).parent != base:
                errors.append(name); continue
            target.unlink(); removed.append(name)
        except OSError:
            errors.append(name)
    # Keep an active file present even on hosts where logging is initialized lazily.
    active = base / active_name
    if active_requested and not active.exists() and not active.is_symlink():
        try:
            fd = os.open(active, os.O_CREAT | os.O_APPEND | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
            os.close(fd)
            if active_name not in removed: removed.append(active_name)
        except OSError:
            if active_name not in errors: errors.append(active_name)
    _audit("managed-log-clear", ",".join(removed), "success" if removed else "failed", request)
    return {"ok": bool(removed), "removed": removed, "failed": errors,
            "detail": "Managed logs were cleared. The active idontMonitor log file is recreated and ready for new records."}


@router.get("/log-manager")
def log_manager(request: Request):
    _auth(request)
    items = _safe_managed_logs(); settings = _read_log_manager_settings()
    total = sum(x["size_bytes"] for x in items)
    return {"settings": settings, "items": items, "total_bytes": total,
            "cap_reached": total >= settings["cap_bytes"],
            "rotation_policy": "Python RotatingFileHandler; active log + three rotated files; existing handler cap is 100 MiB per file.",
            "deletion_enabled": False,
            "safety_note": "The manager never deletes arbitrary files. Existing application log rotation is bounded; cap setting is informational until a validated runtime reconfiguration is available."}


@router.post("/log-manager")
def update_log_manager(payload: dict[str, Any], request: Request):
    _auth(request)
    try:
        cap = int(payload.get("cap_bytes", 1024**3))
        enabled = bool(payload.get("enabled", True))
        if not 64 * 1024**2 <= cap <= 10 * 1024**3:
            raise ValueError
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="cap_bytes must be between 64 MiB and 10 GiB")
    # Persist settings atomically; do not trigger deletion or change open log files.
    _atomic_json(LOG_MANAGER_SETTINGS, {"cap_bytes": cap, "enabled": enabled})
    _audit("log-manager-settings", "managed-application-logs", "success", request)
    return {"ok": True, "settings": {"cap_bytes": cap, "enabled": enabled},
            "note": "Settings saved. No files were deleted; current handler rotation remains bounded at 100 MiB x 4 files."}


def _backpack_engine_health(unit: str) -> dict[str, Any] | None:
    match = re.fullmatch(r"backpack-([A-Za-z0-9_.-]+)\.service", unit)
    if not match: return None
    path = Path("/etc/backpack") / f"{match.group(1)}.metrics.json"
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 128_000: return {"state":"unknown","detail":"BackPack snapshot unavailable"}
        data=json.loads(path.read_text(encoding="utf-8"))
        taken=data.get("taken")
        age=None
        if isinstance(taken,str):
            try: age=(datetime.now(timezone.utc)-datetime.fromisoformat(taken.replace("Z","+00:00"))).total_seconds()
            except ValueError: pass
        connected=data.get("connected")
        if age is None or age>90: state="stale"
        elif connected is True: state="online"
        elif connected is False: state="offline"
        elif connected is None: state="unknown"
        else: state="unknown"
        detail = {"online":"Engine confirms an active control peer; ICMP may still be filtered.",
                  "offline":"Engine explicitly reports that the control peer is disconnected.",
                  "stale":"Native metrics snapshot is older than 90 seconds; engine state is not current.",
                  "unknown":"This engine snapshot does not contain an explicit connected state."}.get(state, "Native engine state unavailable")
        return {"state":state,"peer":str(data.get("peer") or "")[:160],"connected":connected,
                "transport":str(data.get("transport") or ""),"role":str(data.get("role") or ""),
                "snapshot_age_seconds":round(age,1) if age is not None else None,"detail":detail}
    except (OSError,ValueError,TypeError): return {"state":"unknown","detail":"BackPack snapshot could not be read"}


@router.get("/tunnels/ping")
def tunnel_pings(request: Request):
    _auth(request)
    rows = []
    for item in detect_tunnels():
        info = _endpoint_info_for_unit(item["unit"]) if item.get("active") else {"host": None, "interface": None, "source": "service-inactive", "mode": "unavailable"}
        host = info.get("host")
        if not host:
            native = info.get("native") or (_backpack_snapshot_for_unit(item["unit"]) if item["unit"].startswith("backpack-") else None)
            state = "disconnected" if info.get("mode") == "disconnected" else "unavailable"
            ping = {"available": False, "status": state, "latency_ms": None,
                    "note": ("BackPack engine reports no connected peer." if state == "disconnected" else
                             "No verified peer/endpoint is available; service state alone is not tunnel health."),
                    "source": info.get("source"), "native": native}
        else:
            ping = {**_ping_endpoint(host, info.get("interface")), "host": host,
                    "interface": info.get("interface"), "source": info.get("source"),
                    "mode": info.get("mode"), "native": info.get("native")}
        engine_health = _backpack_engine_health(item["unit"]) if item["unit"].startswith("backpack-") else None
        rows.append({"unit": item["unit"], "type": item["name"], "active": item["active"], "ping": ping,
                     "engine_health": engine_health,
                     "health_summary": ("Native BackPack peer connected; ICMP probe is independent" if engine_health and engine_health.get("state") == "online" and not ping.get("available") else None),
                     "generated_at": datetime.now(timezone.utc).isoformat()})
    return {"items": rows, "note": "ICMP endpoint reachability is not the same as end-to-end tunnel latency. Unavailable is not zero."}


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
    return {"version": "4.0.2", "tunnels": tunnels, "projects": projects, "traffic_total": traffic_total, "tunnel_count": len(tunnels),
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
    """Remove an explicitly confirmed tunnel instance using its engine-specific lifecycle."""
    _auth(request)
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required.")
    if not TUNNEL_UNIT.fullmatch(unit) or unit in {"backpack-monitor.service", "backpack-webui.service", "backpack-proxy.service", "paqet-relay.service", "paqet-auto-reset.service", "paqet-tunnel.service"}:
        raise HTTPException(status_code=400, detail="This unit is not an eligible tunnel instance.")
    # C-Tunnel uses shared systemd template units; instances have no standalone
    # file in /etc/systemd/system. Permit verified template instances while
    # keeping management/relay units and arbitrary package services protected.
    unit_path = Path("/etc/systemd/system") / unit
    if unit.startswith(("ctunnel@", "ctunnel-engine@")):
        template = "ctunnel@.service" if unit.startswith("ctunnel@") else "ctunnel-engine@.service"
        candidates = (Path("/etc/systemd/system") / template,
                      Path("/usr/lib/systemd/system") / template,
                      Path("/lib/systemd/system") / template)
        if not any(p.is_file() and not p.is_symlink() for p in candidates):
            raise HTTPException(status_code=409, detail="C-Tunnel template unit is not installed; refusing to remove an unknown instance.")
    elif not unit_path.is_file() or unit_path.is_symlink():
        raise HTTPException(status_code=409, detail="This tunnel has no verified custom unit file. Refresh detection or repair the service installation first.")
    ok, detail = _helper("delete-tunnel", unit)
    _audit("delete-tunnel", unit, "success" if ok else "failed", request)
    if not ok:
        raise HTTPException(status_code=409, detail=detail)
    return {"ok": True, "unit": unit, "detail": detail, "configuration_preserved": not unit.startswith("backpack-") , "removed_configuration": unit.startswith("backpack-")}


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



# Resource inspection is read-only; separately authenticated, allowlisted actions
# below require explicit confirmation and revalidate process identity or log paths.
def _decode_systemd_cgroup(value: str) -> str:
    # systemd escapes arbitrary bytes as \xNN in unit/cgroup names.
    return re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), value)


def _pid_service(pid: int) -> str:
    """Resolve the owning systemd service, including delegated/user cgroups and parents."""
    current = pid
    seen: set[int] = set()
    for _ in range(6):
        if current <= 1 or current in seen:
            break
        seen.add(current)
        try:
            raw = (Path('/proc') / str(current) / 'cgroup').read_text(encoding='utf-8', errors='ignore')
            for line in raw.splitlines():
                path = _decode_systemd_cgroup(line.rsplit(':', 1)[-1])
                # Prefer the innermost service unit; scopes are a fallback only.
                units = re.findall(r'([^/]+\.(?:service|scope))(?:/|$)', path)
                services = [u for u in units if u.endswith('.service')]
                if services:
                    return services[-1]
                if units:
                    return units[-1]
            status = (Path('/proc') / str(current) / 'status').read_text(encoding='utf-8', errors='ignore')
            parent = re.search(r'^PPid:\s*(\d+)', status, re.M)
            current = int(parent.group(1)) if parent else 0
        except (OSError, ValueError, PermissionError):
            break
    return 'unassigned / user process'


def _process_inventory() -> list[dict[str, Any]]:
    rows=[]
    try:
        for proc in Path("/proc").iterdir():
            if not proc.name.isdigit() or proc.name == "1": continue
            try:
                status=(proc/"status").read_text(encoding="utf-8", errors="ignore")
                vals=dict(re.findall(r"^(Name|State|Uid|VmRSS):\s*(.+)$",status,re.M))
                m=re.match(r"(\d+)\s+kB",vals.get("VmRSS",""))
                if not m: continue
                uid=int(vals.get("Uid","0").split()[0])
                # Include root-owned daemons in accounting (postgres, redis, etc.).
                # The UI/action endpoint still refuses stopping protected/root processes.
                pid=int(proc.name); name=vals.get("Name",proc.name)[:128]
                try: exe=os.readlink(proc/"exe")[:512]
                except OSError: exe="unavailable"
                try:
                    argv=(proc/"cmdline").read_bytes().split(b"\0",1)[0].decode("utf-8",errors="replace")[:512]
                except OSError: argv=""
                service=_pid_service(pid)
                rows.append({"pid":pid,"name":name,"user":str(uid),"state":vals.get("State","unknown")[:40],
                    "ram_bytes":int(m.group(1))*1024,"executable":exe,"command":argv,"start_ticks":_proc_start_ticks(proc),"service":service})
            except (OSError,ValueError,PermissionError): continue
    except OSError: pass
    return sorted(rows,key=lambda x:x["ram_bytes"],reverse=True)


@router.get("/analyzer/ram")
def analyze_ram(request: Request):
    _auth(request)
    processes=_process_inventory(); groups={}
    for proc in processes:
        key=proc["service"]
        group=groups.setdefault(key,{"service":key,"ram_bytes":0,"process_count":0,"processes":[]})
        group["ram_bytes"]+=proc["ram_bytes"]; group["process_count"]+=1
        if len(group["processes"])<8:
            group["processes"].append({k:proc[k] for k in ("pid","name","user","state","ram_bytes","executable","command","start_ticks")})
    items=sorted(groups.values(),key=lambda x:x["ram_bytes"],reverse=True)[:5]
    return {"items":items,"process_count":len(processes),"generated_at":datetime.now(timezone.utc).isoformat(),
            "note":"Processes are attributed using their own systemd cgroup and up to five parent processes. Unknown ownership remains explicitly unassigned; command and executable are shown when available."}


_DISK_ROOTS = (("BackPack",Path("/var/lib/backpack")),("BackPack config",Path("/etc/backpack")),
    ("C-Tunnel",Path("/var/lib/ctunnel")),("C-Tunnel config",Path("/etc/ctunnel")),
    ("idontMonitor",Path("/var/lib/idontmonitor")),("idontMonitor logs",MANAGED_LOG_DIR),
    ("BackPack logs",Path("/var/log/backpack")),("C-Tunnel logs",Path("/var/log/ctunnel")))

def _bounded_dir_size(root: Path, max_entries: int=5000, max_depth: int=5) -> tuple[int,int,bool]:
    total=0; count=0; truncated=False; stack=[(root,0)]
    while stack:
        current,depth=stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    count+=1
                    if count>max_entries: return total,count,True
                    try:
                        if entry.is_symlink(): continue
                        if entry.is_file(follow_symlinks=False): total+=entry.stat(follow_symlinks=False).st_size
                        elif entry.is_dir(follow_symlinks=False) and depth<max_depth: stack.append((Path(entry.path),depth+1))
                    except OSError: continue
        except OSError: continue
    return total,count,truncated


def _disk_top_entries(root: Path, limit: int = 4) -> list[dict[str, Any]]:
    """Return largest immediate children; directories are measured with bounded no-follow scans."""
    found: list[dict[str, Any]] = []
    try:
        with os.scandir(root) as entries:
            for entry in entries:
                try:
                    if entry.is_symlink():
                        continue
                    path = Path(entry.path)
                    if entry.is_file(follow_symlinks=False):
                        size = entry.stat(follow_symlinks=False).st_size
                        kind = "file"
                    elif entry.is_dir(follow_symlinks=False):
                        size, _, _ = _bounded_dir_size(path, max_entries=1200, max_depth=3)
                        kind = "directory"
                    else:
                        continue
                    found.append({"name": entry.name[:160], "path": str(path), "size_bytes": size, "kind": kind})
                except OSError:
                    continue
    except OSError:
        return []
    return sorted(found, key=lambda x: x["size_bytes"], reverse=True)[:limit]


@router.get("/analyzer/disk")
def analyze_disk(request: Request):
    _auth(request)
    items=[]
    for label,root in _DISK_ROOTS:
        try:
            if root.is_symlink() or not root.is_dir(): continue
            size,count,truncated=_bounded_dir_size(root)
            if count: items.append({"name":label,"path":str(root),"size_bytes":size,"entries_scanned":count,
                "top_entries":_disk_top_entries(root),"truncated":truncated,"category":"service-footprint","deletion_allowed":False})
        except OSError: continue
    items.sort(key=lambda x:x["size_bytes"],reverse=True)
    logs=_safe_managed_logs()
    return {"items":items[:5],"managed_logs":logs[:5],"managed_total_bytes":sum(x["size_bytes"] for x in logs),
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "note":"Bounded, no-symlink service footprint scan. Service directories are informational and cannot be bulk-deleted. Only separately listed managed logs have restricted cleanup policy. No files were deleted by scanning."}


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
