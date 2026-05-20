"""
Tests for Aurora Nephelometer reader.

Test Scenarios:
- normal/: Standard Aurora CSV files with Status=00
- status_errors/: Files with out-of-range scattering values
"""
from datetime import datetime

import pandas as pd
import pytest

from .base import BaseReaderTest


@pytest.mark.aurora
class TestAuroraReader(BaseReaderTest):
    """Test Aurora reader functionality."""

    INSTRUMENT = 'Aurora'
    STATUS_COLUMN = None  # Aurora CSV uses S1/S2, not a recognized Status column

    # Fixture spans 2025-01-01 (single 2-hour window)
    DATE_RANGE_START = datetime(2025, 1, 1)
    DATE_RANGE_END = datetime(2025, 1, 7, 23, 59, 59)

    EXPECTED_COLUMNS = [
        'sca_550', 'SAE',
    ]

    def test_raw_data_has_all_columns(self, data_path, date_range, temp_output_dir):
        """Test that raw pickle preserves all original columns."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        self.read_data(normal_path, date_range)

        output_dir = normal_path / 'aurora_outputs'
        raw_pkl = output_dir / '_read_aurora_raw.pkl'
        if raw_pkl.exists():
            raw_data = pd.read_pickle(raw_pkl)
            # Should have scattering columns
            for col in ['B', 'G', 'R', 'BB', 'BG', 'BR']:
                assert col in raw_data.columns, f"{col} not found in raw data"

            # Should have environmental columns (T1, T2, RH, P)
            env_cols = [c for c in raw_data.columns if c in ['T1', 'T2', 'RH', 'P', 'S1', 'S2']]
            assert len(env_cols) > 0, "Expected environmental columns in raw data"

    def test_scattering_columns(self, data_path, date_range, temp_output_dir):
        """Test that scattering coefficient columns are present."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        assert 'sca_550' in df.columns, "sca_550 column not found"

    def test_csv_format(self, data_path, date_range, temp_output_dir):
        """Test reading standard CSV format."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        assert df is not None
        assert not df.empty
        assert isinstance(df.index, pd.DatetimeIndex)
