"""The `Truncated Scan` rule: counts only in the smallest bins, nothing above.

Shape taken from FS, 2026-09-11 12:54: 11.8-14 nm carrying 1.6e4-1.2e5
dN/dlogDp, every bin from 20 nm up exactly 0. It slipped through every other
rule (total inside range, no bin over the CPC ceiling), so it has its own.
Closed-form frames, no fixture data.
"""
import numpy as np
import pandas as pd

from AeroViz.rawDataReader.script.SMPS import Reader as SMPSReader

DP = [11.8, 12.2, 12.6, 13.1, 13.6, 20.2, 50.0, 100.0, 300.0, 593.5]


def _frame(rows):
    return pd.DataFrame(rows, columns=DP, dtype=float,
                        index=pd.date_range('2026-09-11 12:48', periods=len(rows), freq='6min'))


def _mask(df):
    return SMPSReader._truncated_scan_mask(df, SMPSReader.TRUNCATED_SCAN_FACTOR)


def test_fs_0911_1254_is_flagged_and_neighbours_are_not():
    df = _frame([
        [1590, 1801, 1498, 1947, 2140, 3000, 9000, 12000, 4000, 100],
        [16059, 42343, 77981, 122069, 118954, 0, 0, 0, 0, 0],
        [1419, 1651, 1633, 1770, 1904, 2800, 9500, 11000, 4200, 90],
    ])
    assert _mask(df).tolist() == [False, True, False]


def test_nucleation_burst_keeps_particles_above_20nm_and_is_kept():
    df = _frame([[50000, 60000, 40000, 20000, 9000, 3000, 800, 400, 100, 5]])
    assert not _mask(df).any()


def test_nan_above_counts_as_zero_but_an_all_zero_scan_is_not_truncated():
    df = _frame([
        [500, 600, 700, 800, 900, np.nan, np.nan, np.nan, np.nan, np.nan],
        [0] * 10,
        [np.nan] * 10,
    ])
    assert _mask(df).tolist() == [True, False, False]


def test_cutoff_follows_the_grid():
    """Factor 2 on the standard grid is 23.6 nm: the 20.2 nm bin is *below* the
    cutoff, so counts there alone still make a truncated scan."""
    df = _frame([[100, 100, 100, 100, 100, 500, 0, 0, 0, 0]])
    assert _mask(df).tolist() == [True]


def test_rule_is_wired_into_qc(tmp_path):
    """The rule name must reach the QC builder, or the helper is dead code."""
    src = (SMPSReader.__module__)
    import inspect
    assert "name='Truncated Scan'" in inspect.getsource(SMPSReader._QC)
