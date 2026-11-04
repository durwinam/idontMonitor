from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def test_version_is_3400_everywhere():
    assert (ROOT / 'VERSION').read_text().strip() == '4.0.2'
    install = (ROOT / 'install.sh').read_text()
    assert 'VERSION="4.0.2"' in install
    assert 'VERSION="1.9.9"' not in install

def test_updater_supports_tar_and_main():
    updater = (ROOT / 'scripts/idontmonitor-update').read_text()
    assert 'tarfile.open' in updater
    assert 'releases/latest' in updater
    assert 'apply-main' in updater
    assert 'assets' in updater and 'idontMonitor-v' in updater
    assert 'expected_digest' in updater
    assert '.zip' not in updater

def test_port_probe_exists():
    install = (ROOT / 'install.sh').read_text()
    assert 'find_free_port()' in install
    assert 's.bind((host,p))' in install

def test_readme_install_and_update_docs():
    readme = (ROOT / 'README.md').read_text()
    assert 'sudo bash -c' in readme
    assert 'sudo idontMonitor update' in readme
    assert 'sudo idontMonitor update-main' in readme


def test_app_and_operations_version_metadata():
    main=(ROOT/'app/main.py').read_text()
    ops=(ROOT/'app/ops.py').read_text()
    assert 'version="4.0.2"' in main
    assert 'API_VERSION = "4.0.2"' in ops

def test_v402_localization_and_navigation_cleanup():
    html=(ROOT/'static/index.html').read_text()
    locale=(ROOT/'locales/fa/messages.json').read_text()
    assert 'data-page="security"' in html
    assert 'Anti-DDoS Shield' in locale and 'محافظت ضد دیداس' in locale
    assert 'Anti-DDoS Command Center' in locale and 'مرکز فرماندهی ضد دیداس' in locale
    assert 'NEW</span>' not in html and 'new-badge' not in html
    assert 'v4.0.2' in html and 'v=4020' in html
