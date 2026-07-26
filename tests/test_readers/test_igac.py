"""Tests for IGAC (Ion Chromatograph) reader."""
import pytest
from .base import BaseReaderTest


@pytest.mark.igac
class TestIGACReader(BaseReaderTest):
    INSTRUMENT = 'IGAC'


@pytest.mark.igac
class TestIGACMetaWiring:
    """`IGAC` reads its detection limits and measurement ranges from `meta`.

    No IGAC fixture is available, so `_QC` is exercised directly on a synthetic
    frame. What matters here is that the vendor spec in
    `config/supported_instruments.py` is the single source of truth — there used
    to be a second, disagreeing copy as a class attribute.
    """

    @staticmethod
    def _reader(tmp_path):
        from AeroViz.rawDataReader.script.IGAC import Reader

        return Reader(path=tmp_path, qc=True, quiet=True)

    def test_mdl_comes_from_config(self, tmp_path):
        from AeroViz.rawDataReader.config.supported_instruments import meta

        reader = self._reader(tmp_path)
        expected = {k: v for k, v in meta['IGAC']['MDL'].items() if v is not None}

        assert reader.MDL == expected
        # Unmeasured species (None in the spec) are dropped, not treated as 0.
        for species in ('HF', 'F-', 'PO43-'):
            assert species not in reader.MDL

    def test_mr_comes_from_config(self, tmp_path):
        from AeroViz.rawDataReader.config.supported_instruments import meta

        reader = self._reader(tmp_path)
        expected = {k: v for k, v in meta['IGAC']['MR'].items() if v is not None}

        assert reader.MR == expected

    @staticmethod
    def _frame():
        import pandas as pd

        idx = pd.date_range('2024-01-01', periods=3, freq='1h')
        # Row 1: ordinary. Row 2: SO42- above its measurement range (300).
        # Row 3: NH4+ below its MDL (0.08) but otherwise fine.
        df = pd.DataFrame(
            {'NH4+': [2.0, 2.1, 0.01],
             'SO42-': [5.0, 999.0, 4.8],
             'NO3-': [3.0, 3.1, 2.9],
             'Na+': [0.5, 0.6, 0.55],
             'Cl-': [0.4, 0.45, 0.42],
             'HNO3': [1.0, 1.1, 1.05],
             'NH3': [2.0, 2.2, 2.1]},
            index=idx,
        )
        df.index.name = 'time'
        return df

    def test_gases_are_kept(self, tmp_path):
        """Gas species in the spec used to be dropped: IGAC is a gas *and*
        aerosol monitor, and the config lists MDLs for HNO3 / NH3 / HCl / ..."""
        df = self._reader(tmp_path)._QC(self._frame())

        assert 'HNO3' in df.columns
        assert 'NH3' in df.columns

    def test_above_mr_is_flagged(self, tmp_path):
        df = self._reader(tmp_path)._QC(self._frame())

        assert 'Above MR' in df['QC_Flag'].iloc[1]

    def test_below_mdl_is_not_flagged(self, tmp_path):
        """A below-MDL value is a low measurement, not a broken row — flagging it
        would NaN every other species measured in the same hour."""
        df = self._reader(tmp_path)._QC(self._frame())

        assert 'Below MDL' not in df['QC_Flag'].iloc[2]

    def test_below_mdl_is_reported_per_column(self, tmp_path):
        """It is a diagnostic instead: counted per species."""
        reader = self._reader(tmp_path)
        frame = self._frame()
        report = reader.log_below_mdl(frame, reader.MDL)

        nh4 = report.set_index('column').loc['NH4+']
        assert nh4['below'] == 1
        assert nh4['measured'] == 3
