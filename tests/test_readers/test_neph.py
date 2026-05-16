"""
Tests for NEPH (Nephelometer) reader.

Test Scenarios:
- normal/: Standard nephelometer files with status=0000
- status_errors/: Files with non-zero status codes
"""
import pandas as pd
import pytest
from datetime import datetime

from .base import BaseReaderTest


@pytest.mark.neph
class TestNEPHReader(BaseReaderTest):
    """Test NEPH reader functionality."""

    INSTRUMENT = 'NEPH'
    STATUS_COLUMN = 'status'

    EXPECTED_COLUMNS = [
        'sca_550', 'SAE',
    ]

    @pytest.fixture
    def date_range(self):
        """NEPH test data is from 2024."""
        return {
            'start': datetime(2024, 1, 1),
            'end': datetime(2024, 12, 31, 23, 59, 59)
        }

    def test_raw_data_has_all_columns(self, data_path, date_range, temp_output_dir):
        """Test that raw pickle preserves all original columns."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        self.read_data(normal_path, date_range)

        output_dir = normal_path / 'neph_outputs'
        raw_pkl = output_dir / '_read_neph_raw.pkl'
        if raw_pkl.exists():
            raw_data = pd.read_pickle(raw_pkl)
            # Should have scattering columns
            for col in ['B', 'G', 'R', 'BB', 'BG', 'BR']:
                assert col in raw_data.columns, f"{col} not found in raw data"

            # Should have environmental columns (RH, pressure, temp1, temp2)
            env_cols = [c for c in raw_data.columns if c in ['RH', 'pressure', 'temp1', 'temp2']]
            assert len(env_cols) > 0, "Expected environmental columns in raw data"

    def test_scattering_columns(self, data_path, date_range, temp_output_dir):
        """Test that scattering coefficient columns are present."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        assert 'sca_550' in df.columns, "sca_550 column not found"

    def test_sae_calculation(self, data_path, date_range, temp_output_dir):
        """Test that SAE is calculated."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        if 'SAE' in df.columns:
            valid_sae = df['SAE'].dropna()
            if len(valid_sae) > 0:
                assert valid_sae.min() > -2, "SAE seems unreasonably low"
                assert valid_sae.max() < 5, "SAE seems unreasonably high"
