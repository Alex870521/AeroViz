"""Per-file parse cache (`cache_dir` + `reset='incremental'`).

The contract: an incremental read returns the *same frame* as a cold read,
while parsing only what changed. Everything else — QC, gridding, resampling —
runs on the full series either way, so the only observable differences are
which files were parsed (``df.attrs['parse_cache_*']``) and what sits in the
cache folder afterwards.

Fixtures: the two AE33 scenarios are different days (2025-03-04 / 03-05) of the
same instrument, which gives a two-file folder; SMPS `normal` carries CPC
detector fields in its preamble, which must survive a cache hit.
"""
import os
import shutil

import pandas as pd
import pytest

from AeroViz import RawDataReader

START, END = '2025-03-01', '2025-03-31'


def _ae33_files(raw_data_path):
    files = []
    for scenario in ('normal', 'status_errors'):
        d = raw_data_path / 'AE33' / scenario
        if d.is_dir():
            files += [p for p in d.iterdir() if p.is_file() and not p.name.startswith('.')]
    return files


@pytest.fixture
def two_day_folder(raw_data_path, tmp_path):
    files = _ae33_files(raw_data_path)
    if len(files) < 2:
        pytest.skip('need two AE33 fixture files')
    data = tmp_path / 'AE33_two_days'
    data.mkdir()
    for f in files[:2]:
        shutil.copy2(f, data / f.name)
    return data


@pytest.fixture
def cache_dir(tmp_path):
    return tmp_path / 'parse-cache'


def _read(path, cache_dir, reset, **kw):
    return RawDataReader('AE33', path, start=START, end=END, quiet=True,
                         cache_dir=cache_dir, reset=reset, **kw)


def _entries(cache_dir):
    return sorted(cache_dir.rglob('*.pkl'))


def _same(a, b):
    pd.testing.assert_frame_equal(a, b)


def test_incremental_equals_cold_and_reuses_every_file(two_day_folder, cache_dir):
    cold = _read(two_day_folder, cache_dir, reset=True)
    assert (cold.attrs['parse_cache_hits'], cold.attrs['parse_cache_parsed']) == (0, 2)
    assert len(_entries(cache_dir)) == 2

    warm = _read(two_day_folder, cache_dir, reset='incremental')
    assert (warm.attrs['parse_cache_hits'], warm.attrs['parse_cache_parsed']) == (2, 0)
    _same(cold, warm)


def test_changed_file_is_parsed_again_others_reused(two_day_folder, cache_dir):
    cold = _read(two_day_folder, cache_dir, reset=True)
    victim = sorted(two_day_folder.iterdir())[0]
    st = victim.stat()
    os.utime(victim, ns=(st.st_atime_ns, st.st_mtime_ns + 60 * 10**9))   # same bytes, new mtime

    warm = _read(two_day_folder, cache_dir, reset='incremental')
    assert (warm.attrs['parse_cache_hits'], warm.attrs['parse_cache_parsed']) == (1, 1)
    assert len(_entries(cache_dir)) == 2            # the stale entry was pruned
    _same(cold, warm)


def test_new_file_is_parsed_and_added(raw_data_path, tmp_path, cache_dir):
    files = _ae33_files(raw_data_path)
    if len(files) < 2:
        pytest.skip('need two AE33 fixture files')
    data = tmp_path / 'growing'
    data.mkdir()
    shutil.copy2(files[0], data / files[0].name)
    _read(data, cache_dir, reset=True)
    assert len(_entries(cache_dir)) == 1

    shutil.copy2(files[1], data / files[1].name)        # the station uploaded a new day
    grown = _read(data, cache_dir, reset='incremental')
    assert (grown.attrs['parse_cache_hits'], grown.attrs['parse_cache_parsed']) == (1, 1)
    assert len(_entries(cache_dir)) == 2
    _same(grown, _read(data, None, reset=True))


def test_deleted_file_drops_out_and_its_entry_is_pruned(two_day_folder, cache_dir):
    _read(two_day_folder, cache_dir, reset=True)
    gone = sorted(two_day_folder.iterdir())[1]
    gone.unlink()

    shrunk = _read(two_day_folder, cache_dir, reset='incremental')
    assert (shrunk.attrs['parse_cache_hits'], shrunk.attrs['parse_cache_parsed']) == (1, 0)
    assert len(_entries(cache_dir)) == 1
    _same(shrunk, _read(two_day_folder, None, reset=True))


def test_reset_true_rebuilds_the_cache(two_day_folder, cache_dir):
    _read(two_day_folder, cache_dir, reset=True)
    again = _read(two_day_folder, cache_dir, reset=True)
    assert (again.attrs['parse_cache_hits'], again.attrs['parse_cache_parsed']) == (0, 2)


def test_incremental_without_cache_dir_behaves_like_true(two_day_folder):
    cold = _read(two_day_folder, None, reset=True)
    inc = _read(two_day_folder, None, reset='incremental')
    assert 'parse_cache_hits' not in inc.attrs
    _same(cold, inc)


def test_cache_is_namespaced_per_source_folder(raw_data_path, tmp_path, cache_dir):
    files = _ae33_files(raw_data_path)
    if len(files) < 2:
        pytest.skip('need two AE33 fixture files')
    a, b = tmp_path / 'site_a', tmp_path / 'site_b'
    a.mkdir(); b.mkdir()
    shutil.copy2(files[0], a / files[0].name)
    shutil.copy2(files[1], b / files[1].name)
    _read(a, cache_dir, reset=True)
    _read(b, cache_dir, reset=True)
    assert len(_entries(cache_dir)) == 2
    # Re-reading one folder must not prune the other's entry.
    _read(a, cache_dir, reset='incremental')
    assert len(_entries(cache_dir)) == 2


def test_smps_detector_fields_survive_a_cache_hit(raw_data_path, tmp_path, cache_dir):
    src = raw_data_path / 'SMPS' / 'normal'
    if not src.is_dir() or not any(src.iterdir()):
        pytest.skip('SMPS/normal fixture not available')
    data = tmp_path / 'SMPS'
    shutil.copytree(src, data, ignore=shutil.ignore_patterns('*_outputs'))
    kw = dict(start='2025-02-01', end='2025-02-28', quiet=True, cache_dir=cache_dir)

    cold = RawDataReader('SMPS', data, reset=True, **kw)
    warm = RawDataReader('SMPS', data, reset='incremental', **kw)

    cpc = lambda df: {k: v for k, v in df.attrs.items() if k.startswith('cpc_')}  # noqa: E731
    assert warm.attrs['parse_cache_hits'] == 1
    assert cpc(warm) == cpc(cold)
    _same(cold, warm)
