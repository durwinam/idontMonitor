#!/usr/bin/env python3
"""Admin-only Telegram companion for idontMonitor. No third-party Python dependencies."""
import json, os, time, re, urllib.parse, urllib.request, urllib.error, subprocess, shutil
from pathlib import Path

CONFIG = Path(os.environ.get('IDM_TELEGRAM_CONFIG', '/var/lib/idontmonitor/telegram-bot.json'))
OFFSET = 0
LANG_FILE = CONFIG.parent / 'telegram-bot-languages.json'
LANGUAGES = {'inline_keyboard': [[{'text': '🇮🇷 فارسی', 'callback_data': 'lang_fa'}, {'text': '🇬🇧 English', 'callback_data': 'lang_en'}]]}
# Keep the approved order; panel URL is the final single-button row.
MENU_FA = {'inline_keyboard': [
    [{'text': '🖥 وضعیت سرور', 'callback_data': 'status'}],
    [{'text': '🧠 منابع سیستم', 'callback_data': 'resources'}, {'text': '🌐 شبکه و ترافیک', 'callback_data': 'network'}],
    [{'text': '🔗 وضعیت تانل‌ها', 'callback_data': 'tunnels'}],
    [{'text': '🔐 تغییر رمز VPS', 'callback_data': 'password'}, {'text': '♻️ راه‌اندازی مجدد VPS', 'callback_data': 'reboot'}],
    [{'text': '🌐 تغییر زبان', 'callback_data': 'language'}, {'text': 'ℹ️ راهنما', 'callback_data': 'help'}],
    [{'text': '🔗 لینک ورود به پنل', 'callback_data': 'panel_link'}],
]}
MENU_EN = {'inline_keyboard': [
    [{'text': '🖥 Server status', 'callback_data': 'status'}],
    [{'text': '🧠 System resources', 'callback_data': 'resources'}, {'text': '🌐 Network & traffic', 'callback_data': 'network'}],
    [{'text': '🔗 Tunnel status', 'callback_data': 'tunnels'}],
    [{'text': '🔐 Change VPS password', 'callback_data': 'password'}, {'text': '♻️ Reboot VPS', 'callback_data': 'reboot'}],
    [{'text': '🌐 Change language', 'callback_data': 'language'}, {'text': 'ℹ️ Help', 'callback_data': 'help'}],
    [{'text': '🔗 Open panel link', 'callback_data': 'panel_link'}],
]}
def menu(lang): return MENU_FA if lang == 'fa' else MENU_EN


def _button_icon_for(button):
    """Pick a known user-supplied Premium emoji ID for each inline action."""
    action = str(button.get('callback_data', '')).lower()
    by_action = {
        'status': '📊', 'refresh': '📊',
        'resources': '🧠', 'network': '🌐', 'tunnels': '⚙️',
        'password': '🔒', 'password_confirm': '✅',
        'reboot': '🔄', 'reboot_confirm': '🔴',
        'language': '🌐', 'lang_fa': '🌐', 'lang_en': '🌐',
        'help': '❗️', 'menu': '🔄', 'cancel': '❌', 'panel_link': '🌐',
    }
    emoji = by_action.get(action)
    if emoji in PREMIUM_EMOJI_IDS:
        return emoji, PREMIUM_EMOJI_IDS[emoji]
    label = str(button.get('text', ''))
    for candidate in sorted(PREMIUM_EMOJI_IDS, key=len, reverse=True):
        if label.startswith(candidate):
            return candidate, PREMIUM_EMOJI_IDS[candidate]
    return None, None


_BUTTON_PREFIXES = (
    '🇮🇷', '🇬🇧', '🖥', '🔗', '🔐', '♻️', '↩️', '✖️', '✖',
    '⚠️', 'ℹ️', '👋', '⚡️', '⚙️', '🧠', '💾', '🔒', '✅',
    '🔴', '🟡', '🔵', '👤', '🌐', '📊', '❗️', '🔄', '❌', '⏰',
)


def styled_keyboard(keyboard, include_custom_emoji=True):
    """Apply consistent Telegram button colors and optional Premium icons.

    Paired rows: first/left button green, second/right button blue. Single-button
    rows are red. Unicode labels remain available in the non-Premium fallback.
    """
    if not isinstance(keyboard, dict) or not isinstance(keyboard.get('inline_keyboard'), list):
        return keyboard
    result = {'inline_keyboard': []}
    for row in keyboard['inline_keyboard']:
        row = row if isinstance(row, list) else []
        styled_row = []
        for index, button in enumerate(row):
            if not isinstance(button, dict):
                styled_row.append(button)
                continue
            item = dict(button)
            action = str(item.get('callback_data', '')).lower()
            label = str(item.get('text', '')).lower()
            if len(row) == 1:
                item['style'] = 'danger'
            elif index == 0:
                item['style'] = 'primary'
            else:
                item['style'] = 'success'
            # Keep dangerous confirmation/cancel controls red even in paired rows.
            if action in {'cancel', 'reboot_confirm'} or any(x in label for x in ('لغو', 'cancel', 'ریبوت', 'reboot')):
                item['style'] = 'danger'
            if include_custom_emoji:
                emoji, emoji_id = _button_icon_for(item)
                if emoji_id:
                    item['icon_custom_emoji_id'] = str(emoji_id)
                    original_label = str(item.get('text', ''))
                    prefix = next((p for p in sorted(_BUTTON_PREFIXES, key=len, reverse=True)
                                   if original_label.startswith(p)), None)
                    if prefix:
                        item['text'] = original_label[len(prefix):].lstrip()
            else:
                item.pop('icon_custom_emoji_id', None)
            styled_row.append(item)
        result['inline_keyboard'].append(styled_row)
    return result


def _has_custom_button_icons(data):
    try:
        markup = json.loads(data.get('reply_markup', '{}'))
        return any('icon_custom_emoji_id' in button
                   for row in markup.get('inline_keyboard', [])
                   for button in row if isinstance(button, dict))
    except Exception:
        return False


def _fallback_payload(data, fallback_data=None):
    """Use the original Unicode text and unadorned keyboard on retry."""
    if fallback_data is not None:
        return dict(fallback_data)
    result = dict(data)
    result.pop('entities', None)
    if 'reply_markup' in result:
        try:
            markup = json.loads(result['reply_markup'])
            for row in markup.get('inline_keyboard', []):
                for button in row:
                    if isinstance(button, dict):
                        button.pop('icon_custom_emoji_id', None)
            result['reply_markup'] = json.dumps(markup, ensure_ascii=False, separators=(',', ':'))
        except Exception:
            pass
    return result

def load_languages():
    try:
        d=json.loads(LANG_FILE.read_text())
        return {str(k): ('fa' if v == 'fa' else 'en') for k,v in d.items()}
    except Exception: return {}
def save_languages(data):
    try:
        LANG_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp=LANG_FILE.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, ensure_ascii=False))
        os.chmod(tmp, 0o600); os.replace(tmp, LANG_FILE)
    except Exception: pass
def language_prompt(): return '🌐 Please choose your language / لطفاً زبان خود را انتخاب کنید:'


def load():
    try:
        d = json.loads(CONFIG.read_text())
        token = str(d.get('token', '')).strip()
        admins = {int(x) for x in d.get('admin_ids', []) if str(x).isdigit()}
        return token, admins
    except Exception:
        return '', set()


def api(token, method, data=None, timeout=35):
    url = f'https://api.telegram.org/bot{token}/{method}'
    body = urllib.parse.urlencode(data or {}).encode()
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read(2_000_000))


# Optional Telegram Premium custom emoji. IDs can be overridden as a JSON
# object in IDM_TELEGRAM_CUSTOM_EMOJI_IDS; normal Unicode is always the fallback.
PREMIUM_EMOJI_IDS = {
    '👋': '5454390891466726015', '⚡️': '5085022089103016925',
    '⚙️': '5979014214595910994', '🧠': '5980861776382663883',
    '💾': '5978658578418900414', '🔒': '5116516255355897110',
    '✅': '6016907976609107800', '🔴': '6001066256025785838',
    '🟡': '6001542748287539188', '🔵': '6001233652376146830',
    '👤': '5974038293120027938', '🌐': '5974475701179387553',
    '📊': '5118775128980718591', '❗️': '5976801477509778431',
    '🔄': '6019623375192724683', '❌': '4958526153955476488', '⏰': '5809742105987259196',
}
try:
    _custom_ids = json.loads(os.environ.get('IDM_TELEGRAM_CUSTOM_EMOJI_IDS', '{}'))
    if isinstance(_custom_ids, dict):
        PREMIUM_EMOJI_IDS.update({str(k): str(v) for k, v in _custom_ids.items() if str(k) and str(v).isdigit()})
except Exception:
    pass

def custom_emoji_entities(text):
    # Telegram offsets and lengths are UTF-16 code units, not Python indexes.
    entities = []
    for emoji in sorted(PREMIUM_EMOJI_IDS, key=len, reverse=True):
        start = 0
        while True:
            index = text.find(emoji, start)
            if index < 0:
                break
            entities.append({'type': 'custom_emoji',
                'offset': len(text[:index].encode('utf-16-le')) // 2,
                'length': len(emoji.encode('utf-16-le')) // 2,
                'custom_emoji_id': PREMIUM_EMOJI_IDS[emoji]})
            start = index + len(emoji)
    entities.sort(key=lambda item: item['offset'])
    return entities

# Bot API does not expose a reliable Premium flag for the bot owner. Try custom
# entities and learn from Telegram's response. If Telegram explicitly says the
# owner cannot use them, switch to Unicode for the rest of this worker lifetime.
CUSTOM_EMOJI_CAPABILITY = None  # None=auto-detect, False=use Unicode fallback


def _error_detail(error):
    try:
        if isinstance(error, urllib.error.HTTPError):
            raw = error.read(1_000_000).decode('utf-8', 'replace')
            try:
                payload = json.loads(raw)
                return str(payload.get('description', raw)).lower()
            except Exception:
                return raw.lower()
        if isinstance(error, dict):
            return str(error.get('description', error)).lower()
        return str(error).lower()
    except Exception:
        return str(error).lower()


def _entity_rejected(error):
    detail = _error_detail(error)
    return any(term in detail for term in (
        'entity', 'custom emoji', 'custom_emoji', 'parse entities',
        'custom emoji id', 'custom_emoji_id', 'emoji entity', 'icon_custom_emoji_id',
        'button icon', 'custom emoji icon'
    ))


def _premium_not_available(error):
    detail = _error_detail(error)
    # Avoid treating "Premium emoji ID invalid" as proof that the owner lacks
    # Premium. Cache the downgrade only for explicit eligibility restrictions.
    return any(term in detail for term in (
        'non-premium', 'not a premium user', 'without telegram premium', 'without premium', 'owner must have telegram premium',
        'owner must have premium', 'not allowed to use custom emoji',
        'cannot use custom emoji', "can't use custom emoji",
        'custom emoji is not allowed', 'custom emoji are not allowed',
        'custom emoji icons are not allowed', 'not allowed to use custom emoji in buttons',
        'premium subscription is required', 'requires a telegram premium subscription'
    ))


def _send_with_optional_entities(token, method, data, text, fallback_data=None):
    global CUSTOM_EMOJI_CAPABILITY
    entities = custom_emoji_entities(text)
    has_button_icons = _has_custom_button_icons(data)
    wants_custom = bool(entities or has_button_icons)
    if not wants_custom:
        return api(token, method, data, timeout=12)

    fallback = _fallback_payload(data, fallback_data)
    if CUSTOM_EMOJI_CAPABILITY is False:
        return api(token, method, fallback, timeout=12)

    rich = dict(data)
    if entities:
        rich['entities'] = json.dumps(entities, separators=(',', ':'))
    else:
        rich.pop('entities', None)
    try:
        result = api(token, method, rich, timeout=12)
    except Exception as exc:
        detail = _error_detail(exc)
        if not _entity_rejected(detail):
            raise
        if _premium_not_available(detail):
            CUSTOM_EMOJI_CAPABILITY = False
        return api(token, method, fallback, timeout=12)

    # Some proxies/API wrappers return JSON ok:false instead of raising HTTPError.
    if isinstance(result, dict) and result.get('ok') is False:
        detail = _error_detail(result)
        if _entity_rejected(detail):
            if _premium_not_available(detail):
                CUSTOM_EMOJI_CAPABILITY = False
            return api(token, method, fallback, timeout=12)
    return result


def send(token, chat_id, text, keyboard=None):
    data = {'chat_id': str(chat_id), 'text': text[:3900]}
    fallback_data = dict(data)
    if keyboard:
        include_icons = CUSTOM_EMOJI_CAPABILITY is not False
        data['reply_markup'] = json.dumps(styled_keyboard(keyboard, include_custom_emoji=include_icons), ensure_ascii=False, separators=(',', ':'))
        fallback_data['reply_markup'] = json.dumps(styled_keyboard(keyboard, include_custom_emoji=False), ensure_ascii=False, separators=(',', ':'))
    try:
        _send_with_optional_entities(token, 'sendMessage', data, data['text'], fallback_data)
    except Exception:
        pass


def edit_message(token, chat_id, message_id, text, keyboard=None):
    data = {'chat_id': str(chat_id), 'message_id': str(message_id), 'text': text[:3900]}
    fallback_data = dict(data)
    data['reply_markup'] = json.dumps(styled_keyboard(keyboard, include_custom_emoji=CUSTOM_EMOJI_CAPABILITY is not False) if keyboard is not None else {'inline_keyboard': []}, ensure_ascii=False, separators=(',', ':'))
    fallback_data['reply_markup'] = json.dumps(styled_keyboard(keyboard, include_custom_emoji=False) if keyboard is not None else {'inline_keyboard': []}, ensure_ascii=False, separators=(',', ':'))
    try:
        _send_with_optional_entities(token, 'editMessageText', data, data['text'], fallback_data)
    except Exception:
        # A no-op edit can happen when the text and keyboard are unchanged.
        pass

def delete_message(token, chat_id, message_id):
    try:
        api(token, 'deleteMessage', {'chat_id': str(chat_id), 'message_id': str(message_id)}, timeout=8)
    except Exception:
        pass


def change_root_password(password):
    if not isinstance(password, str) or len(password) < 14 or len(password) > 128 or any(c in password for c in ('\n', '\r', '\x00', ':')):
        return False
    try:
        result = subprocess.run(['sudo', '-n', '/usr/local/sbin/idontmonitor-ops', 'change-root-password'],
                                input=password + '\n', capture_output=True, text=True, timeout=12,
                                close_fds=True, env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8'})
        return result.returncode == 0
    except Exception:
        return False


BACK = {'inline_keyboard': [[{'text': '↩️ بازگشت به منوی اصلی', 'callback_data': 'menu'}, {'text': '✖️ لغو', 'callback_data': 'cancel'}]]}
CONFIRM_REBOOT = {'inline_keyboard': [[{'text': '⚠️ بله، ریبوت کن', 'callback_data': 'reboot_confirm'}, {'text': '↩️ بازگشت', 'callback_data': 'menu'}], [{'text': '✖️ لغو', 'callback_data': 'cancel'}]]}
CONFIRM_PASSWORD = {'inline_keyboard': [[{'text': '✅ تأیید تغییر رمز', 'callback_data': 'password_confirm'}, {'text': '↩️ بازگشت', 'callback_data': 'password'}], [{'text': '✖️ لغو', 'callback_data': 'cancel'}]]}


def answer_callback(token, cb_id, message=''):
    try:
        api(token, 'answerCallbackQuery', {'callback_query_id': cb_id, 'text': message[:180]}, timeout=8)
    except Exception:
        pass


def memory_info():
    values = {}
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                values[k] = int(v.strip().split()[0])
    except Exception:
        pass
    total = values.get('MemTotal', 0)
    available = values.get('MemAvailable', 0)
    return total, max(0, total - available)


def uptime_text():
    try:
        seconds = int(float(Path('/proc/uptime').read_text().split()[0]))
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes = rem // 60
        return f'{days} روز، {hours} ساعت، {minutes} دقیقه'
    except Exception:
        return 'نامشخص'


def cpu_percent():
    try:
        fields=Path('/proc/stat').read_text().splitlines()[0].split()[1:]
        values=[int(x) for x in fields]
        idle=values[3]+(values[4] if len(values)>4 else 0)
        total=sum(values)
        previous=getattr(cpu_percent, '_previous', None)
        cpu_percent._previous=(total,idle)
        if previous is None: time.sleep(0.12); return cpu_percent()
        dt=total-previous[0]; di=idle-previous[1]
        return round(max(0,min(100,(dt-di)*100/dt)),1) if dt>0 else 0.0
    except Exception: return 0.0


def cpu_count():
    try:
        return sum(1 for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('processor')) or 1
    except Exception:
        return os.cpu_count() or 1


def disk_info():
    try:
        d = shutil.disk_usage('/')
        return d.total, d.used, d.free
    except Exception:
        return 0, 0, 0


def network_info():
    rx = tx = 0
    try:
        for line in Path('/proc/net/dev').read_text().splitlines()[2:]:
            iface, raw = line.split(':', 1)
            iface = iface.strip()
            if iface == 'lo':
                continue
            vals = raw.split()
            rx += int(vals[0]); tx += int(vals[8])
    except Exception:
        pass
    return rx, tx


def fmt_bytes(n):
    value = float(n)
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if value < 1024 or unit == 'TiB':
            return f'{value:.1f} {unit}'
        value /= 1024



def _read_key_value_file(path):
    """Read simple KEY=value deployment metadata without executing shell code."""
    values = {}
    try:
        for line in Path(path).read_text(encoding='utf-8').splitlines():
            if '=' not in line or line.lstrip().startswith('#'):
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            if key and re.fullmatch(r'[A-Z0-9_]+', key):
                values[key] = value.strip().strip('"').strip("'")
    except (OSError, UnicodeError):
        pass
    return values


def panel_login_url():
    """Resolve the URL from idontMonitor's own installer/runtime metadata only.

    HTTPS installs are served publicly by Caddy on standard HTTPS; the app port is
    loopback-only and must never be exposed as the public panel port. HTTP installs
    publish the dedicated port recorded by idontMonitor's installer. Never guess a
    sibling product's port or call an external IP-detection service from the bot.
    """
    configured = os.environ.get('IDM_PANEL_URL', '').strip()
    if configured:
        parsed = urllib.parse.urlsplit(configured)
        if parsed.scheme in ('http', 'https') and parsed.hostname:
            return configured.rstrip('/')
        return None

    state_path = os.environ.get('IDM_INSTALL_MODE_FILE', '/var/lib/idontmonitor/install-mode')
    env_path = os.environ.get('IDM_ENV_FILE', '/etc/idontmonitor/environment')
    state = _read_key_value_file(state_path)
    runtime = _read_key_value_file(env_path)
    mode = state.get('MODE', '').lower()

    # Optional explicit host override is only a host; the port and scheme still
    # come from idontMonitor's own installation metadata.
    host = os.environ.get('IDM_PUBLIC_HOST', '').strip()
    if mode == 'https':
        host = host or state.get('DOMAIN', '').strip()
        if not host:
            return None
        # A domain-backed Caddy site is publicly exposed on 443, not on the
        # local Uvicorn port in /etc/idontmonitor/environment.
        return f'https://{host.rstrip("./")}'
    if mode == 'http':
        host = host or state.get('PUBLIC_IP', '').strip()
        port = state.get('HTTP_PORT', '').strip() or runtime.get('IDM_APP_PORT', '').strip()
        if not host or not port.isdigit() or not (1 <= int(port) <= 65535):
            return None
        return f'http://{host}:{int(port)}'

    # If installer metadata is absent, do not guess from WEB_PUBLIC_PORT,
    # serverip, or a random public-IP lookup; a wrong link is worse than no link.
    return None

def status_text():
    total, used = memory_info()
    mem = f'{fmt_bytes(used * 1024)} / {fmt_bytes(total * 1024)} ({used / total * 100:.1f}٪)' if total else 'نامشخص'
    _, disk_used, disk_free = disk_info()
    return ('📊 وضعیت سرور idontMonitor\n\n'
            f'⏰ زمان فعالیت: {uptime_text()}\n'
            f'✅ وضعیت سرویس: فعال\n'
            f'🧠 مصرف RAM: {mem}\n'
            f'💾 دیسک مصرف‌شده: {fmt_bytes(disk_used)}\n'
            f'🔵 فضای آزاد دیسک: {fmt_bytes(disk_free)}\n'
            f'⚙️ هسته‌های CPU: {cpu_count()}\n'
            f'⚙️ استفاده از CPU: ⚡️ {cpu_percent():.1f}%')

def resources_text():
    total, used = memory_info()
    disk_total, disk_used, disk_free = disk_info()
    mem = f'{fmt_bytes(used * 1024)} از {fmt_bytes(total * 1024)}' if total else 'در دسترس نیست'
    disk = f'{fmt_bytes(disk_used)} از {fmt_bytes(disk_total)} (آزاد: {fmt_bytes(disk_free)})' if disk_total else 'در دسترس نیست'
    return f'🧠 منابع سیستم\n\n⚡️ استفاده از CPU: {cpu_percent():.1f}%\n🧠 RAM: {mem}\n💾 فضای دیسک: {disk}\n⚙️ تعداد هسته CPU: {cpu_count()}\n\nمقادیر از سیستم‌عامل خوانده شده‌اند.'


def network_text():
    rx, tx = network_info()
    return f'🌐 شبکه و ترافیک\n\n📊 دریافت کل از شمارنده‌های فعلی: {fmt_bytes(rx)}\n🔵 ارسال کل از شمارنده‌های فعلی: {fmt_bytes(tx)}\n\nاین اعداد شمارنده‌های رابط‌های شبکه هستند و ممکن است پس از راه‌اندازی مجدد صفر شوند.'


def tunnels_text():
    """Read known tunnel service states without invoking arbitrary commands."""
    found = []
    try:
        p = subprocess.run(['/usr/bin/systemctl', 'list-units', '--type=service', '--all', '--no-legend', '--plain'],
                           capture_output=True, text=True, timeout=5, check=False)
        for line in p.stdout.splitlines():
            parts = line.split(None, 4)
            if len(parts) < 4:
                continue
            unit, load_state, active_state, sub_state = parts[:4]
            lower = unit.lower()
            if any(key in lower for key in ('backpack', 'c-tunnel', 'ctunnel', 'paqet', 'paquet')):
                found.append((unit, active_state if active_state else sub_state))
    except Exception:
        pass
    if not found:
        return '🟡 وضعیت تانل‌ها\n\nسرویس شناخته‌شده‌ای با نام BackPack، C-Tunnel یا Paqet در systemd پیدا نشد. برای جزئیات کامل، پنل وب را باز کنید.'
    lines = ['🔗 وضعیت سرویس‌های تانل شناسایی‌شده', '']
    lines.extend(f'{"✅" if state == "active" else ("🔴" if state in ("failed", "inactive") else "🟡")} {unit}: {state}' for unit, state in found[:30])
    return '\n'.join(lines)


def response_for(action, lang='fa'):
    if action == 'panel_link':
        url = panel_login_url()
        if url:
            return (f'🔗 لینک ورود به پنل: {url}' if lang != 'en' else f'🔗 Panel login link: {url}')
        return ('🔗 آدرس عمومی پنل پیدا نشد. متغیر IDM_PANEL_URL یا IDM_PUBLIC_HOST و IDM_WEB_PORT را تنظیم کنید.' if lang != 'en' else '🔗 Public panel address could not be detected. Set IDM_PANEL_URL or IDM_PUBLIC_HOST and IDM_WEB_PORT.')
    if lang == 'en':
        if action in ('status','refresh'):
            total,used=memory_info(); dt,du,df=disk_info()
            mem=f'{fmt_bytes(used*1024)} / {fmt_bytes(total*1024)} ({used/total*100:.1f}%)' if total else 'Unavailable'
            return f'📊 idontMonitor server status\n\n⏰ Uptime: {uptime_text()}\n✅ Service: active\n⚙️ CPU usage: ⚡️ {cpu_percent():.1f}%\n🧠 RAM: {mem}\n💾 Disk used: {fmt_bytes(du)}\n🔵 Disk free: {fmt_bytes(df)}\n⚙️ CPU cores: {cpu_count()}'
        if action == 'resources':
            total,used=memory_info(); dt,du,df=disk_info()
            return f'🧠 System resources\n\n⚙️ CPU usage: ⚡️ {cpu_percent():.1f}%\n🧠 RAM: {fmt_bytes(used*1024)} / {fmt_bytes(total*1024)}\n💾 Disk: {fmt_bytes(du)} / {fmt_bytes(dt)} (free: {fmt_bytes(df)})\n⚙️ CPU cores: {cpu_count()}'
        if action == 'network':
            rx,tx=network_info(); return f'🌐 Network & traffic\n\n📊 Total received: {fmt_bytes(rx)}\n🔵 Total sent: {fmt_bytes(tx)}\n\nCounters may reset after reboot.'
        if action == 'tunnels':
            fa=tunnels_text().replace('وضعیت تانل‌ها','Tunnel status').replace('وضعیت سرویس‌های تانل شناسایی‌شده','Detected tunnel services').replace('سرویس شناخته‌شده‌ای با نام BackPack، C-Tunnel یا Paqet در systemd پیدا نشد. برای جزئیات کامل، پنل وب را باز کنید.','No BackPack, C-Tunnel, or Paqet service was detected.')
            return fa
        if action == 'help': return '❗️ idontMonitor bot help\n\n/start — Main menu\n/status — Server status\n/resources — System resources\n/network — Network traffic\n/tunnels — Tunnel status\n/help — Help\n/reboot — Reboot with confirmation\n\nAccess is restricted to administrators configured in the web panel.'
        return 'Unknown action. Send /start to open the menu.'
    if action in ('status', 'refresh'): return status_text()
    if action == 'resources': return resources_text()
    if action == 'network': return network_text()
    if action == 'tunnels': return tunnels_text()
    if action == 'help': return ('❗️ راهنمای ربات idontMonitor\n\n/start — نمایش منوی اصلی\n/status — وضعیت سرور\n/resources — منابع سیستم\n/network — ترافیک شبکه\n/tunnels — وضعیت سرویس‌های تانل\n/help — راهنما\n/reboot — راه‌اندازی مجدد با تأیید\n\nاین ربات فقط برای شناسه‌های ادمین ثبت‌شده در پنل قابل استفاده است.')
    return 'دستور شناخته نشد. برای نمایش منو /start را ارسال کنید.'


def main():
    global OFFSET
    last_token = ''
    flows = {}  # (user_id, chat_id) -> short-lived, in-memory state; never written to disk.
    languages = load_languages()
    while True:
        token, admins = load()
        if not token or not admins:
            time.sleep(3)
            continue
        if token != last_token:
            OFFSET = 0
            flows.clear()
            last_token = token
        try:
            result = api(token, 'getUpdates', {'timeout': 25, 'offset': OFFSET, 'allowed_updates': json.dumps(['message', 'callback_query'])}, timeout=35)
            if not result.get('ok'):
                time.sleep(3); continue
            for update in result.get('result', []):
                OFFSET = max(OFFSET, int(update.get('update_id', 0)) + 1)
                cb = update.get('callback_query')
                incoming = update.get('message') or {}
                message = incoming or ((cb or {}).get('message') or {})
                sender = (incoming or cb or {}).get('from') or {}
                uid = sender.get('id')
                chat = (message.get('chat') or {}).get('id')
                msg_text = incoming.get('text', '').strip()
                msg_id = message.get('message_id')
                command = msg_text.split(' ', 1)[0].split('@', 1)[0].lower() if msg_text else ''
                key = (uid, chat)
                lang = languages.get(str(uid), '')
                if uid not in admins:
                    if command == '/start' and chat is not None:
                        send(token, chat, 'شما دسترسی به ربات ندارید.\nYou do not have access to this bot.')
                    if cb: answer_callback(token, cb.get('id', ''), 'Access denied')
                    continue
                if cb:
                    action = cb.get('data', '')
                    answer_callback(token, cb.get('id', ''))
                    if chat is None or msg_id is None: continue
                    if action == 'lang_fa' or action == 'lang_en':
                        languages[str(uid)] = 'fa' if action == 'lang_fa' else 'en'; save_languages(languages)
                        lang = languages[str(uid)]
                        edit_message(token, chat, msg_id, '🟢 منوی مدیریت idontMonitor\nزبان روی فارسی تنظیم شد.' if lang == 'fa' else '🟢 idontMonitor admin menu\nLanguage set to English.', menu(lang))
                        continue
                    if action == 'language':
                        edit_message(token, chat, msg_id, language_prompt(), LANGUAGES); continue
                    if action in ('menu', 'cancel'):
                        flows.pop(key, None)
                        edit_message(token, chat, msg_id, ('🟢 منوی مدیریت idontMonitor\nعملیات لغو شد.' if action == 'cancel' else '🟢 منوی مدیریت idontMonitor\nیک عملیات را انتخاب کنید.') if lang != 'en' else ('🟢 idontMonitor admin menu\nOperation cancelled.' if action == 'cancel' else '🟢 idontMonitor admin menu\nChoose an action.'), menu(lang))
                    elif action in ('status', 'refresh', 'resources', 'network', 'tunnels', 'help', 'panel_link'):
                        edit_message(token, chat, msg_id, response_for(action, lang or 'fa'), menu(lang or 'fa'))
                    elif action == 'password':
                        if (message.get('chat') or {}).get('type') != 'private':
                            edit_message(token, chat, msg_id, '🔒 تغییر رمز فقط در گفت‌وگوی خصوصی با ربات مجاز است. برای امنیت، رمز را در گروه ارسال نکنید.' if lang != 'en' else '🔒 Password changes are only allowed in a private chat. Never send passwords in groups.', menu(lang or 'fa'))
                            continue
                        flows[key] = {'step': 'password_new', 'message_id': msg_id, 'created_at': time.time()}
                        edit_message(token, chat, msg_id, ('🔐 تغییر رمز عبور root VPS\n\nیک رمز جدید و قوی با حداقل ۱۴ کاراکتر را در پیام بعدی بفرستید. پیام رمز بلافاصله برای حذف درخواست می‌شود و در فایل ذخیره نخواهد شد. رمز در تاریخچه سرویس تلگرام ممکن است موقتاً قابل مشاهده باشد؛ از این روش فقط در گفت‌وگوی خصوصی با ربات استفاده کنید.' if lang != 'en' else '🔐 Change root VPS password\n\nSend a strong password of at least 14 characters in your next message. The incoming message will be deleted immediately; use this only in a private chat. Telegram may temporarily retain message history.'), {'inline_keyboard': [[{'text':'↩️ بازگشت','callback_data':'menu'},{'text':'✖️ لغو','callback_data':'cancel'}]] if lang != 'en' else [[{'text':'↩️ Back','callback_data':'menu'},{'text':'✖️ Cancel','callback_data':'cancel'}]]})
                    elif action == 'reboot':
                        flows[key] = {'step': 'reboot_confirm', 'message_id': msg_id}
                        edit_message(token, chat, msg_id, ('⚠️ راه‌اندازی مجدد VPS\n\nاتصال‌ها و سرویس‌ها موقتاً قطع می‌شوند. آیا مطمئن هستید؟' if lang != 'en' else '⚠️ Reboot VPS\n\nConnections and services will be interrupted temporarily. Continue?'), {'inline_keyboard': [[{'text':'⚠️ بله، ریبوت کن','callback_data':'reboot_confirm'},{'text':'↩️ بازگشت','callback_data':'menu'}],[{'text':'✖️ لغو','callback_data':'cancel'}]]} if lang != 'en' else {'inline_keyboard': [[{'text':'⚠️ Confirm reboot','callback_data':'reboot_confirm'},{'text':'↩️ Back','callback_data':'menu'}],[{'text':'✖️ Cancel','callback_data':'cancel'}]]})
                    elif action == 'reboot_confirm':
                        flows.pop(key, None)
                        try:
                            r = subprocess.run(['sudo', '-n', '/usr/local/sbin/idontmonitor-ops', 'reboot-vps'], capture_output=True, text=True, timeout=5, close_fds=True, env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8'})
                            if r.returncode == 0:
                                edit_message(token, chat, msg_id, '♻️ درخواست ریبوت ارسال شد. اتصال ربات ممکن است تا بالا آمدن مجدد سرور قطع شود.', None)
                            else:
                                edit_message(token, chat, msg_id, '❌ ریبوت انجام نشد. helper مجاز یا مجوز sudo را بررسی کنید.', MENU)
                        except subprocess.TimeoutExpired:
                            edit_message(token, chat, msg_id, '♻️ درخواست ریبوت ارسال شد؛ سرور در حال راه‌اندازی مجدد است.', None)
                        except Exception:
                            edit_message(token, chat, msg_id, '❌ ارسال درخواست ریبوت ناموفق بود.', MENU)
                    elif action == 'password_confirm':
                        flow = flows.get(key, {})
                        password = flow.pop('password', None)
                        flows.pop(key, None)
                        if not password:
                            edit_message(token, chat, msg_id, '⌛ مرحله تغییر رمز منقضی شده است. از منو دوباره شروع کنید.', MENU)
                        elif change_root_password(password):
                            edit_message(token, chat, msg_id, '✅ رمز عبور root VPS با موفقیت تغییر کرد. رمز قبلی دیگر معتبر نیست.', MENU)
                        else:
                            edit_message(token, chat, msg_id, '❌ تغییر رمز انجام نشد. helper یا سیاست رمز عبور را بررسی کنید.', MENU)
                    else:
                        edit_message(token, chat, msg_id, 'گزینه ناشناخته است.', MENU)
                    continue
                if not msg_text or chat is None:
                    continue
                flow = flows.get(key)
                if flow and time.time() - float(flow.get('created_at', time.time())) > 300:
                    flows.pop(key, None)
                    flow = None
                if flow and flow.get('step') == 'password_new':
                    # Delete the user's message immediately; never echo/log the secret.
                    delete_message(token, chat, msg_id)
                    if len(msg_text) < 14 or len(msg_text) > 128 or any(c in msg_text for c in ('\n','\r','\x00',':')):
                        edit_message(token, chat, flow['message_id'], '❌ رمز باید ۱۴ تا ۱۲۸ کاراکتر داشته باشد و شامل دو نقطه نباشد. دوباره تلاش کنید یا لغو کنید.', BACK)
                        continue
                    flow['password'] = msg_text
                    flow['step'] = 'password_confirm'
                    edit_message(token, chat, flow['message_id'], '🔐 رمز جدید دریافت شد. پیام ورودی حذف درخواست شد. برای اعمال تغییر رمز root VPS تأیید کنید.', CONFIRM_PASSWORD)
                    continue
                if command in ('/start', '/menu'):
                    flows.pop(key, None)
                    if not lang:
                        send(token, chat, language_prompt(), LANGUAGES)
                    else:
                        send(token, chat, '👋 idontMonitor\n👤 دسترسی ادمین تأیید شد. از منوی زیر برای مشاهده اطلاعات یا مدیریت امن VPS استفاده کنید.' if lang == 'fa' else '👋 idontMonitor\n👤 Administrator access verified. Choose an action below.', menu(lang))
                elif command == '/status': send(token, chat, response_for('status', lang or 'fa'), menu(lang or 'fa'))
                elif command == '/resources': send(token, chat, response_for('resources', lang or 'fa'), menu(lang or 'fa'))
                elif command == '/network': send(token, chat, response_for('network', lang or 'fa'), menu(lang or 'fa'))
                elif command == '/tunnels': send(token, chat, response_for('tunnels', lang or 'fa'), menu(lang or 'fa'))
                elif command == '/help': send(token, chat, response_for('help', lang or 'fa'), menu(lang or 'fa'))
                elif command == '/reboot':
                    flows[key] = {'step': 'reboot_confirm', 'message_id': None}
                    send(token, chat, '⚠️ برای ریبوت VPS از دکمه تأیید استفاده کنید.' if lang != 'en' else '⚠️ Use the confirmation button to reboot the VPS.', CONFIRM_REBOOT)
                else:
                    send(token, chat, 'از دکمه‌های منو استفاده کنید یا /help را بفرستید.' if lang != 'en' else 'Use the menu buttons or send /help.', menu(lang or 'fa'))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            time.sleep(3)
        except Exception:
            time.sleep(3)


if __name__ == '__main__':
    main()
