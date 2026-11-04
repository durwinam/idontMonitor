from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/'static/index.html').read_text()
js=(ROOT/'static/telegram-bot.js').read_text()
main=(ROOT/'app/main.py').read_text()
worker=(ROOT/'scripts/idontmonitor-telegram-bot.py').read_text()
unit=(ROOT/'systemd/idontmonitor-telegram-bot.service').read_text()
installer=(ROOT/'install.sh').read_text()
assert 'data-page="telegram"' in html and 'id="page-telegram"' in html
assert 'telegramAdmin1' in html and 'telegramAdmin2' in html and 'telegramAdmin3' in html
assert "@app.get('/api/telegram-bot')" in main and "@app.post('/api/telegram-bot')" in main
assert "getMe" in main and "os.chmod(tmp,0o600)" in main
assert 'You do not have access to this bot.' in worker
assert 'if uid not in admins' in worker and 'callback_data' in worker
assert all(x in worker for x in ['resources', 'network', 'tunnels', 'status_text', 'resources_text', 'network_text'])
assert 'inline_keyboard' in worker and '🧠 منابع سیستم' in worker
assert 'User=idontmonitor' in unit and 'ProtectSystem=strict' in unit
assert 'idontmonitor-telegram-bot.service' in installer
assert "'telegram'" in (ROOT/'static/app.js').read_text()
print('Telegram settings page, token verification, admin allowlist, worker unit and installer checks passed.')

assert 'editMessageText' in worker and 'callback_data' in worker
assert 'password_confirm' in worker and 'reboot_confirm' in worker
assert 'delete_message(token, chat, msg_id)' in worker and 'change_root_password' in worker
assert '↩️ بازگشت' in worker and '✖️ لغو' in worker
print('Inline edit, back/cancel, password and reboot workflow checks passed.')

assert "def custom_emoji_entities(text):" in worker
assert "IDM_TELEGRAM_CUSTOM_EMOJI_IDS" in worker
assert "custom_emoji_id" in worker and "_entity_rejected" in worker
print('Telegram custom emoji entities and explicit-rejection Unicode fallback checks passed.')

assert "5979014214595910994" in worker  # CPU custom emoji
assert "5980861776382663883" in worker  # RAM custom emoji
assert "5978658578418900414" in worker  # Disk custom emoji


def test_inline_buttons_get_bot_api_94_styles_and_preserve_layout():
    import runpy
    ns=runpy.run_path(str(ROOT/'scripts/idontmonitor-telegram-bot.py'))
    styled=ns['styled_keyboard'](ns['MENU_FA'])['inline_keyboard']
    assert [len(row) for row in styled] == [1,2,1,2,2,1]
    assert styled[0][0]['style']=='danger'
    assert styled[-1][0]['callback_data']=='panel_link'
    assert styled[-1][0]['style']=='danger'
    assert styled[1][0]['style']=='primary' and styled[1][1]['style']=='success'
    assert styled[3][1]['style']=='success'
    assert ns['styled_keyboard'](ns['LANGUAGES'])['inline_keyboard'][0][0]['style']=='primary'
    assert ns['styled_keyboard'](ns['LANGUAGES'])['inline_keyboard'][0][1]['style']=='success'

def test_premium_emoji_ids_and_resource_text_markers():
    import runpy
    ns=runpy.run_path(str(ROOT/'scripts/idontmonitor-telegram-bot.py'))
    ids=ns['PREMIUM_EMOJI_IDS']
    assert ids['⚙️']=='5979014214595910994'
    assert ids['🧠']=='5980861776382663883'
    assert ids['💾']=='5978658578418900414'
    assert ids['🔄']=='6019623375192724683'
    assert ids['❌']=='4958526153955476488'
    keyboard=ns['styled_keyboard'](ns['MENU_EN'])
    assert all('style' in b for row in keyboard['inline_keyboard'] for b in row)
    assert '🧠 RAM:' in ns['response_for']('resources','en')
    assert '💾 Disk:' in ns['response_for']('resources','en')
    assert '⚙️ CPU usage:' in ns['response_for']('resources','en')

def test_send_serializes_colored_keyboard_and_custom_emoji_entities():
    import json, runpy
    ns=runpy.run_path(str(ROOT/'scripts/idontmonitor-telegram-bot.py'))
    calls=[]
    ns['send'].__globals__['api']=lambda token, method, data, timeout=35: calls.append((method,dict(data))) or {'ok':True}
    ns['send']('token','123','⚙️ CPU 🧠 RAM 💾 Disk',ns['MENU_FA'])
    assert len(calls)==1
    method,data=calls[0]
    assert method=='sendMessage'
    markup=json.loads(data['reply_markup'])['inline_keyboard']
    assert [len(row) for row in markup]==[1,2,1,2,2,1]
    assert all('style' in button for row in markup for button in row)
    entities=json.loads(data['entities'])
    assert [entity['custom_emoji_id'] for entity in entities]==[
        '5979014214595910994','5980861776382663883','5978658578418900414']
    assert [entity['type'] for entity in entities]==['custom_emoji']*3

def test_custom_emoji_unicode_fallback_when_bot_lacks_premium():
    import json, runpy
    ns = runpy.run_path(str(ROOT/'scripts/idontmonitor-telegram-bot.py'))
    ns['_send_with_optional_entities'].__globals__['CUSTOM_EMOJI_CAPABILITY'] = None
    calls = []
    def fake_api(token, method, data, timeout=35):
        calls.append(dict(data))
        if len(calls) == 1:
            # Simulate Bot API / proxy returning a JSON error without HTTPError.
            return {'ok': False, 'description': "Bad Request: custom emoji entities are not allowed for non-premium users"}
        return {'ok': True, 'result': {'message_id': 99}}
    ns['_send_with_optional_entities'].__globals__['api'] = fake_api
    text = '⚙️ CPU 🧠 RAM 💾 Disk'
    result = ns['_send_with_optional_entities']('token', 'sendMessage', {'chat_id':'1','text':text}, text)
    assert result['ok'] is True
    assert len(calls) == 2
    assert 'entities' in calls[0]
    assert 'entities' not in calls[1]
    assert calls[1]['text'] == text  # same Unicode emoji, not removed
    assert ns['_send_with_optional_entities'].__globals__['CUSTOM_EMOJI_CAPABILITY'] is False


def test_custom_emoji_invalid_id_falls_back_but_does_not_disable_future_custom_emoji():
    import runpy
    ns = runpy.run_path(str(ROOT/'scripts/idontmonitor-telegram-bot.py'))
    ns['_send_with_optional_entities'].__globals__['CUSTOM_EMOJI_CAPABILITY'] = None
    calls = []
    def fake_api(token, method, data, timeout=35):
        calls.append(dict(data))
        if len(calls) == 1:
            return {'ok': False, 'description': 'Bad Request: custom emoji entity is invalid'}
        return {'ok': True}
    ns['_send_with_optional_entities'].__globals__['api'] = fake_api
    text = '⚙️ CPU'
    assert ns['_send_with_optional_entities']('token', 'sendMessage', {'chat_id':'1','text':text}, text)['ok']
    assert len(calls) == 2 and 'entities' not in calls[1]
    assert ns['_send_with_optional_entities'].__globals__['CUSTOM_EMOJI_CAPABILITY'] is None

def test_custom_emoji_http_error_body_is_read_once_and_unicode_retry_works():
    import io, runpy, urllib.error
    ns = runpy.run_path(str(ROOT/'scripts/idontmonitor-telegram-bot.py'))
    g = ns['_send_with_optional_entities'].__globals__
    g['CUSTOM_EMOJI_CAPABILITY'] = None
    calls = []
    def fake_api(token, method, data, timeout=35):
        calls.append(dict(data))
        if len(calls) == 1:
            raise urllib.error.HTTPError(
                'https://api.telegram.org/botTOKEN/sendMessage', 400, 'Bad Request', {},
                io.BytesIO(b'{"ok":false,"description":"Custom emoji entities are not allowed for non-premium users"}')
            )
        return {'ok': True}
    g['api'] = fake_api
    text = '⚙️ CPU'
    assert ns['_send_with_optional_entities']('token', 'sendMessage', {'chat_id':'1','text':text}, text)['ok']
    assert len(calls) == 2 and 'entities' not in calls[1]
    assert calls[1]['text'] == text
    assert g['CUSTOM_EMOJI_CAPABILITY'] is False


def test_all_supplied_premium_emoji_ids_are_registered_and_used_in_status_text():
    import runpy
    ns = runpy.run_path(str(ROOT/'scripts/idontmonitor-telegram-bot.py'))
    ids = ns['PREMIUM_EMOJI_IDS']
    expected = {
        '👋':'5454390891466726015', '⚡️':'5085022089103016925',
        '⚙️':'5979014214595910994', '🧠':'5980861776382663883',
        '💾':'5978658578418900414', '🔒':'5116516255355897110',
        '✅':'6016907976609107800', '🔴':'6001066256025785838',
        '🟡':'6001542748287539188', '🔵':'6001233652376146830',
        '👤':'5974038293120027938', '🌐':'5974475701179387553',
        '📊':'5118775128980718591', '❗️':'5976801477509778431',
        '🔄':'6019623375192724683', '❌':'4958526153955476488',
        '⏰':'5809742105987259196',
    }
    for emoji, emoji_id in expected.items():
        assert ids[emoji] == emoji_id
    text = ns['status_text']() + ns['resources_text']() + ns['network_text']() + ns['response_for']('help','en')
    entities = ns['custom_emoji_entities'](text)
    used_ids = {entity['custom_emoji_id'] for entity in entities}
    assert {'5085022089103016925','5979014214595910994','5980861776382663883',
            '5978658578418900414','6016907976609107800','6001233652376146830',
            '5118775128980718591','5976801477509778431','5809742105987259196'} <= used_ids


def test_every_inline_button_gets_custom_icon_and_keeps_style():
    import runpy
    ns = runpy.run_path(str(ROOT/'scripts/idontmonitor-telegram-bot.py'))
    for keyboard in (ns['MENU_FA'], ns['MENU_EN'], ns['LANGUAGES'], ns['BACK'],
                     ns['CONFIRM_REBOOT'], ns['CONFIRM_PASSWORD']):
        rich = ns['styled_keyboard'](keyboard, include_custom_emoji=True)
        plain = ns['styled_keyboard'](keyboard, include_custom_emoji=False)
        rich_buttons = [b for row in rich['inline_keyboard'] for b in row]
        plain_buttons = [b for row in plain['inline_keyboard'] for b in row]
        assert all('style' in b for b in rich_buttons)
        assert all('icon_custom_emoji_id' in b for b in rich_buttons)
        assert all('icon_custom_emoji_id' not in b for b in plain_buttons)
        assert len(rich_buttons) == len(plain_buttons)
    assert [len(row) for row in ns['styled_keyboard'](ns['MENU_FA'])['inline_keyboard']] == [1,2,1,2,2,1]


def test_button_custom_emoji_rejection_retries_original_unicode_keyboard():
    import json, runpy
    ns = runpy.run_path(str(ROOT/'scripts/idontmonitor-telegram-bot.py'))
    g = ns['_send_with_optional_entities'].__globals__
    g['CUSTOM_EMOJI_CAPABILITY'] = None
    calls = []
    def fake_api(token, method, data, timeout=35):
        calls.append(dict(data))
        if len(calls) == 1:
            return {'ok': False, 'description': "Bad Request: custom emoji icons are not allowed for non-premium users"}
        return {'ok': True}
    g['api'] = fake_api
    ns['send']('token','123','👋 idontMonitor',ns['MENU_FA'])
    assert len(calls) == 2
    rich = json.loads(calls[0]['reply_markup'])['inline_keyboard']
    fallback = json.loads(calls[1]['reply_markup'])['inline_keyboard']
    assert all('icon_custom_emoji_id' in b for row in rich for b in row)
    assert all('icon_custom_emoji_id' not in b for row in fallback for b in row)
    assert fallback[0][0]['text'].startswith('🖥')
    assert calls[1]['text'] == '👋 idontMonitor'
    assert g['CUSTOM_EMOJI_CAPABILITY'] is False


def test_button_icon_rejection_does_not_require_message_entities():
    import json, runpy
    ns = runpy.run_path(str(ROOT/'scripts/idontmonitor-telegram-bot.py'))
    g = ns['_send_with_optional_entities'].__globals__
    g['CUSTOM_EMOJI_CAPABILITY'] = None
    calls = []
    def fake_api(token, method, data, timeout=35):
        calls.append(dict(data))
        if len(calls) == 1:
            return {'ok': False, 'description': "Bad Request: can't use custom emoji icons without Telegram Premium"}
        return {'ok': True}
    g['api'] = fake_api
    plain = {'chat_id':'1','text':'No mapped emoji in body',
             'reply_markup':json.dumps(ns['styled_keyboard'](ns['MENU_EN']))}
    fallback = {'chat_id':'1','text':'No mapped emoji in body',
                'reply_markup':json.dumps(ns['styled_keyboard'](ns['MENU_EN'], include_custom_emoji=False))}
    result = ns['_send_with_optional_entities']('token','sendMessage',plain,plain['text'],fallback)
    assert result['ok'] is True and len(calls) == 2
    assert 'icon_custom_emoji_id' in calls[0]['reply_markup']
    assert 'icon_custom_emoji_id' not in calls[1]['reply_markup']
    assert g['CUSTOM_EMOJI_CAPABILITY'] is False


def test_status_text_has_real_newlines_and_panel_url_is_configurable():
    import runpy, os
    ns=runpy.run_path(str(ROOT/'scripts/idontmonitor-telegram-bot.py'))
    text=ns['status_text']()
    assert '\\n' not in text
    assert '\n' in text
    old=os.environ.get('IDM_PANEL_URL')
    os.environ['IDM_PANEL_URL']='https://monitor.example.com:42624/'
    try:
        assert ns['panel_login_url']()=='https://monitor.example.com:42624'
        assert 'https://monitor.example.com:42624' in ns['response_for']('panel_link','en')
    finally:
        if old is None: os.environ.pop('IDM_PANEL_URL',None)
        else: os.environ['IDM_PANEL_URL']=old


def test_panel_url_uses_idontmonitor_install_metadata_not_sibling_ports(tmp_path):
    import os, runpy
    ns = runpy.run_path(str(ROOT/'scripts/idontmonitor-telegram-bot.py'))
    state = tmp_path/'install-mode'
    env = tmp_path/'environment'
    old = {k: os.environ.get(k) for k in ('IDM_PANEL_URL','IDM_INSTALL_MODE_FILE','IDM_ENV_FILE','IDM_PUBLIC_HOST','WEB_PUBLIC_PORT','IDM_WEB_PORT')}
    try:
        for k in ('IDM_PANEL_URL','IDM_PUBLIC_HOST','IDM_WEB_PORT'):
            os.environ.pop(k, None)
        os.environ['WEB_PUBLIC_PORT'] = '61032'  # another panel's port must be ignored
        os.environ['IDM_INSTALL_MODE_FILE'] = str(state)
        os.environ['IDM_ENV_FILE'] = str(env)
        state.write_text('MODE=https\nDOMAIN=monitor.example.com\nPUBLIC_IP=203.0.113.10\n')
        env.write_text('IDM_APP_PORT=28431\n')
        assert ns['panel_login_url']() == 'https://monitor.example.com'
        state.write_text('MODE=http\nPUBLIC_IP=203.0.113.10\nHTTP_PORT=28431\n')
        assert ns['panel_login_url']() == 'http://203.0.113.10:28431'
        state.write_text('MODE=unknown\n')
        assert ns['panel_login_url']() is None
    finally:
        for k, v in old.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v
