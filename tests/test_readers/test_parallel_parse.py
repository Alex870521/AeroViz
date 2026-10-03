"""`parse_workers`: threaded parsing must give the same frame as sequential.

Files are merged strictly in name order whichever thread finishes first, and
the per-file parse cache is locked, so the only thing that may change is wall
time. Pinned on a two-file AE33 folder (the two fixture days) with and without
a cache, plus an SMPS folder (its reader keeps per-file side state).
"""
import shutil

import pandas as pd
import pytest

from AeroViz import RawDataReader

START, END = '2025-03-01', '2025-03-31'


@pytest.fixture
def ae33_two_days(raw_data_path, tmp_path):
    files = []
    for scenario in ('normal', 'status_errors'):
        d = raw_data_path / 'AE33' / scenario
        if d.is_dir():
            files += [p for p in d.iterdir() if p.is_file() and not p.name.startswith('.')]
    if len(files) < 2:
        pytest.skip('need two AE33 fixture files')
    data = tmp_path / 'ae33'
    data.mkdir()
    for f in files[:2]:
        shutil.copy2(f, data / f.name)
    return data


def _read(path, workers, **kw):
    return RawDataReader('AE33', path, start=START, end=END, reset=True, quiet=True,
                         parse_workers=workers, **kw)


def test_threaded_equals_sequential(ae33_two_days):
    seq = _read(ae33_two_days, 1)
    par = _read(ae33_two_days, 4)
    pd.testing.assert_frame_equal(seq, par)
    assert seq.attrs['n_files'] == par.attrs['n_files'] == 2


def test_threaded_with_parse_cache(ae33_two_days, tmp_path):
    cache = tmp_path / 'cache'
    cold = _read(ae33_two_days, 4, cache_dir=cache)
    assert (cold.attrs['parse_cache_hits'], cold.attrs['parse_cache_parsed']) == (0, 2)
    assert len(list(cache.rglob('*.pkl'))) == 2 and not list(cache.rglob('*.tmp'))
    warm = RawDataReader('AE33', ae33_two_days, start=START, end=END, quiet=True,
                         parse_workers=4, cache_dir=cache, reset='incremental')
    assert (warm.attrs['parse_cache_hits'], warm.attrs['parse_cache_parsed']) == (2, 0)
    pd.testing.assert_frame_equal(cold, warm)


def test_smps_side_state_survives_threads(raw_data_path, tmp_path):
    src = raw_data_path / 'SMPS' / 'normal'
    if not src.is_dir() or not any(src.iterdir()):
        pytest.skip('SMPS/normal fixture not available')
    data = tmp_path / 'smps'
    shutil.copytree(src, data, ignore=shutil.ignore_patterns('*_outputs'))
    kw = dict(start='2025-02-01', end='2025-02-28', reset=True, quiet=True, qc=False, save_csv=False)
    seq = RawDataReader('SMPS', data, parse_workers=1, **kw)
    par = RawDataReader('SMPS', data, parse_workers=4, **kw)
    pd.testing.assert_frame_equal(seq, par)
    cpc = lambda df: {k: v for k, v in df.attrs.items() if k.startswith('cpc_')}  # noqa: E731
    assert cpc(seq) == cpc(par)
