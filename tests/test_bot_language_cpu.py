from pathlib import Path
p=Path(__file__).resolve().parents[1]
bot=(p/'scripts/idontmonitor-telegram-bot.py').read_text()
i18n=(p/'static/i18n.js').read_text()
css=(p/'static/style.css').read_text()
assert "LANG_FILE = CONFIG.parent / 'telegram-bot-languages.json'" in bot
assert "'callback_data': 'lang_fa'" in bot and "'callback_data': 'lang_en'" in bot
assert "'callback_data': 'language'" in bot
assert "def cpu_percent():" in bot and '⚙️ استفاده از CPU:' in bot and 'CPU usage:' in bot
for phrase in ('Sign in to continue','VPS Control Center','Change VPS password'):
    assert phrase in i18n
assert 'env(safe-area-inset-top)' in css and 'prefers-reduced-motion:reduce' in css
print('Per-admin language selection, in-bot language switch, CPU utilization, Persian login/VPS fallback and iOS layout checks passed.')
