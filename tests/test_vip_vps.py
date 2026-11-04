from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
html=(ROOT/'static/index.html').read_text()
js=(ROOT/'static/app.js').read_text()
css=(ROOT/'static/style.css').read_text()
main=(ROOT/'app/main.py').read_text()
helper=(ROOT/'scripts/idontmonitor-ops').read_text()
assert (ROOT/'VERSION').read_text().strip() == '4.0.2'
assert 'data-page="vps"' in html and 'id="page-vps"' in html
assert 'Midnight Emerald Glass' in js
assert 'NEW</span>' not in html and 'new-badge' not in html
assert 'data-theme-vip="true"' in css and 'prefers-reduced-motion:reduce' in css
assert 'vpsModalBackdrop' in html and 'vpsPasswordOpen' in js
assert "'vps'" in js and 'loadVpsSummary' in js
assert "@app.post('/api/vps/password')" in main
assert 'change-root-password)' in helper
assert "@app.post('/api/vps/reboot')" in main
assert 'reboot-vps)' in helper
assert 'arbitrary shell' not in helper.lower() or 'never evaluate input as shell code' in helper.lower()
print('VIP theme, VPS navigation, modal, reboot endpoint and allowlisted helper checks passed.')

assert 'vpsLiveSummary' in html and 'vpsSummaryRefresh' in html
assert "@app.get('/api/vps/summary')" in main
assert "@app.post('/api/vps/password')" in main
print('Live VPS summary and password API checks passed.')

assert "@app.get('/api/vps/password-challenge')" in main
assert "VPS_CAPTCHA_CHALLENGES.pop(captcha_token, None)" in main
assert '"expires_at": now + 180' in main
assert "captcha_token" in js and "refreshVpsCaptcha" in js
assert "X-Content-Type-Options" in main and "Content-Security-Policy" in main
print('v2.3.4 root-password CAPTCHA, one-time challenge and HTTP security-header checks passed.')
