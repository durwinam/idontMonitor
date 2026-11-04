from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import main

# Challenge state is server-side, bounded, short-lived, and bound to IP/session.
request = SimpleNamespace(session={"login_at": 12345}, client=SimpleNamespace(host="192.0.2.10"))
challenge = main._new_vps_password_captcha(request)
record = main.VPS_CAPTCHA_CHALLENGES[challenge["token"]]
assert challenge["expires_in"] == 180
assert record["ip"] == "192.0.2.10" and record["login_at"] == 12345
assert challenge["question"].split(" + ") and 4 <= sum(map(int, challenge["question"].split(" + "))) <= 18

# Telegram custom emoji offsets must be measured in UTF-16 code units.
spec = spec_from_file_location("idontmonitor_telegram_bot", ROOT / "scripts/idontmonitor-telegram-bot.py")
bot = module_from_spec(spec)
spec.loader.exec_module(bot)
text = "سلام 📊 CPU ⚙️"
entities = bot.custom_emoji_entities(text)
assert len(entities) == 2
assert entities[0]["offset"] == len("سلام ".encode("utf-16-le")) // 2
assert entities[1]["offset"] == len("سلام 📊 CPU ".encode("utf-16-le")) // 2
assert all(e["type"] == "custom_emoji" and e["custom_emoji_id"].isdigit() for e in entities)
assert bot.PREMIUM_EMOJI_IDS["⚙️"] == "5979014214595910994"
assert bot.PREMIUM_EMOJI_IDS["🧠"] == "5980861776382663883"
assert bot.PREMIUM_EMOJI_IDS["💾"] == "5978658578418900414"
# Explicit custom-entity rejection retries plain text exactly once.
calls = []
def fake_api(token, method, data, timeout=12):
    calls.append(dict(data))
    if len(calls) == 1:
        raise ValueError("Telegram custom emoji entity rejected")
    return {"ok": True}
bot.api = fake_api
assert bot._send_with_optional_entities("token", "sendMessage", {"chat_id":"1", "text":"⚙️ CPU"}, "⚙️ CPU")["ok"]
assert len(calls) == 2 and "entities" in calls[0] and "entities" not in calls[1]

# Verify response hardening is active in the actual ASGI app.
from fastapi.testclient import TestClient
response = TestClient(main.app).get("/healthz", headers={"host": "localhost"})
assert response.status_code == 200
assert response.headers.get("X-Content-Type-Options") == "nosniff"
assert response.headers.get("X-Frame-Options") == "DENY"
assert response.headers.get("Cache-Control") == "no-store"
print("v2.2.8 CAPTCHA state, Telegram UTF-16 emoji entities, and live ASGI security-header smoke checks passed.")
