from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
js = (ROOT / "static/app.js").read_text()
css = (ROOT / "static/style.css").read_text()
html = (ROOT / "static/index.html").read_text()
assert "if(window.idmRefreshing)return;window.idmRefreshing=true" in js
assert "finally{window.idmRefreshing=false}" in js
assert "$('version').textContent='v4.0.2'" in js
assert "--surface-1" in css and "--control-bg" in css
assert ".traffic-stats>div,.security-summary" in css
assert "v4.0.2" in html and "v=4020" in html
assert not (ROOT / "static/fonts/Vazirmatn-Regular.ttf").exists()
print("v4.0.2 theme consistency, refresh overlap guard, version display, and asset reference checks passed.")


def test_v229_theme_surfaces_use_palette_variables():
    css=(ROOT/'static/style.css').read_text()
    js=(ROOT/'static/app.js').read_text()
    assert '.tunnel-card-dedicated{background:linear-gradient(145deg,var(--surface-raised),var(--surface-inset))' in css
    assert "root.style.setProperty('--surface-raised'" in js
    assert 'input:not([type=checkbox])' in css and 'var(--control-bg)' in css
