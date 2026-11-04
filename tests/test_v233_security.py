from pathlib import Path
from types import SimpleNamespace
from app import main

def test_password_policy_requires_mixed_classes():
    assert main.password_policy_ok("C0mpl3x!LongPassword")
    assert not main.password_policy_ok("a" * 30)
    assert not main.password_policy_ok("lowercase123456789!")
    assert not main.password_policy_ok("UPPERCASE123456789!")
    assert not main.password_policy_ok("C0mpl3x!Short")

def test_login_challenge_is_server_side_and_single_use():
    req=SimpleNamespace(client=SimpleNamespace(host="192.0.2.20"), session={})
    challenge=main._new_login_challenge(req)
    assert "login_captcha" not in req.session
    record=main.LOGIN_CAPTCHA_CHALLENGES.pop(challenge["token"])
    assert record["ip"] == "192.0.2.20" and record["answer"].isdigit()
    assert challenge["expires_in"] == 180

def test_installer_uses_random_username_and_complex_password():
    text=(Path(__file__).resolve().parents[1]/"install.sh").read_text()
    assert "INITIAL_USERNAME" in text and "secrets.randbelow(90000) + 10000" in text
    assert "secrets.SystemRandom().shuffle(chars)" in text
    assert '"admin_user":"admin"' not in text

def test_account_state_is_defined_and_used():
    text=(Path(__file__).resolve().parents[1]/"app/main.py").read_text()
    assert 'ACCOUNT_STATE_PATH = Path(' in text
    assert 'account = json.loads(ACCOUNT_STATE_PATH.read_text())' in text
    assert 'os.replace(tmp, ACCOUNT_STATE_PATH)' in text


def test_account_state_round_trip_is_atomic_and_private(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ACCOUNT_STATE_PATH", tmp_path / "account.json")
    old_cfg = dict(main.CFG)
    try:
        main.CFG["admin_user"] = "48371"
        main.CFG["admin_hash"] = "scrypt$32768$8$1$abcd$ef01"
        main._save_config()
        path = tmp_path / "account.json"
        assert path.exists() and path.stat().st_mode & 0o777 == 0o600
        saved = __import__("json").loads(path.read_text())
        assert saved["admin_user"] == "48371"
        monkeypatch.setattr(main, "CONFIG_PATH", tmp_path / "deployment.json")
        (tmp_path / "deployment.json").write_text('{"version":"2.3.4","session_secret":"test","allowed_hosts":["localhost"]}')
        loaded = main.load_config()
        assert loaded["admin_user"] == "48371" and loaded["admin_hash"] == "scrypt$32768$8$1$abcd$ef01"
    finally:
        main.CFG.clear(); main.CFG.update(old_cfg)


def test_scrypt_derivation_works_with_reset_memory_cap():
    import hashlib, secrets
    password = "V3ry$trong-ResetPassw0rd!"
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=32768, r=8, p=1, dklen=32, maxmem=512*1024*1024)
    assert len(digest) == 32
    installer = (Path(__file__).resolve().parents[1]/"install.sh").read_text()
    assert "maxmem=512*1024*1024" in installer
    main = (Path(__file__).resolve().parents[1]/"app/main.py").read_text()
    assert "maxmem=512*1024*1024" in main

def test_http_login_is_allowed_and_warning_is_localized_and_temporary():
    root = Path(__file__).resolve().parents[1]
    source = (root / 'app/main.py').read_text()
    page = (root / 'static/login.html').read_text()
    assert 'Remote login requires HTTPS' not in source
    assert "location.protocol!=='http:'" in page
    assert 'enable HTTPS' in page and 'SSL/TLS' in page
    assert 'HTTPS را فعال کنید' in page and 'SSL/TLS' in page
    assert '},5000)' in page
    assert 'languageSelect' in page and 'updateHttpNotice' in page
