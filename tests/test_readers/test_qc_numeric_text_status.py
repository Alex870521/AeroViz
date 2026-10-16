"""Text-mode status QC on a column the reader has already made numeric.

AIM 11.x writes `Communication Status` as '0' when healthy. The reader's
to_numeric pass turns that into a number, and the NaN rows the time grid pads
in make it float64, so the text check saw '0.0' and flagged every real scan.
TP 2024-01/02: 6,092 of 6,092 scans were `Status Error`, the only `Valid` rows
were empty padding, and a QC'd read kept 0 hours out of 630.
"""
import numpy as np
import pandas as pd
import pytest

from AeroViz.rawDataReader.core import QCFlagBuilder
from AeroViz.rawDataReader.core.qc import QualityControl

FLAG = QCFlagBuilder.FLAG_COLUMN
COL = 'Communication Status'


def _frame(values):
    idx = pd.date_range('2024-01-01', periods=len(values), freq='6min')
    return pd.DataFrame({COL: values}, index=idx)


@pytest.mark.parametrize('ignored', [None, ['Low aerosol flow', 'Neutralizer not active']])
def test_float_padded_zero_is_ok(ignored):
    df = _frame([0.0, np.nan, 3.0, 0.0])
    assert df[COL].dtype == 'float64'
    m = QualityControl.filter_error_status(
        df, status_column=COL, status_type='text', ok_value='0', ignored_values=ignored)
    assert m.tolist() == [False, False, True, False]


def test_integer_column_still_works():
    m = QualityControl.filter_error_status(
        _frame([0, 3, 0]), status_column=COL, status_type='text', ok_value='0')
    assert m.tolist() == [False, True, False]


def test_non_integral_number_is_not_rounded_into_ok():
    m = QualityControl.filter_error_status(
        _frame([0.5, 0.0]), status_column=COL, status_type='text', ok_value='0')
    assert m.tolist() == [True, False]


@pytest.mark.smps
def test_smps_aim11_scans_survive_qc_after_grid_padding(tmp_path):
    """The shape `_QC` actually receives: AIM 11.x statuses, a padded empty row,
    and `Communication Status` already coerced to float."""
    from AeroViz.rawDataReader.script.SMPS import Reader

    idx = pd.date_range('2024-01-01', periods=3, freq='6min')
    df = pd.DataFrame({
        11.8: [3000.0, np.nan, 3100.0],
        15.0: [3500.0, np.nan, 3600.0],
        20.0: [4000.0, np.nan, 4100.0],
        'Detector Status': ['Normal Scan', np.nan, 'Normal Scan'],
        'Classifier Errors': ['Normal Scan', np.nan, 'Normal Scan'],
        COL: [0.0, np.nan, 0.0],
        'Neutralizer Status': ['ON', np.nan, 'ON'],
    }, index=idx)

    out = Reader(path=tmp_path, qc=True, quiet=True,
                 ignored_status_errors=['Low aerosol flow', 'Neutralizer not active'])._QC(df)

    assert not out[FLAG].str.contains('Status Error').any()
