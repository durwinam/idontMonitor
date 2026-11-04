from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ops_v320', ROOT / 'app' / 'ops.py')
ops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ops)


def test_bounded_disk_scan_counts_files_and_skips_symlinks(tmp_path):
    (tmp_path / 'one.bin').write_bytes(b'x' * 123)
    child = tmp_path / 'nested'
    child.mkdir()
    (child / 'two.bin').write_bytes(b'y' * 77)
    outside = tmp_path.parent / 'outside.bin'
    outside.write_bytes(b'z' * 999)
    try:
        (tmp_path / 'link').symlink_to(outside)
    except OSError:
        pass
    total, entries, truncated = ops._bounded_dir_size(tmp_path)
    assert total == 200
    assert entries >= 2
    assert truncated is False


def test_backpack_and_ctunnel_canonical_paths_are_present():
    source = (ROOT / 'app' / 'ops.py').read_text()
    assert '/etc/ctunnel/state.json' in source
    assert 'REMOTE_IP' in source
    assert 'Path("/etc/backpack") / f"{match.group(1)}.metrics.json"' in source
    assert 'tomllib.loads' in source
    assert 'remote_addr' in source


def test_ram_inventory_is_grouped_by_systemd_cgroup():
    rows = ops._process_inventory()
    assert isinstance(rows, list)
    for row in rows:
        assert 'service' in row
        assert isinstance(row['ram_bytes'], int) and row['ram_bytes'] >= 0
