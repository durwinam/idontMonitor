from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
css = (ROOT / "static/style.css").read_text()
js = (ROOT / "static/app.js").read_text()
html = (ROOT / "static/index.html").read_text()
assert "@keyframes boot-overlay-exit" in css
assert "@media(prefers-reduced-motion:reduce)" in css
assert "-webkit-backdrop-filter" in css
assert "100dvh" in css and "-webkit-fill-available" in css
assert "prefers-reduced-motion: reduce" in js
assert "Dashboard ready · telemetry may still be loading" in js
assert "style.css?v=198" in html and "app.js?v=198" in html
assert "@import url('');" not in css
print("Motion, viewport, reduced-motion and loader regression checks passed.")
