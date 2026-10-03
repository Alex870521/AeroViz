"""Files a reader must skip quietly instead of logging a read error every run.

Both cases come from the TCLab Raw Data Repository, where the hourly pipeline
re-reads every folder and these files produced the same ERROR lines each hour:

- OCEC: RTCalc occasionally writes an ``*_LCRes.csv`` with the four header
  lines and no sample rows. The parser used to fall through to the date-format
  warning, whose ``.iloc[0]`` sample raised ``IndexError``.
- AE33: a station-side script drops ``AE33_<serial>_backfill_*.dat`` next to
  the daily logs — a ``#`` comment preamble plus pipe-delimited FETCH records,
  which the daily-log parser cannot read (``Number of passed names did not
  match number of header fields``).
"""
import shutil
from pathlib import Path

import pandas as pd
import pytest

from AeroViz import RawDataReader
from AeroViz.rawDataReader.script import AE33, OCEC

OCEC_HEADER_ONLY = (
    "Sunset Laboratory LOCAL CONDITION ACTUAL VOLUME OCEC Results \n"
    "Date Calculated:  01-19-2026\n"
    "Calculation Program version used: RTCalc808\n"
    "Sample ID,OC ugC/m^3 (Thermal/Optical),EC ugC/m^3 (Thermal/Optical),"
    "OC by diff ugC (TC-OptEC),OptEC ugC/m^3,TC ugC/m^3,Start Date/Time,"
    "Mid-time of Collection,Sample Volume - m^3 Local Condition\n"
)

AE33_BACKFILL = (
    "# AE33 backfill (raw FETCH pipe-delimited)\n"
    "# Serial: AE33-S05-00503\n"
    "# ID range: 1658268 - 1658268\n"
    "# Generated: 2026-10-02T21:29:40.545748\n"
    "# Fields: Serial|ID|StartTime|EndTime|RecordCount|MeasTime|<data fields>\n"
    "#\n"
    "AE33-S05-00503|1658268|10/2/2026 9:28:00 PM|10/2/2026 9:29:00 PM|13|9/21/2026 2:59:56 PM|"
    + "|".join(str(797926 + i) for i in range(68)) + "\n"
)


def test_ocec_header_only_results_file_is_skipped(tmp_path):
    f = tmp_path / 'SLI_OCEC_20260119_161952_LCRes.csv'
    f.write_text(OCEC_HEADER_ONLY)
    reader = OCEC.Reader(tmp_path, quiet=True)

    assert reader._raw_reader(f) is None     # no exception, nothing to parse


def test_ae33_backfill_dump_is_skipped(tmp_path):
    f = tmp_path / 'AE33_AE33-S05-00503_backfill_1658268-1658268_20261002_212940.dat'
    f.write_text(AE33_BACKFILL)
    reader = AE33.Reader(tmp_path, quiet=True)

    assert reader._raw_reader(f) is None


def test_ae33_daily_log_unaffected_by_backfill_neighbour(raw_data_path, tmp_path):
    """A backfill file sitting next to a real daily log changes nothing."""
    src = raw_data_path / 'AE33' / 'normal'
    if not src.exists() or not any(src.iterdir()):
        pytest.skip('AE33/normal fixture not available')
    clean = tmp_path / 'clean'
    mixed = tmp_path / 'mixed'
    shutil.copytree(src, clean, ignore=shutil.ignore_patterns('*_outputs'))
    shutil.copytree(src, mixed, ignore=shutil.ignore_patterns('*_outputs'))
    (mixed / 'AE33_AE33-S05-00503_backfill_1_20250305_000000.dat').write_text(AE33_BACKFILL)

    kw = dict(start='2025-03-01', end='2025-03-31', reset=True, quiet=True)
    a = RawDataReader('AE33', clean, **kw)
    b = RawDataReader('AE33', mixed, **kw)

    pd.testing.assert_frame_equal(a, b)
