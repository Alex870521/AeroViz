"""
Tests for Xact 625i XRF Heavy Metals reader.

Test Scenarios:
- normal/: Merged Xact data with ALARM=0 and Type=1 (normal sampling)
- status_errors/: Data with ALARM=203 (Upscale Nb Warning)
"""
from datetime import datetime

import pandas as pd
import pytest

from .base import BaseReaderTest


@pytest.mark.xact
class TestXactReader(BaseReaderTest):
    INSTRUMENT = 'Xact'

    EXPECTED_COLUMNS = ['Fe', 'Zn', 'Pb', 'S', 'K', 'Ca']

    # Fixture spans 2025-01-01 (single day)
    DATE_RANGE_START = datetime(2025, 1, 1)
    DATE_RANGE_END = datetime(2025, 1, 7, 23, 59, 59)

    def test_raw_data_has_all_columns(self, data_path, date_range, temp_output_dir):
        """Test that raw pickle preserves all original columns."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        self.read_data(normal_path, date_range)

        output_dir = normal_path / 'xact_outputs'
        raw_pkl = output_dir / '_read_xact_raw.pkl'
        if raw_pkl.exists():
            raw_data = pd.read_pickle(raw_pkl)
            # Should have element columns
            for col in ['Fe', 'Zn', 'Pb']:
                assert col in raw_data.columns, f"{col} not found in raw data"

            # Should have uncertainty columns
            uncert_cols = [c for c in raw_data.columns if '_uncert' in c]
            assert len(uncert_cols) > 0, "Expected uncertainty columns in raw data"

            # Should have environmental columns
            env_cols = [c for c in raw_data.columns if c in ['AT', 'BP', 'RH', 'FLOW_25', 'ALARM']]
            assert len(env_cols) > 0, "Expected environmental columns in raw data"

    def test_uncertainty_columns(self, data_path, date_range, temp_output_dir):
        """Test that uncertainty columns are present in output."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        # Check at least some uncertainty columns
        uncert_cols = [c for c in df.columns if '_uncert' in c]
        assert len(uncert_cols) > 0, "Expected uncertainty columns in output"


@pytest.mark.xact
class TestXactMetaWiring(BaseReaderTest):
    """`Xact` reads its 45-element MDL table from `meta` (single source of truth).

    The limits are a *per-element diagnostic*, never a row-level flag: in the
    fixture alone a dozen elements sit 100% below their MDL, so an
    "any element below MDL" rule would NaN every row.
    """

    INSTRUMENT = 'Xact'
    DATE_RANGE_START = datetime(2025, 1, 1)
    DATE_RANGE_END = datetime(2025, 1, 7, 23, 59, 59)

    def test_mdl_prefers_the_manual(self, tmp_path):
        """The vendor's own table wins; the config supplies only what the manual
        does not cover."""
        from AeroViz.rawDataReader.config.supported_instruments import meta
        from AeroViz.rawDataReader.script.Xact import Reader

        reader = Reader(path=tmp_path, qc=True, quiet=True)

        assert len(reader.MDL) == 45, 'every reported element still has a limit'
        for element, limit in reader.manual_mdl().items():
            assert reader.MDL[element] == limit, element
        # Elements the manual does not specify still come from the config.
        assert reader.MDL['Nb'] == meta['Xact']['MDL']['Nb']

    def test_config_ti_matches_the_manual(self):
        """The config read 1.6 against the manual's 0.16 — a 10x error on a common
        crustal tracer, which counted real measurements as sub-MDL."""
        from AeroViz.rawDataReader.config.supported_instruments import meta
        from AeroViz.rawDataReader.script.Xact import Reader

        assert meta['Xact']['MDL']['Ti'] == Reader.MANUAL_MDL['Ti'][60] == 0.16

    def test_below_mdl_is_diagnostic_only(self, data_path, date_range, temp_output_dir):
        """No `Below MDL` flag reaches QC_Flag, even though most elements are
        below their limit."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        self.read_data(normal_path, date_range)

        qc_pkl = normal_path / 'xact_outputs' / '_read_xact_qc.pkl'
        if not qc_pkl.exists():
            pytest.skip('QC pickle not produced')

        flags = pd.read_pickle(qc_pkl)['QC_Flag'].dropna().unique().tolist()
        assert not any('Below MDL' in flag for flag in flags)

    def test_below_mdl_report_is_produced(self, tmp_path):
        """The diagnostic itself works and is sorted worst-first."""
        import numpy as np
        from AeroViz.rawDataReader.script.Xact import Reader

        reader = Reader(path=tmp_path, qc=True, quiet=True)
        frame = pd.DataFrame(
            {'Fe': [500.0, 600.0, 550.0],     # far above MDL 0.17
             'Pb': [0.01, 0.02, 0.01],        # all below MDL 0.13
             'Cd': [np.nan, np.nan, np.nan]},  # nothing measured
            index=pd.date_range('2025-01-01', periods=3, freq='1h'),
        )

        report = reader.log_below_mdl(frame, reader.MDL).set_index('column')

        assert report.loc['Pb', 'percentage'] == 100.0
        assert report.loc['Fe', 'below'] == 0
        assert 'Cd' not in report.index          # no measurements -> not reported
        assert report.index[0] == 'Pb'           # worst first


@pytest.mark.xact
class TestElementReliability:
    """Per-element classification from the reported 1-sigma uncertainty.

    The Xact 625i manual (Appendix p.73) publishes detection limits that are
    "interference free ONE SIGMA ... at 68% Confidence Level (C1sigma) per US EPA
    IO 3.3 and Currie, 1968". The `{element}_uncert` column is the same 1-sigma
    quantity, so Currie's criteria apply directly: detected at 3 sigma,
    quantifiable at 10 sigma.
    """

    @staticmethod
    def _reader(tmp_path):
        from AeroViz.rawDataReader.script.Xact import Reader

        return Reader(path=tmp_path, qc=True, quiet=True)

    @staticmethod
    def _frame():
        import numpy as np

        idx = pd.date_range('2025-01-01', periods=8, freq='1h')
        return pd.DataFrame({
            # 50x its uncertainty -> quantifiable
            'Fe': [500.0] * 8, 'Fe_uncert': [10.0] * 8,
            # 5x -> detected but not quantifiable
            'Cr': [5.0] * 8, 'Cr_uncert': [1.0] * 8,
            # equal to its uncertainty -> noise
            'Cd': [2.0] * 8, 'Cd_uncert': [2.0] * 8,
            # well measured, but the manual publishes no limit for Nb
            'Nb': [250.0] * 8, 'Nb_uncert': [5.0] * 8,
            'SAMPLE_TIME': [60] * 8,
        }, index=idx)

    def test_classifies_by_currie_criteria(self, tmp_path):
        rel = self._reader(tmp_path).element_reliability(self._frame())

        assert rel.loc['Fe', 'verdict'] == 'quantitative'
        assert rel.loc['Cr', 'verdict'] == 'semi-quantitative'
        assert rel.loc['Cd', 'verdict'] == 'below-detection'

    def test_published_limit_is_reported_separately(self, tmp_path):
        """Measurement quality and vendor coverage are independent axes: Nb is
        the internal standard, measured superbly, with no published limit."""
        rel = self._reader(tmp_path).element_reliability(self._frame())

        assert rel.loc['Nb', 'verdict'] == 'quantitative'
        assert not rel.loc['Nb', 'published_limit']
        assert rel.loc['Fe', 'published_limit']

    def test_detection_and_quantification_percentages(self, tmp_path):
        rel = self._reader(tmp_path).element_reliability(self._frame())

        assert rel.loc['Fe', 'detected'] == 100.0
        assert rel.loc['Fe', 'quantifiable'] == 100.0
        assert rel.loc['Cr', 'detected'] == 100.0
        assert rel.loc['Cr', 'quantifiable'] == 0.0
        assert rel.loc['Cd', 'detected'] == 0.0


@pytest.mark.xact
class TestManualDetectionLimits:
    """`MANUAL_MDL` is transcribed from the manual's appendix."""

    def test_limits_scale_with_sample_time(self, tmp_path):
        """A 15-minute sample cannot reach a 240-minute sample's detection limit;
        a single fixed number is only right for one configuration."""
        from AeroViz.rawDataReader.script.Xact import Reader

        reader = Reader(path=tmp_path, qc=True, quiet=True)

        assert reader.manual_mdl(15)['Fe'] == 1.4
        assert reader.manual_mdl(60)['Fe'] == 0.17
        assert reader.manual_mdl(240)['Fe'] == 0.021

    def test_untabulated_sample_time_takes_the_longer_column(self, tmp_path):
        """Conservative direction: a 90-minute sample is held to the 60-minute
        limit, not the 120-minute one it cannot achieve."""
        from AeroViz.rawDataReader.script.Xact import Reader

        reader = Reader(path=tmp_path, qc=True, quiet=True)

        assert reader.manual_mdl(90)['Fe'] == reader.manual_mdl(60)['Fe']

    def test_covers_the_manual_and_only_the_manual(self, tmp_path):
        from AeroViz.rawDataReader.script.Xact import Reader

        assert len(Reader.MANUAL_MDL) == 29
        for element in ('Al', 'Fe', 'Pb', 'Bi'):
            assert element in Reader.MANUAL_MDL
        # CES publishes no limit for these, though the instrument reports them
        for element in ('Ga', 'Y', 'Cs', 'La', 'Ce', 'W', 'Pt', 'Au', 'Nb'):
            assert element not in Reader.MANUAL_MDL


@pytest.mark.xact
class TestHighUncertaintyRule(BaseReaderTest):
    INSTRUMENT = 'Xact'
    DATE_RANGE_START = datetime(2025, 1, 1)
    DATE_RANGE_END = datetime(2025, 1, 7, 23, 59, 59)

    @staticmethod
    def _reader(tmp_path):
        from AeroViz.rawDataReader.script.Xact import Reader

        return Reader(path=tmp_path, qc=True, quiet=True)

    @staticmethod
    def _frame(fe_uncert):
        idx = pd.date_range('2025-01-01', periods=8, freq='1h')
        return pd.DataFrame({
            'Fe': [500.0] * 8, 'Fe_uncert': fe_uncert,
            'Zn': [120.0] * 8, 'Zn_uncert': [8.0] * 8,
            'SAMPLE_TIME': [60] * 8, 'ALARM': [0] * 8, 'SAMPLE_TYPE': [1] * 8,
        }, index=idx)

    def test_quiet_when_a_trusted_element_is_confident(self, tmp_path):
        out = self._reader(tmp_path)._QC(self._frame([10.0] * 8))

        assert not out['QC_Flag'].str.contains('High Uncertainty').any()

    def test_fires_when_a_trusted_element_goes_noisy(self, tmp_path):
        """Fe above its detection limit but with < 3 sigma confidence on two
        samples: the instrument is claiming a measurement its own error bar does
        not support."""
        out = self._reader(tmp_path)._QC(self._frame([10.0] * 6 + [400.0] * 2))

        flagged = out['QC_Flag'].str.contains('High Uncertainty')
        assert flagged.sum() == 2

    def test_is_advisory(self, tmp_path):
        """One suspect element must not delete the other 44 in the row."""
        out = self._reader(tmp_path)._QC(self._frame([10.0] * 6 + [400.0] * 2))

        flagged = out['QC_Flag'].str.contains('High Uncertainty')
        assert not out.loc[flagged, 'QC_Invalid'].any()

    def test_ignores_permanently_noisy_elements(self, data_path, date_range, temp_output_dir):
        """Scoping matters: a rule over *all* elements fires on ~100% of rows,
        because a dozen elements sit below detection at any real site."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        self.read_data(normal_path, date_range)
        qc = pd.read_pickle(normal_path / 'xact_outputs' / '_read_xact_qc.pkl')

        fired = qc['QC_Flag'].str.contains('High Uncertainty', na=False).mean()
        assert fired < 0.5, f'rule fired on {fired:.0%} of rows — too broad to be useful'

    def test_reliability_sidecar_is_written(self, data_path, date_range, temp_output_dir):
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        self.read_data(normal_path, date_range)
        sidecar = normal_path / 'xact_outputs' / 'output_xact_element_reliability.csv'

        assert sidecar.exists()
        rel = pd.read_csv(sidecar, index_col=0)
        assert set(rel['verdict']) <= {'quantitative', 'semi-quantitative', 'below-detection'}
        # The site's well-measured elements come out as expected.
        assert rel.loc['Fe', 'verdict'] == 'quantitative'
        assert rel.loc['Pb', 'verdict'] == 'quantitative'
