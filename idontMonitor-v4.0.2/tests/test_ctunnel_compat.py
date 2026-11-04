from app import ops


def test_ctunnel_ecmp_lane_counters_are_summed(monkeypatch):
    monkeypatch.setattr(ops, "_systemd_unit_traffic", lambda unit: None)
    counters = {
        "ct-edge": {"rx_bytes": 100, "tx_bytes": 200},
        "ct-edge.1": {"rx_bytes": 10, "tx_bytes": 20},
        "ct-edge.7": {"rx_bytes": 7, "tx_bytes": 14},
        "ct-other": {"rx_bytes": 9999, "tx_bytes": 9999},
        "ct-edge.8": {"rx_bytes": 8888, "tx_bytes": 8888},
    }
    result = ops._traffic_for_unit("ctunnel@edge.service", counters)
    assert result["available"] is True
    assert result["rx_bytes"] == 117
    assert result["tx_bytes"] == 234
    assert result["interfaces"] == ["ct-edge", "ct-edge.1", "ct-edge.7"]
    assert result["source"] == "engine-derived-exact-interface"


def test_ctunnel_engine_without_lanes_keeps_exact_base_interface(monkeypatch):
    monkeypatch.setattr(ops, "_systemd_unit_traffic", lambda unit: None)
    result = ops._traffic_for_unit(
        "ctunnel-engine@edge.service",
        {"ct-edge": {"rx_bytes": 12, "tx_bytes": 34}, "ct-edge-extra": {"rx_bytes": 900, "tx_bytes": 900}},
    )
    assert result["available"] is True
    assert result["interface"] == "ct-edge"
    assert result["rx_bytes"] == 12
    assert result["tx_bytes"] == 34


def test_ctunnel_without_exact_interface_does_not_guess(monkeypatch):
    monkeypatch.setattr(ops, "_systemd_unit_traffic", lambda unit: None)
    result = ops._traffic_for_unit("ctunnel@edge.service", {"ct-edge-extra": {"rx_bytes": 1, "tx_bytes": 2}})
    assert result["available"] is False
    assert result["rx_bytes"] is None
