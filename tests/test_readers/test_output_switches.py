"""`save_csv` — the `{prefix}.csv` output is optional.

The returned DataFrame is the product; the CSV next to it is a convenience that
pipelines reading the frame directly (or, for SMPS/APS, the dN/dS/dV + stats
sidecars) never use. For a year of 6-minute SMPS data that file is ~40 MB
rewritten on every run, so it must be possible to switch off — while the
default stays on for everyone who relies on it.
"""
import shutil

import pytest

from AeroViz import RawDataReader

FIXTURE, SCENARIO = 'AE33', 'normal'
START, END = '2025-03-01', '2025-03-31'


@pytest.fixture
def dataset(raw_data_path, tmp_path):
    src = raw_data_path / FIXTURE / SCENARIO
    if not src.exists() or not any(src.iterdir()):
        pytest.skip(f'{FIXTURE}/{SCENARIO} fixture not available')
    dst = tmp_path / 'data'
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('*_outputs'))
    return dst


def _outputs(path):
    return path / f'{FIXTURE.lower()}_outputs'


def test_csv_written_by_default(dataset):
    RawDataReader(FIXTURE, dataset, start=START, end=END, reset=True, quiet=True)
    assert (_outputs(dataset) / f'output_{FIXTURE.lower()}.csv').is_file()


def test_save_csv_false_skips_the_file_but_not_the_frame(dataset):
    df = RawDataReader(FIXTURE, dataset, start=START, end=END, reset=True, quiet=True,
                       save_csv=False)
    assert not (_outputs(dataset) / f'output_{FIXTURE.lower()}.csv').exists()
    assert not df.empty                                   # the return value is untouched
    assert (_outputs(dataset) / 'report.json').is_file()  # other outputs unaffected


# --------------------------------------------------------------------------- #
# size_dist_outputs — which SMPS/APS sidecars are written
# --------------------------------------------------------------------------- #
@pytest.fixture
def smps_dataset(raw_data_path, tmp_path):
    src = raw_data_path / 'SMPS' / 'normal'
    if not src.exists() or not any(src.iterdir()):
        pytest.skip('SMPS/normal fixture not available')
    dst = tmp_path / 'smps'
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('*_outputs'))
    return dst


def _smps(path, **kw):
    # qc=False: the `normal` fixture is a short bench run that QC masks entirely,
    # and finalize_size_dist writes nothing for an all-NaN distribution. The raw
    # branch keeps the bins, which is all these file-switch tests need.
    return RawDataReader('SMPS', path, start='2025-02-01', end='2025-02-28', reset=True,
                         quiet=True, save_csv=False, qc=False, **kw)


def _sidecars(path):
    out = path / 'smps_outputs'
    return sorted(p.name.replace('output_smps', '') for p in out.glob('output_smps_*.csv'))


def test_all_sidecars_by_default(smps_dataset):
    _smps(smps_dataset)
    assert _sidecars(smps_dataset) == ['_dNdlogDp.csv', '_dSdlogDp.csv', '_dVdlogDp.csv', '_stats.csv']


def test_number_and_stats_only(smps_dataset):
    df = _smps(smps_dataset, size_dist_outputs=('number', 'stats'))
    assert _sidecars(smps_dataset) == ['_dNdlogDp.csv', '_stats.csv']
    assert not df.empty                    # the returned dN/dlogDp is unaffected


def test_number_only_skips_the_stats_computation_too(smps_dataset):
    _smps(smps_dataset, size_dist_outputs=['number'])
    assert _sidecars(smps_dataset) == ['_dNdlogDp.csv']


def test_append_stats_still_works_without_writing_them(smps_dataset):
    df = _smps(smps_dataset, size_dist_outputs=('number',), append_stats=True)
    assert 'total_num_all' in df.columns   # computed for the frame …
    assert '_stats.csv' not in _sidecars(smps_dataset)   # … but not written


def test_unknown_output_name_is_rejected_early(smps_dataset):
    with pytest.raises(ValueError, match='size_dist_outputs'):
        _smps(smps_dataset, size_dist_outputs=('number', 'mass'))
