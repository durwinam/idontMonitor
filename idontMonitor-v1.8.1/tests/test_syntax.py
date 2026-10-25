import ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ast.parse((ROOT/'app/main.py').read_text())
assert (ROOT/'static/index.html').exists()
assert (ROOT/'install.sh').stat().st_mode & 0o111
print('Basic source structure and Python syntax checks passed.')

css=(ROOT/'static/style.css').read_text()
installer=(ROOT/'install.sh').read_text()
assert '@media(max-width:850px){.login-body{display:block' in css
assert '.login-layout{display:flex;flex-direction:column' in css
assert 'Protected pre-upgrade backup created' in installer
assert 'Safe upgrade: preserving' in installer
assert 'Existing install metadata is incomplete; refusing upgrade' in installer
assert 'Existing reverse-proxy configuration byte-for-byte' not in installer or 'Keep the active reverse-proxy configuration byte-for-byte' in installer
assert 'find_free_port 0.0.0.0' in installer and 'if (( EXISTING_INSTALL == 0 )); then' in installer
print('Mobile login and safe-upgrade regression checks passed.')
