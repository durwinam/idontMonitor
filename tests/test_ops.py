from pathlib import Path
import ast
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def test_operations_module_compiles_and_routes_are_present():
    ast.parse((ROOT / "app/ops.py").read_text())
    source = (ROOT / "app/ops.py").read_text()
    for route in ("/summary", "/tunnels", "/tunnels/history", "/tunnels/restart-all", "/services", "/audit", "/diagnostics", "/maintenance", "/alerts", "/backup", "/restore", "/terminal/{command_id}"):
        assert route in source
    assert "arbitrary_shell" in source


def test_tunnel_unit_patterns_match_supported_templates_only():
    source = (ROOT / "app/ops.py").read_text()
    match = re.search(r'TUNNEL_UNIT = re\.compile\(r"([^"]+)"\)', source)
    assert match
    pattern = re.compile(match.group(1))
    for unit in ("ctunnel@edge.service", "ctunnel-engine@edge.service", "backpack-de-frankfurt.service", "paqet.service", "paqet-entry-1.service"):
        assert pattern.fullmatch(unit), unit
    for unit in ("idontmonitor.service", "nginx.service", "ssh.service"):
        assert not pattern.fullmatch(unit), unit
    # These units match the broad name family but are explicitly excluded from tunnel detection.
    assert '"backpack-webui.service"' in source
    assert '"backpack-monitor.service"' in source
    assert '"paqet-relay.service"' in source


def test_root_helper_has_no_shell_eval_and_narrow_actions():
    helper = (ROOT / "scripts/idontmonitor-ops").read_text()
    assert "eval " not in helper
    assert "systemctl \"$action\" \"$unit\"" in helper
    assert "unsupported operation" in helper
    assert "backpack-webui.service" in helper


def test_log_rotation_is_bounded_and_safari_motion_fallback_exists():
    main = (ROOT / "app/main.py").read_text()
    css = (ROOT / "static/style.css").read_text()
    assert "maxBytes=100 * 1024 * 1024" in main
    assert "backupCount=3" in main
    assert "prefers-reduced-motion:reduce" in css
    assert "@supports not (backdrop-filter:blur(1px))" in css


def test_locale_files_are_valid_and_operations_page_exists():
    messages = json.loads((ROOT / "locales/fa/messages.json").read_text())
    assert "Tunnel Manager" in messages
    html = (ROOT / "static/index.html").read_text()
    assert 'id="page-operations"' in html
    assert 'id="restartAllTunnels"' in html


def test_remote_installer_bootstrap_handles_empty_bash_source():
    installer = (ROOT / "install.sh").read_text()
    assert 'SCRIPT_SOURCE="${BASH_SOURCE[0]-}"' in installer
    assert 'archive/refs/heads/main.tar.gz' in installer
    assert 'dirname "$0"' not in installer


def test_tunnel_delete_is_guarded_and_heuristic_traffic_mapping_removed():
    source = (ROOT / "app/ops.py").read_text()
    helper = (ROOT / "scripts/idontmonitor-ops").read_text()
    assert '@router.delete("/tunnels/{unit}")' in source
    assert 'class DeleteTunnelRequest' in source
    assert 'No engine-native snapshot, enabled systemd accounting, or exact engine-derived interface was found.' in source
    assert 'backpack-native-metrics' in source
    assert 'ct-' in source
    assert 'any(name.startswith(prefix) for prefix in ("ct", "paqet", "bp"))' not in source
    assert 'delete-tunnel)' in helper
    assert 'fully removed' in helper
    assert 'CleanupPckGuards' not in helper  # helper performs the narrowly scoped tagged-rule cleanup


def test_backpack_instance_config_and_native_transport_are_supported():
    source = (ROOT / "app/ops.py").read_text()
    assert "backpack-([A-Za-z0-9_.-]+)\\.service" in source
    assert 'transport=str(data.get("transport") or "").strip()' in source
    assert 'f"/etc/backpack/{m.group(1)}.toml"' in source
    assert 'Per-instance BackPack snapshot read from the exact config path.' in source
    assert 'REMOTE_IP' in source and '/etc/ctunnel/state.json' in source
    assert 'systemd cgroup' in source and '_bounded_dir_size' in source


def test_ctunnel_template_instances_are_disabled_without_deleting_shared_template():
    helper = (ROOT / "scripts/idontmonitor-ops").read_text()
    assert 'ctunnel@*.service|ctunnel-engine@*.service)' in helper
    assert 'systemctl stop "$unit" || { echo "C-Tunnel teardown failed;' in helper
    assert 'systemctl disable "$unit"' in helper
    assert 'shared template and tunnel configuration/state were preserved.' in helper
    assert 'systemctl stop "$unit" || true' not in helper


def test_active_managed_log_is_reopened_after_clear(tmp_path, monkeypatch):
    import logging
    from logging.handlers import RotatingFileHandler
    from types import SimpleNamespace
    import app.ops as ops

    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    active = log_dir / "idontmonitor.log"
    backup = log_dir / "idontmonitor.log.1"
    active.write_text("old active log\n")
    backup.write_text("old rotated log\n")
    handler = RotatingFileHandler(active, maxBytes=1024, backupCount=3, encoding="utf-8")
    logger = logging.getLogger("idontmonitor")
    logger.addHandler(handler)
    monkeypatch.setattr(ops, "MANAGED_LOG_DIR", log_dir)
    monkeypatch.setattr(ops, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(ops, "AUDIT_PATH", tmp_path / "state" / "audit.json")
    request = SimpleNamespace(session={"authenticated": True}, client=SimpleNamespace(host="127.0.0.1"))
    try:
        result = ops.analyzer_delete_logs({"confirm": True, "names": ["idontmonitor.log", "idontmonitor.log.1"]}, request)
        assert result["ok"] is True
        assert not backup.exists()
        assert active.is_file()
        logger.info("new log after clear")
        handler.flush()
        assert "new log after clear" in active.read_text()
    finally:
        logger.removeHandler(handler)
        handler.close()


def test_updater_reinstalls_restricted_helper_and_sudoers():
    updater = (ROOT / "scripts/idontmonitor-update").read_text()
    installer = (ROOT / "install.sh").read_text()
    assert "scripts/idontmonitor-ops" in updater
    assert "visudo" in updater and "/etc/sudoers.d/idontmonitor-ops" in updater
    assert "install -o root -g root -m 0750" in installer
    assert "/usr/local/sbin/idontmonitor-ops" in installer


def test_tunnel_delete_supports_shared_ctunnel_templates():
    source = (ROOT / "app/ops.py").read_text()
    assert "C-Tunnel uses shared systemd template units" in source
    assert "ctunnel-engine@.service" in source
    assert "ctunnel@.service" in source


def test_restricted_helper_is_not_checked_with_unprivileged_os_access():
    source = (ROOT / "app/ops.py").read_text()
    start = source.index("def _helper(")
    end = source.index("\n\nclass RestartRequest", start)
    helper = source[start:end]
    assert "HELPER.lstat()" in helper
    assert "st.st_uid != 0" in helper
    assert "st.st_mode & 0o100" in helper
    assert "os.access(HELPER, os.X_OK)" not in helper
    assert 'args = ["sudo", "-n", str(HELPER), action]' in helper


def test_systemd_service_allows_only_the_narrow_sudo_setuid_transition():
    service = (ROOT / "systemd/idontmonitor.service").read_text()
    assert "NoNewPrivileges=false" in service
    assert "RestrictSUIDSGID=true" not in service
    # An empty bounding set prevents sudo from setting root gid/uid and breaks
    # sudoers_audit before the allowlisted helper can even start.
    assert "CapabilityBoundingSet=" not in service
    assert "AmbientCapabilities=" in service
    assert "root-owned allowlisted helper" in service


def test_backpack_tunnel_delete_follows_native_per_tunnel_lifecycle():
    helper = (ROOT / "scripts/idontmonitor-ops").read_text()
    assert 'backpack-*.service)' in helper
    assert 'config_file="/etc/backpack/$name.toml"' in helper
    assert 'metrics_file="/etc/backpack/$name.metrics.json"' in helper
    assert 'quota_file="/etc/backpack/$name.quota.json"' in helper
    assert 'backpack-restart-$name.timer' in helper
    assert 'systemctl stop "$unit"' in helper
    assert 'systemctl disable "$unit"' in helper
    assert 'systemctl disable --now "$unit"' not in helper
    assert 'rm -- "$config_file"' in helper
    assert 'rm -- "$unit_file"' in helper
    assert 'BackPack tunnel fully removed:' in helper


def test_sudo_helper_write_paths_are_explicitly_scoped():
    service = (ROOT / "systemd/idontmonitor.service").read_text()
    line = next(x for x in service.splitlines() if x.startswith("ReadWritePaths="))
    assert "/etc/systemd/system" in line
    assert "/etc/backpack" in line


def test_backpack_delete_cleans_exact_native_state_and_reports_truthfully():
    helper = (ROOT / "scripts/idontmonitor-ops").read_text()
    api = (ROOT / "app/ops.py").read_text()
    ui = (ROOT / "static/operations.js").read_text()
    for token in ("meta.json", "node-pairs.json", "retired-traffic.json", "backpack-pck-v1:", "--comment", "flock", "tomllib"):
        assert token in helper
    assert '"configuration_preserved": not unit.startswith("backpack-")' in api
    assert "This removes only this BackPack tunnel" in ui
    assert "RuntimeDirectory=backpack-pck" in (ROOT / "systemd/idontmonitor.service").read_text()


def test_backpack_helper_never_uses_recursive_or_wildcard_deletion():
    helper = (ROOT / "scripts/idontmonitor-ops").read_text()
    branch = helper.split("backpack-*.service)", 1)[1].split("      *)", 1)[0]
    assert "rm -rf" not in branch
    assert "find " not in branch
    assert 'rm -- "$config_file"' in branch
    assert 'rm -- "$unit_file"' in branch
