from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v400_version_and_watchdog_installation():
    assert (ROOT/'VERSION').read_text().strip()=='4.0.2'
    install=(ROOT/'install.sh').read_text()
    for unit in ('idontmonitor-collector.service','idontmonitor-collector.timer','idontmonitor-auto-reboot.service','idontmonitor-auto-reboot.timer'):
        assert unit in install
    watchdog=(ROOT/'scripts/idontmonitor-auto-reboot.py').read_text()
    assert 'THRESHOLD=90.0' in watchdog and 'HOLD=120' in watchdog and 'COOLDOWN=1800' in watchdog
    assert 'time.sleep(ALERT_DELAY)' in watchdog and 'systemctl\',\'reboot' in watchdog

def test_v400_collector_and_six_hour_report():
    collector=(ROOT/'scripts/idontmonitor-collector.py').read_text()
    bot=(ROOT/'scripts/idontmonitor-telegram-bot.py').read_text()
    for field in ('cpu_percent','memory_percent','disk_percent','memory_used_bytes','memory_total_bytes'):
        assert field in collector
    assert 'metrics-history.json' in bot and 'tunnel-events.json' in bot
    for label in ('بیشترین مصرف CPU','مصرف RAM','مصرف دیسک','تونل‌های فعال','تونل‌های غیرفعال','مشکلات تونل'):
        assert label in bot

def test_v400_dedicated_shield_page_and_api():
    html=(ROOT/'static/index.html').read_text(); js=(ROOT/'static/app.js').read_text(); main=(ROOT/'app/main.py').read_text(); css=(ROOT/'static/style.css').read_text()
    assert 'Anti-DDoS Shield' in html and 'id="page-security"' in html
    assert all(x in html for x in ('shieldRpm','shieldRps','shieldSources','shieldEvents'))
    assert "@app.get('/api/security/traffic')" in main
    assert 'auto_blocking' in main and 'loadShield()' in js
    assert '.shield-hero' in css and '.shield-kpis' in css

def test_six_hour_cpu_never_falls_back_to_load_average():
    bot=(ROOT/'scripts/idontmonitor-telegram-bot.py').read_text()
    report=bot.split('def _report_caption(states):',1)[1].split('\n\n\ndef main():',1)[0]
    assert "peak_cpu=max((float(x['cpu_percent'])" in report
    assert 'os.getloadavg' not in report
