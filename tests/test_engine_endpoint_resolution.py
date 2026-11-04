from app import ops


def test_backpack_uses_fresh_native_connected_peer(monkeypatch):
    monkeypatch.setattr(ops, "_backpack_snapshot_for_unit", lambda unit: {
        "peer": "198.51.100.8:443", "connected": True, "snapshot_fresh": True,
        "snapshot_age_seconds": 3.0,
    })
    monkeypatch.setattr(ops, "_clean_endpoint_host", lambda value: value.split(":")[0] if value else None)
    result = ops._endpoint_info_for_unit("backpack-client-3527.service")
    assert result["host"] == "198.51.100.8"
    assert result["source"] == "backpack-native-peer"
    assert result["mode"] == "connected-peer"


def test_backpack_fresh_disconnected_snapshot_does_not_fallback(monkeypatch):
    monkeypatch.setattr(ops, "_backpack_snapshot_for_unit", lambda unit: {
        "peer": "", "connected": False, "snapshot_fresh": True,
        "snapshot_age_seconds": 2.0,
    })
    result = ops._endpoint_info_for_unit("backpack-client-3527.service")
    assert result["host"] is None
    assert result["mode"] == "disconnected"


def test_ctunnel_reverse_uses_inner_peer_and_tunnel_interface(monkeypatch):
    monkeypatch.setattr(ops, "_ctunnel_config", lambda name: {
        "name": name, "reverse": True, "remote_ip": "0.0.0.0",
        "tun_remote4": "10.77.3.1",
    })
    monkeypatch.setattr(ops, "_clean_endpoint_host", lambda value: value if value else None)
    result = ops._endpoint_info_for_unit("ctunnel@kh-443.service")
    assert result["host"] == "10.77.3.1"
    assert result["interface"] == "ct-kh-443"
    assert result["mode"] == "tunnel-peer"


def test_ctunnel_normal_uses_underlay_remote_ip(monkeypatch):
    monkeypatch.setattr(ops, "_ctunnel_config", lambda name: {
        "name": name, "reverse": False, "remote_ip": "203.0.113.9",
        "tun_remote4": "10.77.3.1",
    })
    monkeypatch.setattr(ops, "_clean_endpoint_host", lambda value: value if value else None)
    result = ops._endpoint_info_for_unit("ctunnel@kh-443.service")
    assert result["host"] == "203.0.113.9"
    assert result["interface"] is None
    assert result["mode"] == "underlay-endpoint"


def test_ctunnel_reverse_without_tunnel_peer_is_unavailable(monkeypatch):
    monkeypatch.setattr(ops, "_ctunnel_config", lambda name: {
        "name": name, "reverse": True, "remote_ip": "0.0.0.0",
        "tun_remote4": "",
    })
    monkeypatch.setattr(ops, "_clean_endpoint_host", lambda value: None)
    result = ops._endpoint_info_for_unit("ctunnel@kh-443.service")
    assert result["host"] is None
    assert result["mode"] == "unavailable"


def test_systemd_cgroup_escaped_name_decodes_to_real_service():
    assert ops._decode_systemd_cgroup(r"/system.slice/backpack-client\x2d3527.service") == "/system.slice/backpack-client-3527.service"


def test_backpack_snapshot_with_missing_connected_field_is_unknown_not_offline(tmp_path, monkeypatch):
    import json
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    (tmp_path / "client.metrics.json").write_text(json.dumps({"name":"client", "taken":now, "peer":"198.51.100.4:443"}))
    original_path = ops.Path
    monkeypatch.setattr(ops, "Path", lambda value: tmp_path if str(value) == "/etc/backpack" else original_path(value))
    result = ops._backpack_engine_health("backpack-client.service")
    assert result["state"] == "unknown"
    assert result["connected"] is None


def test_disk_top_entries_returns_largest_immediate_files_and_dirs(tmp_path):
    (tmp_path / "small.log").write_bytes(b"x" * 10)
    large = tmp_path / "large-dir"
    large.mkdir()
    (large / "data.bin").write_bytes(b"x" * 2048)
    rows = ops._disk_top_entries(tmp_path)
    assert rows[0]["name"] == "large-dir"
    assert rows[0]["size_bytes"] == 2048
