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
    assert "sys.argv[1] not in ('apply','apply-main')" in source
    assert 'Release asset/tag archive' in source or 'release asset' in source
    assert "tarfile.open" in source
    assert "Unsafe path or unsupported file type" in source
    assert "Health check failed; previous release was restored" in source

def test_update_api_is_authenticated_and_no_arbitrary_urls():
    source=(ROOT / "app" / "main.py").read_text()
    assert "@app.get('/api/updates/check')" in source
    assert "@app.post('/api/updates/apply')" in source
    assert "require_auth(request)" in source
    assert "UPDATE_REPO = \"durwinam/idontMonitor\"" in source


def test_release_source_prefers_exact_tar_asset(monkeypatch):
    import json
    release = {"tag_name":"v2.0.1", "html_url":"https://github.com/durwinam/idontMonitor/releases/tag/v2.0.1",
               "assets":[{"name":"idontMonitor-v2.0.1.tar.gz",
                           "browser_download_url":"https://github.com/durwinam/idontMonitor/releases/download/v2.0.1/idontMonitor-v2.0.1.tar.gz",
                           "state":"uploaded", "digest":"sha256:" + "a"*64},
                          {"name":"notes.txt", "browser_download_url":"https://example.com/notes.txt"}]}
    monkeypatch.setitem(helper["release_source"].__globals__, "request", lambda *a, **k: json.dumps(release).encode())
    version, url, page, digest = helper["release_source"]()
    assert version == "2.0.1"
    assert url == release["assets"][0]["browser_download_url"]
    assert digest == "sha256:" + "a"*64

def test_archive_rejects_unsafe_members(tmp_path):
    import io, tarfile, pytest
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        info=tarfile.TarInfo("../escape")
        data=b"bad"; info.size=len(data)
        tf.addfile(info, io.BytesIO(data))
    with pytest.raises(RuntimeError):
        helper["safe_extract"](buf.getvalue(), tmp_path)
