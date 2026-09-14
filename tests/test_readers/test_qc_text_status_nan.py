"""Text-mode status QC with blanks in the column (pandas 3).

Under pandas 3 a string column keeps missing values as NaN through
``astype(str)``; the token check then met a float and raised, and the rule
runner disabled the whole `Status Error` rule for the run. FS 2026: 212
`Incomplete scan` rows passed QC because *other* rows were blank.
"""
import numpy as np
import pandas as pd
import pytest

from AeroViz.rawDataReader.core.qc import QCFlagBuilder, QCRule, QualityControl

COL = 'Instrument Errors'


def _frame(values):
    idx = pd.date_range('2026-09-11 12:00', periods=len(values), freq='6min')
    return pd.DataFrame({COL: values, 'x': np.arange(len(values), dtype=float)}, index=idx)


@pytest.mark.parametrize('blank', [np.nan, None, ''])
def test_blank_status_is_never_an_error_with_whitelist(blank):
    df = _frame(['Normal Scan', blank, 'Incomplete scan', 'Connection reset,Incomplete scan'])
    m = QualityControl.filter_error_status(
        df, status_column=COL, status_type='text', ok_value='', ignored_values=['Normal Scan'])
    assert m.tolist() == [False, False, True, True]


@pytest.mark.parametrize('blank', [np.nan, None, ''])
def test_blank_status_is_never_an_error_without_whitelist(blank):
    df = _frame(['Normal Scan', blank, 'Incomplete scan'])
    m = QualityControl.filter_error_status(
        df, status_column=COL, status_type='text', ok_value='Normal Scan')
    assert m.tolist() == [False, False, True]


def test_pandas_string_dtype_column():
    """The dtype the readers actually produce under pandas 3."""
    df = _frame(['Normal Scan', None, 'Incomplete scan'])
    df[COL] = df[COL].astype('string')
    m = QualityControl.filter_error_status(
        df, status_column=COL, status_type='text', ok_value='', ignored_values=['Normal Scan'])
    assert m.tolist() == [False, False, True]


def test_rule_runner_reports_a_broken_rule_as_error(caplog):
    """A rule that raises is skipped -- and that must be logged at ERROR, the
    level pipelines actually keep."""
    import logging
    logger = logging.getLogger('test-qc-runner')
    builder = QCFlagBuilder(logger=logger)
    builder.add_rules([QCRule(name='Boom', condition=lambda df: 1 / 0)])
    with caplog.at_level(logging.ERROR, logger='test-qc-runner'):
        out = builder.apply(_frame(['Normal Scan']))
    assert (out['QC_Flag'] == 'Valid').all()
    assert any('Boom' in r.message and r.levelno == logging.ERROR for r in caplog.records)
