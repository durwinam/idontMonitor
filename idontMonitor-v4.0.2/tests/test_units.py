from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/'static/app.js').read_text()
html=(ROOT/'static/index.html').read_text()
main=(ROOT/'app/main.py').read_text()
installer=(ROOT/'install.sh').read_text()
assert 'const MB=1024**2,GB=1024**3,TB=1024**4' in js
assert 'tracked_total_bytes' in main
assert "@app.get('/api/history')" in main
assert 'fcntl.flock' in main
assert 'HISTORY_MAX_SAMPLES' in main
for page in ('overview','resources','network','security','settings'):
    assert f'id="page-{page}"' in html
for elem in ('totalRx','totalTx','totalTracked','trafficUsedBig','remaining'):
    assert f'id="{elem}"' in html
for theme in ('Nebula Purple','Cyber Mint','Crimson Pulse','Arctic Blue','Emerald Matrix','Solar Amber','Ultra Dark'):
    assert theme in html
for route in ("/api/security/logins", "/api/account/username", "/api/account/password", "/api/account/port"):
    assert route in main
assert 'id="loginAudit"' in html
assert '/usr/local/sbin/idontmonitor-set-port' in installer
assert '1024 GB' in html and '10240 GB' in html
print('Units, navigation, themes, login audit, account controls and port helper checks passed.')

assert 'rx_bytes_per_second' in main
assert 'tx_bytes_per_second' in main
assert 'bandwidth-live' in html
assert 'bootScreen' in html
assert (ROOT/'static/idontmonitor-logo.png').exists()
