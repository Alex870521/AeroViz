"""Older Xact per-sample `*_output.txt` exports read into the same columns as
the `Sample_*.csv` path.

TCLab's TP_Xact 2023-12 / 2024-01 (IOP) exists only in this form; the reader's
`*.csv` glob matched nothing, so the read failed with "No files ... could be
read". Fixtures are three real TP files: two hourly samples and the 00:30
calibration check (Sample Type 2).
"""
import re
import shutil
from datetime import datetime

import pytest

from AeroViz import RawDataReader
from AeroViz.rawDataReader.script import Xact

NORMAL = '01_01_2024__00_00_05_output.txt'        # sample start 2023-12-31 22:00
CALIBRATION = '01_01_2024__00_30_04_output.txt'   # Sample Type 2


@pytest.fixture
def folder(raw_data_path, tmp_path):
    src = raw_data_path / 'Xact' / 'output_txt'
    if not src.exists():
        pytest.skip('Xact output_txt fixtures not available')
    dst = tmp_path / 'TP_Xact'
    shutil.copytree(src, dst)
    return dst


def test_sample_reads_into_the_csv_columns(folder):
    reader = Xact.Reader(folder, quiet=True)
    df = reader._raw_reader(folder / NORMAL)

    assert list(df.index) == [datetime(2023, 12, 31, 22)]
    expected = set(Xact.Reader.ELEMENTS) | {f'{e}_uncert' for e in Xact.Reader.ELEMENTS} \
        | set(Xact.Reader.ENV_COLUMNS)
    assert set(df.columns) <= expected
    for col in ('S', 'S_uncert', 'Fe', 'Pb', 'FLOW_ACT', 'VOLUME', 'SAMPLE_TIME', 'SAMPLE_TYPE'):
        assert col in df.columns

    row = df.iloc[0]
    assert row['S'] == pytest.approx(2160.5041)          # the Concentration column
    assert row['S_uncert'] == pytest.approx(75.8889)
    assert row['VOLUME'] == pytest.approx(983.27)
    assert reader._sample_time == 60


def test_concentration_is_mass_over_volume(folder):
    """What makes it the same ng/m³ as the CSV's `(ng/m3)` columns."""
    text = (folder / NORMAL).read_text()
    mass = float(re.search(r'^Fe,26,([0-9.]+),', text, re.M).group(1))
    volume_m3 = float(re.search(r'Volume = ,([0-9.]+)', text).group(1)) / 1000
    df = Xact.Reader(folder, quiet=True)._raw_reader(folder / NORMAL)
    assert df['Fe'].iloc[0] == pytest.approx(mass / volume_m3, rel=1e-4)


def test_calibration_sample_is_dropped(folder):
    df = Xact.Reader(folder, quiet=True)._raw_reader(folder / CALIBRATION)
    assert df is not None and df.empty


def test_folder_of_output_txt_is_readable(folder):
    df = RawDataReader('Xact', folder, start=datetime(2023, 12, 31), end=datetime(2024, 1, 1, 23),
                       reset=True, qc=False, mean_freq='1h', save_pkl=False,
                       save_intermediate_csv=False, save_report=False, quiet=True, log_level='ERROR')
    assert df['S'].dropna().index.tolist() == [datetime(2023, 12, 31, 22), datetime(2023, 12, 31, 23)]
