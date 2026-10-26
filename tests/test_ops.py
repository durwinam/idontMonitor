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
    assert 'configuration/data were preserved' in helper


def test_backpack_instance_config_and_native_transport_are_supported():
    source = (ROOT / "app/ops.py").read_text()
    assert "backpack-client-([A-Za-z0-9_.-]+)\\.service" in source
    assert 'transport=str(data.get("transport") or "").strip()' in source
    assert 'client-{m.group(1)}.toml' in source
    assert 'Per-instance BackPack snapshot read from the exact config path.' in source
