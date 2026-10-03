"""`output_split` and change-aware writes of the CSV products.

`_write_product` is the single writer for `{prefix}.csv` and the SMPS/APS
sidecars: it lays files out per `output_split`, rewrites a file only when its
bytes would differ, and clears the other layout's files when the layout
changes. Pinned at the helper level with a frame that spans a year boundary,
plus one real read through the AE33 fixture.
"""
import shutil

import numpy as np
import pandas as pd
import pytest

from AeroViz import RawDataReader
from AeroViz.rawDataReader.script import AE33


def _frame():
    idx = pd.date_range('2025-12-30', '2026-01-02 23:00', freq='1h')
    return pd.DataFrame({'a': np.arange(len(idx), dtype=float), 'b': 1.0}, index=idx)


def _reader(tmp_path, **kw):
    return AE33.Reader(tmp_path, quiet=True, **kw)


def _names(folder, stem):
    return sorted(p.name for p in folder.glob(f'{stem}*.csv'))


def test_month_split_names_and_round_trip(tmp_path):
    r = _reader(tmp_path, output_split='month')
    df = _frame()
    written = r._write_product('x', df)
    out = r._output_folder
    assert _names(out, 'x') == ['x_2025-12.csv', 'x_2026-01.csv'] == sorted(p.name for p in written)
    back = pd.concat([pd.read_csv(out / n, index_col=0, parse_dates=True) for n in _names(out, 'x')])
    pd.testing.assert_frame_equal(back, df, check_freq=False)


def test_year_split(tmp_path):
    r = _reader(tmp_path, output_split='year')
    r._write_product('x', _frame())
    assert _names(r._output_folder, 'x') == ['x_2025.csv', 'x_2026.csv']


def test_unchanged_periods_are_not_rewritten(tmp_path):
    r = _reader(tmp_path, output_split='month')
    df = _frame()
    assert len(r._write_product('x', df)) == 2
    assert r._write_product('x', df) == []                   # nothing changed → nothing written
    df.loc['2026-01-01 05:00', 'a'] = 999.0                   # one month changes
    assert [p.name for p in r._write_product('x', df)] == ['x_2026-01.csv']


def test_switching_layout_removes_the_other_layout(tmp_path):
    out = _reader(tmp_path, output_split='month')
    out._write_product('x', _frame())
    one = _reader(tmp_path, output_split='none')
    one._write_product('x', _frame())
    assert _names(one._output_folder, 'x') == ['x.csv']
    back = _reader(tmp_path, output_split='month')
    back._write_product('x', _frame())
    assert _names(back._output_folder, 'x') == ['x_2025-12.csv', 'x_2026-01.csv']


def test_single_layout_is_change_aware_too(tmp_path):
    r = _reader(tmp_path)
    df = _frame()
    assert len(r._write_product('x', df)) == 1
    assert r._write_product('x', df) == []


def test_invalid_value_rejected_in_factory(tmp_path):
    with pytest.raises(ValueError, match='output_split'):
        RawDataReader('AE33', tmp_path, output_split='week')


def test_real_read_month_split(raw_data_path, tmp_path):
    src = raw_data_path / 'AE33' / 'normal'
    if not src.exists() or not any(src.iterdir()):
        pytest.skip('AE33/normal fixture not available')
    data = tmp_path / 'ae33'
    shutil.copytree(src, data, ignore=shutil.ignore_patterns('*_outputs'))
    df = RawDataReader('AE33', data, start='2025-03-01', end='2025-03-31', reset=True, quiet=True,
                       output_split='month')
    out = data / 'ae33_outputs'
    assert (out / 'output_ae33_2025-03.csv').is_file()
    assert not (out / 'output_ae33.csv').exists()
    assert (out / 'report.json').is_file()                    # report stays whole
    assert len(pd.read_csv(out / 'output_ae33_2025-03.csv', index_col=0)) == len(df)
