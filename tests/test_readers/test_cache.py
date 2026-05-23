"""Cache-layer behaviour for RawDataReader.

The pkl cache stores the *canonical* parsed frame (data over the files' own
coverage, not padded). The requested range and ``fill_missing`` are applied on
every call — including cache hits — and parse provenance is restored from the
cached frame's attrs. These tests pin that contract.
"""
import shutil

import pandas as pd
import pytest

from AeroViz import RawDataReader

FIXTURE = 'AE33'
SCENARIO = 'normal'
START, END = '2025-03-01', '2025-03-31'  # AE33 fixture data sits on 2025-03-05


@pytest.fixture
def cached_dataset(raw_data_path, tmp_path):
    """Copy the AE33 fixture to a temp dir so the pkl cache persists across
    calls within a test without polluting the shared fixture."""
    src = raw_data_path / FIXTURE / SCENARIO
    if not src.exists() or not any(src.iterdir()):
        pytest.skip(f'{FIXTURE}/{SCENARIO} fixture not available')
    dst = tmp_path / f'{FIXTURE}_{SCENARIO}'
    shutil.copytree(src, dst)
    return dst


def _read(path, **kwargs):
    return RawDataReader(FIXTURE, path, start=START, end=END, quiet=True, **kwargs)


def test_cache_hit_honors_fill_missing(cached_dataset):
    """A cache hit must respect this call's fill_missing, not the write-time one."""
    # First call writes the canonical cache (padded output here).
    df_first = _read(cached_dataset, reset=True, fill_missing=True)
    # Second call is a cache hit but asks for the clamped (subset) view.
    df_hit = _read(cached_dataset, reset=False, fill_missing=False)

    assert df_hit.attrs['fill_missing'] is False
    assert len(df_hit) < len(df_first)            # clamped, not the padded frame
    assert df_hit.index.max() <= df_first.index.max()


def test_cache_hit_restores_parse_metadata(cached_dataset):
    """n_files / raw_freq / freq_mixed survive a cache hit via df.attrs."""
    fresh = _read(cached_dataset, reset=True)
    hit = _read(cached_dataset, reset=False)

    assert hit.attrs.get('n_files') == fresh.attrs.get('n_files')
    assert hit.attrs.get('n_files') is not None
    assert hit.attrs.get('raw_freq') == fresh.attrs.get('raw_freq')
    assert hit.attrs.get('freq_mixed') == fresh.attrs.get('freq_mixed')


def test_cached_pkl_is_canonical_not_padded(cached_dataset):
    """The stored pkl holds only the data coverage, not the padded range."""
    _read(cached_dataset, reset=True, fill_missing=True)
    pkl = cached_dataset / f'{FIXTURE.lower()}_outputs' / f'_read_{FIXTURE.lower()}_qc.pkl'
    cached = pd.read_pickle(pkl)

    assert cached.attrs.get('cache_format') == 2
    # The request spans all of March; the canonical pkl must be clamped to the
    # data's actual coverage (~1 day on 2025-03-05), not padded to the request.
    requested_span = pd.Timestamp(END) - pd.Timestamp(START)
    assert (cached.index.max() - cached.index.min()) < pd.Timedelta(days=5)
    assert (cached.index.max() - cached.index.min()) < requested_span


def test_old_format_cache_is_reparsed(cached_dataset):
    """A pkl without the current cache_format marker is treated as stale."""
    _read(cached_dataset, reset=True)  # writes current-format cache
    out_dir = cached_dataset / f'{FIXTURE.lower()}_outputs'
    for name in (f'_read_{FIXTURE.lower()}_qc.pkl', f'_read_{FIXTURE.lower()}_raw.pkl'):
        pkl = out_dir / name
        stale = pd.read_pickle(pkl)
        stale.attrs.pop('cache_format', None)  # simulate a pre-v2 pkl
        stale.to_pickle(pkl)

    # Should not raise and should still return valid stamped data (re-parsed).
    df = _read(cached_dataset, reset=False)
    assert df.attrs.get('instrument') == FIXTURE
    assert df.attrs.get('n_files') is not None
