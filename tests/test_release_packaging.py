from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def test_version_is_200_everywhere():
    assert (ROOT / 'VERSION').read_text().strip() == '2.0.0'
    install = (ROOT / 'install.sh').read_text()
    assert 'VERSION="2.0.0"' in install
    assert 'VERSION="1.9.9"' not in install

def test_updater_supports_tar_and_main():
    updater = (ROOT / 'scripts/idontmonitor-update').read_text()
    assert 'tarfile.open' in updater
    assert 'releases/latest' in updater
    assert 'apply-main' in updater
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
