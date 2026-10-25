import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
helper = runpy.run_path(str(ROOT / "scripts" / "idontmonitor-update"))

def test_stable_version_parser():
    assert helper["version_tuple"]("v1.8.1") == (1, 8, 1)
    assert helper["version_tuple"]("1.10.0") > helper["version_tuple"]("1.9.9")

def test_version_parser_rejects_untrusted_tag():
    import pytest
    for invalid in ("main", "latest", "v1.2", "../1.2.3", "v1.2.3-rc1"):
        with pytest.raises(RuntimeError):
            helper["version_tuple"](invalid)

def test_update_helper_is_fixed_action_only():
    source=(ROOT / "scripts" / "idontmonitor-update").read_text()
    assert "sys.argv[1]!='apply'" in source
    assert "SHA-256 verification failed" in source
    assert "Unsafe archive paths detected" in source
    assert "Health check failed; previous version restored" in source

def test_update_api_is_authenticated_and_no_arbitrary_urls():
    source=(ROOT / "app" / "main.py").read_text()
    assert "@app.get('/api/updates/check')" in source
    assert "@app.post('/api/updates/apply')" in source
    assert "require_auth(request)" in source
    assert "UPDATE_REPO = \"durwinam/idontMonitor\"" in source
