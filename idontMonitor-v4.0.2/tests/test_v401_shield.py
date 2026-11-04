from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v401_persistent_24h_telemetry_and_manual_toggle():
    main=(ROOT/'app/main.py').read_text(); html=(ROOT/'static/index.html').read_text(); js=(ROOT/'static/app.js').read_text()
    assert (ROOT/'VERSION').read_text().strip()=='4.0.2'
    assert 'security-traffic.sqlite3' in main
    assert 'CREATE TABLE IF NOT EXISTS request_minutes' in main
    assert "@app.post('/api/security/protection')" in main
    assert 'protection_enabled": False' in main
    assert 'history_24h' in main and 'requests_24h' in main
    assert 'shieldProtectionToggle' in html and 'type="checkbox"' in html
    assert 'shieldTrafficChart' in html and 'drawShieldChart' in js
    assert 'Last 24 hours' in html

def test_v401_mitigation_is_off_by_default_and_explicitly_gated():
    main=(ROOT/'app/main.py').read_text()
    assert 'if cfg.get("protection_enabled") and' in main
    assert 'mitigation_threshold_10s' in main
    assert 'Temporarily rate-limited' in main

def test_backpack_delete_preserves_enablement_on_firewall_inspection_failure():
    helper=(ROOT/'scripts/idontmonitor-ops').read_text()
    assert 'systemctl stop "$unit"' in helper
    assert 'systemctl disable --now "$unit"' not in helper
    assert 'systemctl disable "$unit"' in helper
    assert 'cannot inspect PCK firewall rules (' in helper
    assert 'unit/configuration preserved' in helper
    assert helper.index('\nPYBP\n') < helper.index('systemctl disable "$unit"', helper.index('backpack-*.service)'))

def test_shield_mobile_layout_and_accessible_switch():
    css=(ROOT/'static/style.css').read_text(); html=(ROOT/'static/index.html').read_text()
    assert '@media(max-width:420px)' in css
    assert '.shield-switch input:focus-visible' in css
    assert 'aria-label="Enable Anti-DDoS protection"' in html
