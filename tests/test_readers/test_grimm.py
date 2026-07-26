"""Tests for GRIMM Optical Particle Counter reader."""
import pytest
from .base import BaseReaderTest


@pytest.mark.grimm
class TestGRIMMReader(BaseReaderTest):
    INSTRUMENT = 'GRIMM'


@pytest.mark.grimm
class TestGRIMMQC:
    """Unit tests for `GRIMM._QC`.

    There is no GRIMM fixture yet (the instrument is real, but no sample export
    is on hand), so the QC rules are exercised directly on a synthetic frame
    rather than through `RawDataReader`.
    """

    @staticmethod
    def _reader(tmp_path):
        from AeroViz.rawDataReader.script.GRIMM import Reader

        return Reader(path=tmp_path, qc=True, quiet=True)

    @staticmethod
    def _frame():
        import numpy as np
        import pandas as pd

        # A full clock hour on the 6-min native grid (10 rows) so the
        # completeness rule is satisfied; row 2 carries a negative count and
        # row 3 is entirely missing.
        idx = pd.date_range('2024-01-01 00:00', periods=10, freq='6min')
        base = [100.0, 120.0, 110.0, np.nan, 105.0, 108.0, 112.0, 99.0, 101.0, 103.0]
        df = pd.DataFrame(
            {0.25: base,
             0.28: [90.0, 95.0, -5.0, np.nan, 92.0, 93.0, 94.0, 91.0, 90.5, 92.5],
             0.30: [80.0, 85.0, 82.0, np.nan, 83.0, 84.0, 81.0, 80.5, 82.5, 83.5]},
            index=idx,
        )
        df.index.name = 'time'
        return df

    def test_produces_qc_flag(self, tmp_path):
        """The pipeline contract (rule R2) requires a QC_Flag column."""
        df = self._reader(tmp_path)._QC(self._frame())

        assert 'QC_Flag' in df.columns
        assert df['QC_Flag'].notna().all()

    def test_flags_negative_and_missing(self, tmp_path):
        df = self._reader(tmp_path)._QC(self._frame())
        flags = df['QC_Flag'].tolist()

        assert 'Negative Conc' in flags[2]
        assert 'No Data' in flags[3]

    def test_clean_rows_stay_valid(self, tmp_path):
        """A good row is not flagged — no invented concentration thresholds."""
        df = self._reader(tmp_path)._QC(self._frame())

        assert df['QC_Flag'].iloc[0] == 'Valid'
        assert df['QC_Flag'].iloc[1] == 'Valid'

    def test_values_are_not_destroyed(self, tmp_path):
        """QC judges but never masks — masking is the presentation layer's job."""
        original = self._frame()
        df = self._reader(tmp_path)._QC(original)

        assert df.loc[df.index[2], 0.28] == -5.0
