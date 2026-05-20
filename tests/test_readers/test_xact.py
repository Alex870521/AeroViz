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
