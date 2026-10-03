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
