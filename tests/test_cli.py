"""The `aeroviz` command: thin argparse front over the Python API."""
import shutil

import pandas as pd
import pytest

from AeroViz.cli import main, build_parser


def test_instruments_lists_readers(capsys):
    assert main(['instruments']) == 0
    out = capsys.readouterr().out
    assert 'SMPS' in out and 'AE33' in out and '*.dat' in out


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as e:
        main(['--version'])
    assert e.value.code == 0 and capsys.readouterr().out.startswith('AeroViz')


def test_incremental_requires_cache_dir(tmp_path):
    with pytest.raises(SystemExit, match='--cache-dir'):
        main(['read', 'AE33', str(tmp_path), '--incremental'])


def test_unknown_out_suffix_is_refused(tmp_path):
    from AeroViz.cli import _write_frame
    with pytest.raises(SystemExit, match='suffix'):
        _write_frame(pd.DataFrame({'x': [1]}), tmp_path / 'x.xlsx')


@pytest.fixture
def ae33_dir(raw_data_path, tmp_path):
    src = raw_data_path / 'AE33' / 'normal'
    if not src.exists() or not any(src.iterdir()):
        pytest.skip('AE33/normal fixture not available')
    dst = tmp_path / 'NZ_AE33'
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('*_outputs'))
    return dst


def test_read_writes_csv_and_report_and_prints_summary(ae33_dir, tmp_path, capsys):
    out, rep = tmp_path / 'o' / 'ae33.csv', tmp_path / 'o' / 'ae33.md'
    code = main(['read', 'AE33', str(ae33_dir), '--start', '2025-03-01', '--end', '2025-03-31',
                 '--freq', '1h', '--reset', '--quiet', '--out', str(out), '--report', str(rep)])
    assert code == 0
    text = capsys.readouterr().out
    assert text.startswith('NZ AE33:') and 'rates:' in text and 'coverage:' in text
    df = pd.read_csv(out, index_col=0, parse_dates=True)
    assert 'eBC' in df.columns and len(df) == 744
    assert rep.read_text(encoding='utf-8').startswith('# NZ AE33')


def test_read_no_qc_has_no_rates(ae33_dir, capsys):
    main(['read', 'AE33', str(ae33_dir), '--start', '2025-03-01', '--end', '2025-03-31', '--reset',
          '--quiet', '--no-qc'])
    assert 'rates:' not in capsys.readouterr().out


def test_read_to_netcdf(ae33_dir, tmp_path):
    pytest.importorskip('netCDF4')
    out = tmp_path / 'ae33.nc'
    main(['read', 'AE33', str(ae33_dir), '--start', '2025-03-01', '--end', '2025-03-31', '--reset',
          '--quiet', '--out', str(out)])
    from AeroViz import read_netcdf
    assert read_netcdf(out).attrs['instrument'] == 'AE33'


def test_read_to_parquet(ae33_dir, tmp_path):
    pytest.importorskip('pyarrow')
    out = tmp_path / 'ae33.parquet'
    main(['read', 'AE33', str(ae33_dir), '--start', '2025-03-01', '--end', '2025-03-31', '--reset',
          '--quiet', '--out', str(out)])
    assert 'eBC' in pd.read_parquet(out).columns


def test_inventory_prints_table_and_writes_json(ae33_dir, tmp_path, capsys):
    out = tmp_path / 'inv.json'
    assert main(['inventory', 'AE33', str(ae33_dir), '--out', str(out)]) == 0
    text = capsys.readouterr().out
    assert 'file' in text and 'n_files' in text
    import json
    data = json.loads(out.read_text())
    assert data['summary']['n_files'] == len(data['files']) > 0


def test_parser_help_mentions_every_command():
    h = build_parser().format_help()
    assert all(c in h for c in ('read', 'inventory', 'instruments'))
