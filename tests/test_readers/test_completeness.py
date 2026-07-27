"""`Insufficient` — representativeness, not validity.

The rule asks whether an hour holds enough data for an *average over that hour*
to mean anything. The readings themselves are fine either way, which is why it
is advisory: it must not delete data.

It also used to be measured against a full hour regardless of how much of that
hour the read actually covered, so the first and last hour of every read were
condemned no matter how well the instrument ran. Users reported exactly that
symptom — the head and tail of their data disappearing.
"""
import pandas as pd
import pytest

from AeroViz.rawDataReader.core import QCFlagBuilder
from AeroViz.rawDataReader.core.qc import QualityControl

FLAG = QCFlagBuilder.FLAG_COLUMN
INVALID = QCFlagBuilder.INVALID_COLUMN


class TestCoverageScaling:
    """The expectation follows how much of each hour the data spans."""

    @staticmethod
    def _frame(start, periods, freq='2min'):
        idx = pd.date_range(start, periods=periods, freq=freq)
        return pd.DataFrame({'v': 50.0}, index=idx)

    def test_partial_first_hour_is_not_condemned(self):
        """A read starting at 10:54 has six minutes in the 10 o'clock hour. It
        cannot fill an hour it never had."""
        df = self._frame('2025-11-17 10:54', 12)

        mask = QualityControl.hourly_completeness_QC(df, freq='2min')

        assert not mask.any(), 'a complete 22-minute read has nothing missing'

    def test_partial_last_hour_is_not_condemned(self):
        df = self._frame('2025-11-17 10:00', 41)   # 10:00 -> 11:20

        mask = QualityControl.hourly_completeness_QC(df, freq='2min')

        assert not mask.any()

    def test_interior_gap_is_still_caught(self):
        """The check must not be weakened for hours that *could* have been full."""
        df = self._frame('2025-11-17 10:54', 104)  # ~3.5 h
        outage = (df.index >= '2025-11-17 12:10') & (df.index < '2025-11-17 12:56')
        df.loc[outage, 'v'] = float('nan')

        mask = QualityControl.hourly_completeness_QC(df, freq='2min')

        flagged_hours = set(df.index[mask].floor('1h'))
        assert flagged_hours == {pd.Timestamp('2025-11-17 12:00')}

    def test_sparse_interior_hour_against_the_true_period(self):
        """A full hour holding a third of its points is still insufficient."""
        idx = pd.date_range('2025-11-17 10:00', periods=10, freq='6min')
        df = pd.DataFrame({'v': 50.0}, index=idx)

        assert not QualityControl.hourly_completeness_QC(df, freq='6min').any()
        assert QualityControl.hourly_completeness_QC(df, freq='2min').all()

    def test_empty_columns_are_ignored(self):
        """An unconnected optional sensor says nothing about any hour, but used to
        mark every hour insufficient for every other column too."""
        idx = pd.date_range('2025-11-17 10:00', periods=30, freq='2min')
        df = pd.DataFrame({'v': 50.0, 'unconnected_sensor': float('nan')}, index=idx)

        assert not QualityControl.hourly_completeness_QC(df, freq='2min').any()

    def test_empty_frame(self):
        empty = pd.DataFrame({'v': []}, index=pd.DatetimeIndex([]))

        assert not QualityControl.hourly_completeness_QC(empty, freq='2min').any()


@pytest.mark.aps
class TestInsufficientIsAdvisory:
    """It records a caveat; it must never delete the measurement."""

    @staticmethod
    def _reader(tmp_path, **kw):
        from AeroViz.rawDataReader.script.APS import Reader

        return Reader(path=tmp_path, qc=True, quiet=True, **kw)

    @staticmethod
    def _sparse():
        """One hour holding 4 of its 30 possible 2-minute points."""
        idx = pd.date_range('2025-11-17 10:00', periods=30, freq='2min')
        df = pd.DataFrame({0.542: 50.0, 1.0: 40.0}, index=idx)
        df.iloc[4:] = float('nan')
        return df

    def test_flag_is_raised(self, tmp_path):
        reader = self._reader(tmp_path)
        reader._resolved_freq = '2min'

        out = reader._QC(self._sparse())

        assert out[FLAG].str.contains('Insufficient').any()

    def test_but_the_rows_are_kept(self, tmp_path):
        reader = self._reader(tmp_path)
        reader._resolved_freq = '2min'

        out = reader._QC(self._sparse())
        sparse_rows = out[FLAG].str.contains('Insufficient')

        assert not out.loc[sparse_rows, INVALID].any(), (
            'a sparse hour is a representativeness caveat, not a broken reading')

    def test_can_be_promoted_per_run(self, tmp_path):
        """Anyone who wants the old strictness asks for it."""
        reader = self._reader(tmp_path, flag_severity={'Insufficient': 'error'})
        reader._resolved_freq = '2min'

        out = reader._QC(self._sparse())
        sparse_rows = out[FLAG].str.contains('Insufficient')

        assert out.loc[sparse_rows, INVALID].all()


@pytest.mark.aps
def test_short_read_survives_end_to_end(raw_data_path, tmp_path):
    """The reported symptom: a 22-minute APS file used to lose every row —
    flagged for not filling two clock hours it only partly covered."""
    import shutil

    from AeroViz import RawDataReader

    src = raw_data_path / 'APS' / 'normal'
    if not src.exists():
        pytest.skip('APS fixture not available')
    dst = tmp_path / 'APS'
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('aps_outputs'))

    df = RawDataReader('APS', dst, reset=True, quiet=True, fill_missing=False)
    bins = [c for c in df.columns if isinstance(c, float)]

    assert df[bins].notna().any(axis=1).all(), 'every row should survive'
    assert df.attrs['total_rate'] == 100.0
