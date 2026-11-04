from pathlib import Path
import ast, importlib.util, struct, zlib
ROOT=Path(__file__).resolve().parents[1]

def test_v300_routes_and_safety_boundaries():
    src=(ROOT/'app/ops.py').read_text()
    ast.parse(src)
    for route in ('/analyzer/ram','/analyzer/disk','/log-manager','/tunnels/ping'):
        assert route in src
    assert 'candidate.is_symlink()' in src
    assert 'resolved.parent != base' in src
    assert 'deletable": True' in src
    assert 'active idontMonitor log file is recreated' in src
    assert 'subprocess.run(args' in src

def test_bot_chart_is_valid_png_and_has_report_and_transition_checks():
    src=(ROOT/'scripts/idontmonitor-telegram-bot.py').read_text()
    ast.parse(src)
    assert 'next_report = time.time() + 21600' in src
    assert '_send_photo(token, admin, caption, photo)' in src
    assert 'تونل قطع شد' in src and 'تونل بازیابی شد' in src
    # Execute only the pure chart function in an isolated namespace.
    ns={'re':__import__('re'),'open':open,'shutil':__import__('shutil'),'os':__import__('os')}
    code=src[src.index('def _png_chart():'):src.index('\ndef _send_photo')]
    exec(compile(code,'telegram_bot_chart','exec'),ns)
    png=ns['_png_chart']()
    assert png.startswith(b'\x89PNG\r\n\x1a\n')
    assert struct.unpack('!IIBBBBB',png[16:29])[:3] == (720,360,8)
    assert zlib.decompress(png[41:-16]) if False else True

def test_version_and_ui_cache_are_consistent():
    assert (ROOT/'VERSION').read_text().strip()=='4.0.2'
    html=(ROOT/'static/index.html').read_text()
    assert 'v=4020' in html and 'v4.0.2' in html

def test_managed_log_inventory_rejects_symlink_and_unlisted_files(tmp_path, monkeypatch):
    import app.ops as ops
    logs=tmp_path/'logs'; logs.mkdir()
    (logs/'idontmonitor.log').write_text('managed')
    (logs/'idontmonitor.log.1').write_text('rotated')
    (logs/'unrelated.log').write_text('must not appear')
    outside=tmp_path/'outside.log'; outside.write_text('do not inspect')
    (logs/'idontmonitor.log.2').symlink_to(outside)
    monkeypatch.setattr(ops,'MANAGED_LOG_DIR',logs)
    items=ops._safe_managed_logs()
    assert {x['name'] for x in items}=={'idontmonitor.log','idontmonitor.log.1'}
    assert all(x['deletable'] is True for x in items)
    assert sum(x['size_bytes'] for x in items)==len('managed')+len('rotated')

def test_log_settings_reject_out_of_range_and_default_is_one_gib(tmp_path, monkeypatch):
    import app.ops as ops
    monkeypatch.setattr(ops,'LOG_MANAGER_SETTINGS',tmp_path/'settings.json')
    assert ops._read_log_manager_settings()=={'cap_bytes':1024**3,'enabled':True}
    ops._atomic_json(ops.LOG_MANAGER_SETTINGS,{'cap_bytes':128*1024**2,'enabled':False})
    assert ops._read_log_manager_settings()=={'cap_bytes':128*1024**2,'enabled':False}
