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

    def test_mdl_comes_from_config(self, tmp_path):
        from AeroViz.rawDataReader.config.supported_instruments import meta
        from AeroViz.rawDataReader.script.Xact import Reader

        reader = Reader(path=tmp_path, qc=True, quiet=True)
        expected = {k: v for k, v in meta['Xact']['MDL'].items() if v is not None}

        assert reader.MDL == expected
        assert len(reader.MDL) == 45

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
